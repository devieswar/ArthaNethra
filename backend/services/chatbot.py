"""
AI Chatbot service using AWS Bedrock (Claude 3)
"""
import boto3
import json
from typing import AsyncGenerator, Dict, Any, List, Optional, Set
from loguru import logger

from config import settings
from services.indexing import IndexingService
from services.analytics import AnalyticsService


class ChatbotService:
    """AI-powered chatbot using AWS Bedrock (Amazon Nova models) with tool calling"""
    
    def __init__(self):
        self.bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.model_id = settings.BEDROCK_MODEL_ID
        self.fallback_models = getattr(settings, 'BEDROCK_FALLBACK_MODELS', [])
        self.indexing_service = IndexingService()
        self.analytics_service = AnalyticsService(self.indexing_service)
        
        # Define tools for AWS Bedrock models
        self.tools = self._initialize_tools()
    
    def _invoke_with_fallback(self, body_dict: dict, models_to_try: list = None) -> dict:
        """
        Invoke Claude model with automatic fallback on throttling
        
        Args:
            body_dict: Request body with inferenceConfig format
            models_to_try: List of Claude model IDs to try
            
        Returns:
            Response body dict
        """
        if models_to_try is None:
            models_to_try = [self.model_id] + self.fallback_models
        
        last_error = None
        for model_id in models_to_try:
            try:
                logger.info(f"Trying model: {model_id}")
                
                # Convert to Claude format
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": body_dict.get("inferenceConfig", {}).get("maxTokens", 4096),
                    "temperature": body_dict.get("inferenceConfig", {}).get("temperature", 0.7),
                    "messages": body_dict["messages"]
                }
                
                # Add system prompt if present
                if "system" in body_dict:
                    system = body_dict["system"]
                    request_body["system"] = system[0]["text"] if isinstance(system, list) else system
                
                # Add tools if present
                if "tools" in body_dict:
                    request_body["tools"] = body_dict["tools"]
                
                response = self.bedrock.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body)
                )
                response_body = json.loads(response['body'].read())
                logger.info(f"✅ Success with model: {model_id}")
                return response_body
                
            except Exception as e:
                error_str = str(e)
                if "ThrottlingException" in error_str or "Too many requests" in error_str or "throttled" in error_str.lower():
                    logger.warning(f"⚠️ Model {model_id} throttled, trying next model...")
                    last_error = e
                    continue
                else:
                    logger.error(f"Error with model {model_id}: {e}")
                    raise
        
        # All models failed
        raise Exception(f"All models throttled or failed. Last error: {last_error}")
    
    def _initialize_tools(self) -> list:
        """Initialize and return tool definitions for Bedrock"""
        return [
            {
                "name": "graph_query",
                "description": "Query the knowledge graph for specific entities (companies, loans, metrics, cities, locations). Use for structured entity lookup with optional property filters.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query_text": {
                            "type": "string",
                            "description": "Natural language description of what to search for (e.g., 'cities with accounts payable over 500000', 'companies with debt over 1 million')"
                        },
                        "entity_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by entity types: Company, Loan, Location, City, Metric, Invoice, Person, Vendor, etc."
                        },
                        "property_filters": {
                            "type": "object",
                            "description": "Filter entities by property values. Example: {\"accounts_payable\": {\"$gt\": 500000}, \"total_assets\": {\"$lt\": 1000000}}",
                            "properties": {}
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 50
                        }
                    },
                    "required": ["query_text"]
                }
            },
            {
                "name": "doc_lookup",
                "description": "Retrieve source document evidence for a specific page or section",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "Document identifier"
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number to retrieve"
                        }
                    },
                    "required": ["document_id"]
                }
            },
            {
                "name": "document_search",
                "description": "Search full document text for concepts, phrases, or topics not captured in entities. Use for questions about document content, context, or passages.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for in document text"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of chunks to return",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "metric_compute",
                "description": "Compute advanced analytics: comparisons, aggregations, thresholds, financial health checks. Supports Location, Company, Loan, Invoice entities.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "metric_name": {
                            "type": "string",
                            "description": "Metric to compute: property_threshold, property_comparison, grouped_aggregation, sequential_drop, liquidity_analysis, debt_risk, loan_maturity"
                        },
                        "params": {
                            "type": "object",
                            "description": "Metric parameters (entity_type, property names, thresholds, operators, group_by, etc.)",
                            "default": {}
                        }
                    },
                    "required": ["metric_name"]
                }
            },
            {
                "name": "graph_traverse",
                "description": "Traverse the knowledge graph to find relationships. Use for questions about connections, ownership, subsidiaries, or related entities.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_name": {
                            "type": "string",
                            "description": "Starting entity name (e.g., 'City Of Columbus', 'Acme Corp')"
                        },
                        "relationship_type": {
                            "type": "string",
                            "description": "Type of relationship to follow: OWNS, HAS_LOAN, LOCATED_IN, SUBSIDIARY_OF, WORKS_FOR, SUPPLIES_TO, RELATED_TO, or 'any' for all types",
                            "default": "any"
                        },
                        "direction": {
                            "type": "string",
                            "description": "Direction: 'outgoing' (entity->others), 'incoming' (others->entity), or 'both'",
                            "enum": ["outgoing", "incoming", "both"],
                            "default": "both"
                        },
                        "depth": {
                            "type": "integer",
                            "description": "How many hops to traverse (1-3)",
                            "default": 1,
                            "minimum": 1,
                            "maximum": 3
                        }
                    },
                    "required": ["entity_name"]
                }
            },
            {
                "name": "graph_path",
                "description": "Find shortest path between two entities in the graph. Use for 'how are X and Y connected?' questions.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "from_entity": {
                            "type": "string",
                            "description": "Starting entity name"
                        },
                        "to_entity": {
                            "type": "string",
                            "description": "Target entity name"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum path length to search",
                            "default": 5
                        }
                    },
                    "required": ["from_entity", "to_entity"]
                }
            },
            {
                "name": "graph_pattern",
                "description": "Find entities matching a specific graph pattern. Use for complex queries like 'companies with multiple loans' or 'cities in multiple counties'.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern_description": {
                            "type": "string",
                            "description": "Natural language description of the pattern to find"
                        },
                        "entity_type": {
                            "type": "string",
                            "description": "Type of entity to return (Company, Loan, Location, etc.)"
                        },
                        "min_connections": {
                            "type": "integer",
                            "description": "Minimum number of relationships",
                            "default": 1
                        }
                    },
                    "required": ["pattern_description"]
                }
            }
        ]
    
    async def chat(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> AsyncGenerator[str, None]:
        """
        Chat with the AI assistant (streaming)
        
        Args:
            message: User message
            context: Additional context (graph_id, document_id, etc.)
            
        Yields:
            Streaming response chunks
        """
        logger.info(f"Chat request: {message[:100]}...")
        
        if context is None:
            context = {}
        
        # Build messages
        messages = [
            {
                "role": "user",
                "content": message  # Simple string for Claude compatibility
            }
        ]
        
        # Build context-aware system prompt
        entities_context = ""
        if context.get("entities"):
            entities_summary = {}
            for e in context["entities"]:
                e_type = e.get("type", "UNKNOWN")
                entities_summary[e_type] = entities_summary.get(e_type, 0) + 1
            
            entities_context = f"\n\nCurrent Knowledge Graph Context:\n"
            entities_context += f"- Total entities: {context.get('total_entities', 0)}\n"
            entities_context += f"- Total documents: {context.get('total_documents', 0)}\n"
            for e_type, count in entities_summary.items():
                entities_context += f"- {e_type}: {count}\n"
            
            # Add sample entities for reference
            entities_context += f"\nKey Entities Available:\n"
            for e in context["entities"][:10]:  # Show first 10
                entities_context += f"- {e.get('name')} ({e.get('type')})\n"
        
        system_prompt = f"""You are ArthaNethra, an AI financial investigation assistant.
        
Your role is to help analysts understand complex financial documents by:
- Analyzing cities, companies, loans, and financial data from uploaded documents
- Providing evidence-backed insights with specific references to organizations and amounts
- Detecting risks and anomalies
- Explaining findings in clear, natural language that business users can understand
{entities_context}

TOOL USAGE GUIDE:

1. **graph_query**: Use for finding entities by name, type, or properties
   - ALWAYS set entity_types when user asks about entities (cities, companies, loans, etc.)
   - When user asks "Show me all cities" or "Which cities":
     * MUST set entity_types: ["Location"]
     * Set query_text: "all cities" or "cities"
     * Set limit: 100 (or higher if you want all)
   
   - When user asks "Which cities have accounts payable over $500,000?":
     * MUST set entity_types: ["Location"]
     * Set property_filters: {{"accounts_payable": {{"$gt": 500000}}}}
     * Set query_text: "cities with accounts payable over 500000"
   
   - When user asks "Show me companies" or "Show me all companies":
     * MUST set entity_types: ["Company"]
     * Set query_text: "companies"
     * Set limit: 100
   
   - When user asks "Show me companies with debt over $1 million":
     * MUST set entity_types: ["Company"]
     * Set property_filters: {{"total_debt": {{"$gt": 1000000}}}} OR {{"debt": {{"$gt": 1000000}}}}
   
   - CRITICAL: Common entity type mappings (ALWAYS use these):
     * "cities" or "city" or "all cities" → entity_types: ["Location"]
     * "companies" or "company" or "all companies" → entity_types: ["Company"]
     * "loans" or "loan" or "all loans" → entity_types: ["Loan"]
     * "invoices" or "invoice" or "all invoices" → entity_types: ["Invoice"]
     * "locations" or "location" → entity_types: ["Location"]
   
   - Property filter operators:
     * $gt: greater than (use for "over", "above", "more than")
     * $lt: less than (use for "under", "below", "less than")
     * $gte: greater than or equal (use for "at least")
     * $lte: less than or equal (use for "at most")
     * $eq: equals (use for exact matches)

2. **graph_traverse**: Use for finding connected entities
   - "Show me all entities connected to City Of Columbus"
   - "What entities are related to Company X?"

3. **graph_path**: Use for finding connections between two entities
   - "How are City X and City Y connected?"

4. **document_search**: Use for searching document text content
   - "What does page 5 say about refinancing?"

5. **metric_compute**: Use for advanced analytics that combine, compare, or aggregate multiple properties
   
   **Generic Metrics** (work with any entity type):
   - `property_threshold`: Find entities where a property meets criteria
     Example: {{"metric_name": "property_threshold", "params": {{"entity_type": "Company", "property_name": "revenue", "operator": "gt", "threshold": 1000000}}}}
   
   - `property_comparison`: Compare two properties within entities (ratio, difference, percentage)
     Example: {{"metric_name": "property_comparison", "params": {{"entity_type": "Location", "property_a": "inventory_held_for_resale", "property_b": "materials_and_supplies_inventory", "comparison_type": "pct", "operator": "gt", "threshold": 20}}}}
   
   - `grouped_aggregation`: Group entities and aggregate properties (sum, avg, max, min)
     Example: {{"metric_name": "grouped_aggregation", "params": {{"entity_type": "Location", "group_by": "county", "aggregate_property": "total_assets", "operation": "sum"}}}}
   
   - `sequential_drop`: Detect drops between consecutive entities in ordered groups
     Example: {{"metric_name": "sequential_drop", "params": {{"entity_type": "Location", "group_by": "county", "order_by": "total_assets", "drop_threshold": 0.30}}}}
   
   **Financial Health Metrics**:
   - `liquidity_analysis`: Find asset-rich but cash-poor entities
   - `debt_risk`: Identify high debt-to-asset ratios
   - `loan_maturity`: Find loans approaching maturity with high balances
   
   - ALWAYS include `graph_id` in params when available to scope analytics to the correct knowledge graph
   - Use `entity_type` param to specify Location, Company, Loan, or Invoice

IMPORTANT INSTRUCTIONS:
- ALWAYS use graph_query tool when user asks about cities, companies, loans, etc.
- When you receive tool results, you MUST use them to answer the question - DO NOT say "Let me try a different approach"
- If tool returns 0 results, say something natural like: "I didn't find any cities matching those criteria in the uploaded documents" or "No data available yet - please upload a document first"
- When metrics return a "message" field, translate it to natural language (don't say "the metric returned a message")
- Extract property names from the question using EXACT field names:
  * "cash" or "cash balance" → use "cash_and_cash_equivalents"
  * "inventory for resale" → use "inventory_held_for_resale"  
  * "materials inventory" → use "materials_and_supplies_inventory"
  * "accounts payable" → use "accounts_payable"
  * "total assets" → use "total_assets" (if available, otherwise entity may not have it)
- Use appropriate comparison operators ($gt, $lt, etc.) based on question wording
- Map entity type names correctly (cities → Location, companies → Company)
- Provide specific organization names, dollar amounts, and percentages from the results
- For financial metrics, cite actual numbers with proper formatting ($1.2M, 45%, etc.)
- If asked about risks, explain the concerning financial patterns in plain language
General guidelines:
- Always cite the document/page when you use evidence.
- If nothing is found, say so plainly and suggest a next step (e.g. upload more data, relax the filter, or re-run indexing).
- Include numbers or dates when they matter.
- NEVER use technical jargon in your responses to users. Forbidden words: "knowledge graph", "graph_id", "entity", "metric_compute", "graph_query", "tool", "Neo4j", "Weaviate", "vector", "embedding", "property_threshold", "sequential_drop", etc.
- Instead use natural business language: "financial data", "cities", "companies", "documents", "analysis", "search", "comparison", "found", "calculated"
- When you use tools internally, NEVER mention the tool names or parameters to the user
- Speak like a financial analyst, not a software engineer
"""
        
        try:
            # First call: get model's response with potential tool use
            # Use unified format (will be adapted per model in _invoke_with_fallback)
            request_body = {
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": 4096,
                    "temperature": 0.7,
                    "topP": 0.9
                },
                "tools": self.tools  # Add tools for Claude
            }
            
            # Add system prompt if provided
            if system_prompt:
                request_body["system"] = [{"text": system_prompt}]
            
            response_body = self._invoke_with_fallback(request_body)
            
            # Handle Claude response format
            content_blocks = response_body.get("content", [])
            
            for block in content_blocks:
                if block["type"] == "text":
                    yield block["text"]
                elif block["type"] == "tool_use":
                    # Execute the tool
                    tool_name = block["name"]
                    tool_input = block["input"]
                    tool_use_id = block["id"]
                    
                    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
                    
                    # Execute tool
                    tool_result = await self._execute_tool(tool_name, tool_input, context)
                    
                    # Send tool result back to Claude
                    messages.append({
                        "role": "assistant",
                        "content": content_blocks
                    })
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": json.dumps(tool_result)
                            }
                        ]
                    })
                    
                    # Get final response from Claude
                    final_request = {
                        "messages": messages,
                        "inferenceConfig": {
                            "maxTokens": 4096,
                            "temperature": 0.7,
                            "topP": 0.9
                        },
                        "tools": self.tools
                    }
                    if system_prompt:
                        final_request["system"] = [{"text": system_prompt}]
                    
                    final_body = self._invoke_with_fallback(final_request)
                    
                    # Handle Claude response
                    for final_block in final_body.get("content", []):
                        if final_block["type"] == "text":
                            yield final_block["text"]
        
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            yield f"I encountered an error: {str(e)}"
    
    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool and return results with full graph context"""
        
        if tool_name == "graph_query":
            query_text = tool_input.get("query_text", "")
            entity_types = tool_input.get("entity_types", [])
            property_filters = tool_input.get("property_filters", {})
            limit = tool_input.get("limit", 50)

            # Normalize property filter names (handle synonyms like "cash balance")
            property_filters = self._normalize_property_filters(
                property_filters,
                context=context,
                graph_id=context.get("graph_id") if context else None
            )
            
            # Use Neo4j for property-based queries (more precise)
            graph_id = context.get("graph_id") if context else None
            combined_results: List[Dict[str, Any]] = []
            sources: List[str] = []
            neo4j_results: List[Dict[str, Any]] = []

            if self.indexing_service.neo4j_driver and (property_filters or entity_types or query_text):
                try:
                    neo4j_results = await self._query_neo4j_with_filters(
                        query_text=query_text,
                        entity_types=entity_types,
                        property_filters=property_filters,
                        limit=limit,
                        graph_id=graph_id
                    )
                    logger.info(
                        f"Neo4j query returned {len(neo4j_results)} results (graph_id: {graph_id}, entity_types: {entity_types})"
                    )
                    if neo4j_results:
                        combined_results.extend(neo4j_results)
                        sources.append("neo4j_filtered")
                except Exception as e:
                    logger.warning(f"Neo4j filtered query failed: {e}")
            
            # Try Weaviate semantic search for text-based queries (also when filters are applied)
            weaviate_results: List[Dict[str, Any]] = []
            if self.indexing_service.weaviate_client:
                try:
                    weaviate_results = await self.indexing_service.query_entities(
                        query_text=query_text,
                        limit=limit
                    )
                    logger.info(f"Weaviate returned {len(weaviate_results)} results for: {query_text}")
                    
                    # Normalize Weaviate results: entityType → type, entityId → id
                    for result in weaviate_results:
                        if "entityType" in result and "type" not in result:
                            result["type"] = result["entityType"]
                        if "entityId" in result and "id" not in result:
                            result["id"] = result["entityId"]
                    
                    # Apply property filters to Weaviate results if provided
                    if property_filters and weaviate_results:
                        weaviate_results = self._filter_entities_by_properties(weaviate_results, property_filters)
                        logger.info(f"After property filtering: {len(weaviate_results)} results")
                    
                    # Apply entity type filters if provided
                    if entity_types and weaviate_results:
                        type_lower = [t.lower() for t in entity_types]
                        weaviate_results = [
                            r for r in weaviate_results
                            # Check both 'type' (Neo4j format) and 'entityType' (Weaviate format)
                            if (r.get("type", "").lower() in type_lower or
                                r.get("entityType", "").lower() in type_lower or
                                any(t in r.get("type", "").lower() for t in type_lower) or
                                any(t in r.get("entityType", "").lower() for t in type_lower))
                        ]
                        logger.info(f"After type filtering: {len(weaviate_results)} results")
                    
                    if weaviate_results:
                        combined_results.extend(weaviate_results)
                        sources.append("weaviate")
                except Exception as e:
                    logger.warning(f"Weaviate query failed: {e}")
            
            # Fallback: use entities from context if neither Neo4j nor Weaviate produced results
            if not combined_results and context.get("entities"):
                query_lower = query_text.lower()
                matching_entities = [
                    e for e in context["entities"]
                    if query_lower in e.get("name", "").lower() or
                       query_lower in str(e.get("properties", {})).lower()
                ]

                if property_filters:
                    matching_entities = self._filter_entities_by_properties(matching_entities, property_filters)

                combined_results = matching_entities[:limit]
                if combined_results:
                    sources.append("context")
                logger.info(f"Context search returned {len(combined_results)} results")

            # Deduplicate while preserving order and re-apply property filters as a safeguard
            seen_keys = set()
            deduped_results: List[Dict[str, Any]] = []
            for entity in combined_results:
                key = entity.get("id") or entity.get("entityId")
                if key:
                    key = f"id:{key}"
                else:
                    key = f"name:{entity.get('name', '').lower()}"

                if key in seen_keys:
                    continue
                seen_keys.add(key)
                deduped_results.append(entity)

            final_results = deduped_results
            if property_filters and final_results:
                final_results = self._filter_entities_by_properties(final_results, property_filters)

            if limit and final_results:
                final_results = final_results[:limit]

            evidence = await self._build_markdown_evidence(final_results, graph_id)

            source_label = "+".join(sources) if sources else ("weaviate" if self.indexing_service.weaviate_client else "context")

            return {
                "results": final_results,
                "count": len(final_results),
                "query": query_text,
                "source": source_label,
                "graph_id": graph_id,
                "evidence": evidence
            }
        
        elif tool_name == "graph_traverse":
            return await self._tool_graph_traverse(tool_input)
        
        elif tool_name == "graph_path":
            return await self._tool_graph_path(tool_input)
        
        elif tool_name == "graph_pattern":
            return await self._tool_graph_pattern(tool_input)
        
        elif tool_name == "doc_lookup":
            # Look up document evidence
            document_id = tool_input.get("document_id")
            page = tool_input.get("page")
            return {
                "document_id": document_id,
                "page": page,
                "url": f"/api/v1/evidence/{document_id}?page={page}"
            }
        
        elif tool_name == "document_search":
            # Search full document text
            query = tool_input.get("query", "")
            limit = tool_input.get("limit", 5)
            
            try:
                chunks = await self.indexing_service.search_document_chunks(query, limit)
                logger.info(f"Document search returned {len(chunks)} chunks for: {query}")
                
                return {
                    "query": query,
                    "chunks": chunks,
                    "count": len(chunks)
                }
            except Exception as e:
                logger.error(f"Document search error: {e}")
                return {
                    "query": query,
                    "chunks": [],
                    "error": str(e)
                }
        
        elif tool_name == "metric_compute":
            metric_name = tool_input.get("metric_name")
            params = tool_input.get("params", {})

            enriched_context = dict(context or {})
            if "graph_id" not in enriched_context and params.get("graph_id"):
                enriched_context["graph_id"] = params.get("graph_id")

            result = self.analytics_service.compute_metric(
                metric_name=metric_name,
                params=params,
                context=enriched_context,
            )

            result.setdefault("metric_name", metric_name)
            return result
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def generate_risk_summary(
        self,
        risks: List[Dict[str, Any]]
    ) -> str:
        """Generate natural language risk summary using Claude"""
        
        prompt = f"""Analyze these financial risks and provide a concise executive summary:

{json.dumps(risks, indent=2)}

Focus on:
1. Most critical risks
2. Overall risk level
3. Key recommendations

Keep it under 200 words and professional."""

        messages = [{"role": "user", "content": prompt}]
        
        response_body = self._invoke_with_fallback({
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": 1024,
                "temperature": 0.5,
                "topP": 0.9
            }
        })
        
        # Handle Claude response
        return response_body["content"][0]["text"]
    
    async def _tool_graph_traverse(self, params: Dict) -> Dict:
        """Traverse relationships from a starting entity using Neo4j"""
        if not self.indexing_service.neo4j_driver:
            return {"error": "Neo4j not available", "results": []}
        
        entity_name = params["entity_name"]
        relationship_type = params.get("relationship_type", "any")
        direction = params.get("direction", "both")
        depth = min(params.get("depth", 1), 3)  # Cap at 3 hops
        
        logger.info(f"🔍 Graph traverse: {entity_name} | type: {relationship_type} | direction: {direction} | depth: {depth}")
        
        # Build Cypher query based on direction
        if direction == "outgoing":
            pattern = f"(start)-[r*1..{depth}]->(connected)"
        elif direction == "incoming":
            pattern = f"(start)<-[r*1..{depth}]-(connected)"
        else:  # both
            pattern = f"(start)-[r*1..{depth}]-(connected)"
        
        # Add relationship type filter if specified
        if relationship_type != "any":
            rel_filter = f"AND ALL(rel IN r WHERE rel.type = '{relationship_type}')"
        else:
            rel_filter = ""
        
        cypher = f"""
        MATCH (start:Entity)
        WHERE start.name = $entity_name
        MATCH {pattern}
        WHERE connected.id <> start.id {rel_filter}
        RETURN DISTINCT
            connected.id AS id,
            connected.name AS name,
            connected.type AS type,
            connected.properties AS properties,
            [rel IN r | rel.type] AS relationship_path,
            length(r) AS distance
        ORDER BY distance, name
        LIMIT 50
        """
        
        try:
            with self.indexing_service.neo4j_driver.session() as session:
                result = session.run(cypher, entity_name=entity_name)
                
                connected_entities = []
                for record in result:
                    connected_entities.append({
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "properties": json.loads(record["properties"]) if record["properties"] else {},
                        "relationship_path": record["relationship_path"],
                        "distance": record["distance"]
                    })
                
                logger.info(f"✅ Found {len(connected_entities)} connected entities")
                
                return {
                    "starting_entity": entity_name,
                    "connected_entities": connected_entities,
                    "count": len(connected_entities),
                    "relationship_type": relationship_type,
                    "direction": direction,
                    "max_depth": depth
                }
        
        except Exception as e:
            logger.error(f"Neo4j traverse error: {e}")
            return {"error": str(e), "results": []}
    
    async def _tool_graph_path(self, params: Dict) -> Dict:
        """Find shortest path between two entities using Neo4j"""
        if not self.indexing_service.neo4j_driver:
            return {"error": "Neo4j not available", "path": []}
        
        from_entity = params["from_entity"]
        to_entity = params["to_entity"]
        max_depth = min(params.get("max_depth", 5), 10)  # Cap at 10 hops
        
        logger.info(f"🔍 Finding path: {from_entity} → {to_entity} (max depth: {max_depth})")

        try:
            with self.indexing_service.neo4j_driver.session() as session:
                exists_query = """
                MATCH (n:Entity {name: $name})
                RETURN n
                LIMIT 1
                """

                start_exists = session.run(exists_query, name=from_entity).single() is not None
                end_exists = session.run(exists_query, name=to_entity).single() is not None

                if not start_exists or not end_exists:
                    missing = []
                    if not start_exists:
                        missing.append(from_entity)
                    if not end_exists:
                        missing.append(to_entity)

                    evidence = await self._build_markdown_evidence([
                        {"name": from_entity},
                        {"name": to_entity}
                    ])
                    return {
                        "from": from_entity,
                        "to": to_entity,
                        "path_found": False,
                        "missing_entities": missing,
                        "message": "Entities not present in knowledge graph"
                    }

                cypher = """
                MATCH (start:Entity {name: $from_entity})
                MATCH (end:Entity {name: $to_entity})
                MATCH path = shortestPath((start)-[*1..%d]-(end))
                RETURN 
                    [node IN nodes(path) | {
                        id: node.id,
                        name: node.name,
                        type: node.type,
                        properties: node.properties
                    }] AS nodes,
                    [rel IN relationships(path) | {
                        type: rel.type,
                        properties: rel.properties
                    }] AS relationships,
                    length(path) AS path_length
                LIMIT 1
                """ % max_depth

                result = session.run(
                    cypher,
                    from_entity=from_entity,
                    to_entity=to_entity
                )
                
                record = result.single()
                if not record:
                    evidence = await self._build_markdown_evidence([
                        {"name": from_entity},
                        {"name": to_entity}
                    ])
                    return {
                        "from": from_entity,
                        "to": to_entity,
                        "path_found": False,
                        "missing_entities": [],
                        "message": f"No path found between '{from_entity}' and '{to_entity}' within {max_depth} hops",
                        "evidence": evidence
                    }
                
                # Parse nodes and relationships
                nodes = []
                for node in record["nodes"]:
                    nodes.append({
                        "id": node["id"],
                        "name": node["name"],
                        "type": node["type"],
                        "properties": json.loads(node["properties"]) if node["properties"] else {}
                    })
                
                relationships = []
                for rel in record["relationships"]:
                    relationships.append({
                        "type": rel["type"],
                        "properties": json.loads(rel["properties"]) if rel["properties"] else {}
                    })
                
                logger.info(f"✅ Found path with {record['path_length']} hops")
                
                return {
                    "from": from_entity,
                    "to": to_entity,
                    "path_found": True,
                    "path_length": record["path_length"],
                    "nodes": nodes,
                    "relationships": relationships
                }
        
        except Exception as e:
            logger.error(f"Neo4j path finding error: {e}")
            return {"error": str(e), "path_found": False}
    
    async def _tool_graph_pattern(self, params: Dict) -> Dict:
        """Find entities matching a graph pattern using Neo4j"""
        if not self.indexing_service.neo4j_driver:
            return {"error": "Neo4j not available", "results": []}
        
        pattern_description = params["pattern_description"]
        entity_type = params.get("entity_type", "")
        min_connections = params.get("min_connections", 1)
        
        logger.info(f"🔍 Pattern search: {pattern_description} | type: {entity_type} | min connections: {min_connections}")
        
        # Build type filter
        type_filter = f"AND e.type = '{entity_type}'" if entity_type else ""
        
        # Query for entities with minimum number of relationships
        cypher = f"""
        MATCH (e:Entity)
        WHERE true {type_filter}
        OPTIONAL MATCH (e)-[r]-(other:Entity)
        WITH e, count(DISTINCT r) AS relationship_count, collect(DISTINCT other.name) AS connected_to
        WHERE relationship_count >= $min_connections
        RETURN 
            e.id AS id,
            e.name AS name,
            e.type AS type,
            e.properties AS properties,
            relationship_count,
            connected_to
        ORDER BY relationship_count DESC
        LIMIT 50
        """
        
        try:
            with self.indexing_service.neo4j_driver.session() as session:
                result = session.run(cypher, min_connections=min_connections)
                
                matches = []
                for record in result:
                    matches.append({
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "properties": json.loads(record["properties"]) if record["properties"] else {},
                        "relationship_count": record["relationship_count"],
                        "connected_to": record["connected_to"][:10]  # Limit to first 10
                    })
                
                logger.info(f"✅ Found {len(matches)} entities matching pattern")
                
                return {
                    "pattern": pattern_description,
                    "entity_type": entity_type or "any",
                    "min_connections": min_connections,
                    "matches": matches,
                    "count": len(matches)
                }
        
        except Exception as e:
            logger.error(f"Neo4j pattern matching error: {e}")
            return {"error": str(e), "results": []}
    
    async def _query_neo4j_with_filters(
        self,
        query_text: str,
        entity_types: List[str],
        property_filters: Dict[str, Any],
        limit: int,
        graph_id: str = None
    ) -> List[Dict[str, Any]]:
        """Query Neo4j with entity type and property filters"""
        if not self.indexing_service.neo4j_driver:
            return []
        
        # Map common entity type names to actual EntityType enum values
        # IMPORTANT: These must match the EntityType enum values exactly (case-sensitive)
        type_mapping = {
            "city": "Location",
            "cities": "Location",
            "location": "Location",
            "company": "Company",
            "companies": "Company",
            "loan": "Loan",
            "loans": "Loan",
            "invoice": "Invoice",
            "invoices": "Invoice",
            "metric": "Metric",
            "metrics": "Metric",
            "person": "Person",
            "vendor": "Vendor"
        }
        
        # If no entity_types provided, try to infer from query_text
        if not entity_types:
            query_lower = query_text.lower()
            if "cities" in query_lower or "city" in query_lower:
                entity_types = ["Location"]
            elif "companies" in query_lower or "company" in query_lower:
                entity_types = ["Company"]
            elif "loans" in query_lower or "loan" in query_lower:
                entity_types = ["Loan"]
            elif "invoices" in query_lower or "invoice" in query_lower:
                entity_types = ["Invoice"]
        
        # Normalize entity types to match EntityType enum values
        normalized_types = []
        for et in entity_types:
            et_lower = et.lower()
            if et_lower in type_mapping:
                normalized_types.append(type_mapping[et_lower])
            elif et in ["Company", "Loan", "Location", "Metric", "Invoice", "Person", "Vendor", "Clause"]:
                # Already in correct format
                normalized_types.append(et)
        
        # Build Cypher query - filter by graphId if provided (Neo4j stores as graphId)
        graph_filter = ""
        if graph_id:
            graph_filter = f"AND e.graphId = '{graph_id}'"
        
        type_filter = ""
        if normalized_types:
            type_list = "', '".join(normalized_types)
            type_filter = f"AND e.type IN ['{type_list}']"
        
        # Build property filters - use Python filtering for complex queries
        # Note: Neo4j stores properties as entityId, graphId, type, name, properties (not id)
        cypher = f"""
        MATCH (e:Entity)
        WHERE true {graph_filter} {type_filter}
        RETURN 
            e.entityId AS id,
            e.name AS name,
            e.type AS type,
            e.properties AS properties
        LIMIT {limit * 2}
        """
        
        logger.info(f"Executing Neo4j query: {cypher}")
        
        try:
            with self.indexing_service.neo4j_driver.session() as session:
                result = session.run(cypher)
                
                entities = []
                for record in result:
                    props_str = record.get("properties", "")
                    try:
                        # Properties are stored as string, need to parse
                        if isinstance(props_str, str):
                            props = json.loads(props_str) if props_str else {}
                        else:
                            props = props_str or {}
                    except:
                        props = {}
                    
                    entities.append({
                        "id": record.get("id"),
                        "name": record.get("name"),
                        "type": record.get("type"),
                        "properties": props
                    })
                
                logger.info(f"Neo4j query returned {len(entities)} entities")
                
                # Apply property filters in Python (more reliable than Cypher for complex JSON)
                if property_filters:
                    entities = self._filter_entities_by_properties(entities, property_filters)
                
                return entities[:limit]
        except Exception as e:
            logger.error(f"Neo4j query error: {e}")
            return []
    
    def _filter_entities_by_properties(self, entities: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
        """Filter entities by property values in Python"""
        filtered = []
        
        for entity in entities:
            props = entity.get("properties", {})
            if not isinstance(props, dict):
                try:
                    props = json.loads(props) if isinstance(props, str) else {}
                except:
                    props = {}
            
            matches = True
            for prop_name, prop_value in filters.items():
                # Handle nested property names (e.g., "accounts_payable")
                entity_value = props.get(prop_name)
                
                if entity_value is None:
                    matches = False
                    break
                
                # Handle operators
                if isinstance(prop_value, dict):
                    try:
                        entity_num = float(entity_value)
                        
                        if "$gt" in prop_value:
                            if entity_num <= float(prop_value["$gt"]):
                                matches = False
                        elif "$lt" in prop_value:
                            if entity_num >= float(prop_value["$lt"]):
                                matches = False
                        elif "$gte" in prop_value:
                            if entity_num < float(prop_value["$gte"]):
                                matches = False
                        elif "$lte" in prop_value:
                            if entity_num > float(prop_value["$lte"]):
                                matches = False
                        elif "$eq" in prop_value:
                            if entity_num != float(prop_value["$eq"]):
                                matches = False
                    except (ValueError, TypeError):
                        # If not numeric, skip numeric comparison
                        if "$eq" in prop_value:
                            if str(entity_value) != str(prop_value["$eq"]):
                                matches = False
                else:
                    # Simple equality
                    try:
                        if float(entity_value) != float(prop_value):
                            matches = False
                    except (ValueError, TypeError):
                        if str(entity_value) != str(prop_value):
                            matches = False
                
                if not matches:
                    break
            
            if matches:
                filtered.append(entity)
        
        return filtered

    def _normalize_property_filters(
        self,
        filters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        graph_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Map friendly property names or synonyms to actual entity property keys."""
        if not filters:
            return {}

        def normalize_key(value: str) -> str:
            return "".join(ch for ch in value.lower() if ch.isalnum())

        available_props: Set[str] = set()

        if context and context.get("entities"):
            for entity in context["entities"]:
                props = entity.get("properties") or {}
                available_props.update(props.keys())

        if not available_props and graph_id and self.indexing_service.neo4j_driver:
            try:
                with self.indexing_service.neo4j_driver.session() as session:
                    records = session.run(
                        """
                        MATCH (e:Entity {graphId: $graph_id})
                        RETURN e.properties AS props
                        LIMIT 20
                        """,
                        graph_id=graph_id
                    )
                    for record in records:
                        props = record.get("props")
                        if isinstance(props, str):
                            try:
                                props = json.loads(props)
                            except Exception:
                                props = {}
                        if isinstance(props, dict):
                            available_props.update(props.keys())
            except Exception as e:
                logger.debug(f"Unable to fetch property keys from Neo4j: {e}")

        normalized_lookup: Dict[str, str] = {}
        for prop in available_props:
            key_norm = normalize_key(prop)
            if key_norm:
                normalized_lookup[key_norm] = prop
                normalized_lookup.setdefault(key_norm.replace("and", ""), prop)
                normalized_lookup.setdefault(key_norm.replace("the", ""), prop)

            words = prop.replace("_", " ").split()
            if words:
                joined = "".join(words)
                normalized_lookup.setdefault(normalize_key(joined), prop)
                if len(words) > 1:
                    normalized_lookup.setdefault(normalize_key(words[0]), prop)
                    normalized_lookup.setdefault(normalize_key(words[-1]), prop)

        normalized: Dict[str, Any] = {}
        for key, value in filters.items():
            candidate = normalize_key(key)
            canonical = normalized_lookup.get(candidate)

            if not canonical:
                # Fuzzy match: find property whose normalized key contains the candidate
                for norm_key, prop in normalized_lookup.items():
                    if candidate and candidate in norm_key:
                        canonical = prop
                        break

            normalized[canonical or key] = value

        return normalized

    async def _build_markdown_evidence(self, entities: List[Dict[str, Any]], graph_id: str = None, per_entity: int = 1, max_entities: int = 5) -> List[Dict[str, Any]]:
        """Collect supporting markdown/document snippets for entities."""
        if not entities or not self.indexing_service or not getattr(self.indexing_service, "weaviate_client", None):
            return []

        evidence: List[Dict[str, Any]] = []
        sampled_entities = entities[:max_entities]

        for entity in sampled_entities:
            name = entity.get("name")
            if not name:
                continue

            try:
                chunks = await self.indexing_service.search_document_chunks(name, limit=per_entity)
            except Exception as e:
                logger.warning(f"Failed to fetch markdown evidence for {name}: {e}")
                continue

            for chunk in chunks:
                evidence.append({
                    "entity_id": entity.get("id"),
                    "entity_name": name,
                    "snippet": chunk.get("content"),
                    "page_number": chunk.get("page_number"),
                    "document_id": chunk.get("document_id"),
                    "score": chunk.get("score")
                })

        return evidence


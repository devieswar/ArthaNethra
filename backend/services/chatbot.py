"""
AI Chatbot service using AWS Bedrock (Claude 3)
"""
import boto3
import json
from typing import AsyncGenerator, Dict, Any, List
from loguru import logger

from config import settings
from services.indexing import IndexingService


class ChatbotService:
    """AI-powered chatbot using Claude 3 on AWS Bedrock with tool calling"""
    
    def __init__(self):
        self.bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.model_id = settings.BEDROCK_MODEL_ID
        self.indexing_service = IndexingService()
        
        # Define tools for Claude
        self.tools = [
            {
                "name": "graph_query",
                "description": "Query the knowledge graph for entities and relationships. Use this to find companies, subsidiaries, loans, or financial metrics.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query_text": {
                            "type": "string",
                            "description": "Natural language description of what to search for"
                        },
                        "entity_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by entity types (Company, Loan, Subsidiary, etc.)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
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
                "name": "metric_compute",
                "description": "Compute or aggregate financial metrics from entities",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "metric_name": {
                            "type": "string",
                            "description": "Name of metric to compute (e.g., 'total_debt', 'debt_ratio')"
                        },
                        "entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Entity IDs to aggregate over"
                        }
                    },
                    "required": ["metric_name"]
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
        
        # Build messages for Claude
        messages = [
            {
                "role": "user",
                "content": message
            }
        ]
        
        # System prompt
        system_prompt = """You are ArthaNethra, an AI financial investigation assistant.
        
Your role is to help analysts understand complex financial documents by:
- Querying the knowledge graph of entities and relationships
- Providing evidence-backed insights with citations
- Detecting risks and anomalies
- Explaining findings in clear, professional language

ALWAYS:
- Use the available tools to retrieve accurate information
- Cite your sources (page numbers, sections)
- Provide numeric evidence when discussing metrics
- Explain your reasoning step-by-step

When asked about financial risks, entities, or relationships:
1. Use graph_query to find relevant entities
2. Analyze the results
3. Provide clear explanations with citations
"""
        
        try:
            # First call: get Claude's response with potential tool use
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": messages,
                    "tools": self.tools,
                    "temperature": 0.7
                })
            )
            
            response_body = json.loads(response['body'].read())
            
            # Check if Claude wants to use a tool
            content_blocks = response_body.get("content", [])
            
            for block in content_blocks:
                if block["type"] == "text":
                    # Stream the text response
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
                    final_response = self.bedrock.invoke_model(
                        modelId=self.model_id,
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 4096,
                            "system": system_prompt,
                            "messages": messages,
                            "tools": self.tools,
                            "temperature": 0.7
                        })
                    )
                    
                    final_body = json.loads(final_response['body'].read())
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
        """Execute a tool and return results"""
        
        if tool_name == "graph_query":
            # Query the knowledge graph
            results = await self.indexing_service.query_entities(
                query_text=tool_input.get("query_text"),
                limit=tool_input.get("limit", 10)
            )
            return {
                "results": results,
                "count": len(results)
            }
        
        elif tool_name == "doc_lookup":
            # Look up document evidence
            document_id = tool_input.get("document_id")
            page = tool_input.get("page")
            return {
                "document_id": document_id,
                "page": page,
                "url": f"/api/v1/evidence/{document_id}?page={page}"
            }
        
        elif tool_name == "metric_compute":
            # Compute metrics
            metric_name = tool_input.get("metric_name")
            entity_ids = tool_input.get("entity_ids", [])
            
            # TODO: Implement actual metric computation
            return {
                "metric_name": metric_name,
                "value": 0.0,
                "entities_count": len(entity_ids)
            }
        
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
        
        response = self.bedrock.invoke_model(
            modelId=self.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": messages,
                "temperature": 0.5
            })
        )
        
        response_body = json.loads(response['body'].read())
        return response_body["content"][0]["text"]


"""
LLM-based relationship detection service
Analyzes entities in chunks to discover semantic relationships
"""
import json
import re
import uuid
import boto3
from typing import List, Dict, Any
from loguru import logger

from config import settings
from models.entity import Entity, EntityType
from models.edge import Edge, EdgeType


class RelationshipDetector:
    """Uses LLM to intelligently discover relationships between entities"""
    
    def __init__(self):
        self.bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        
        # Map string edge types to EdgeType enum (case-insensitive)
        self.edge_type_mapping = {}
        for edge_type in EdgeType:
            canonical = edge_type.value.upper()
            self.edge_type_mapping[canonical] = edge_type
            self.edge_type_mapping[edge_type.name.upper()] = edge_type

        # Synonyms/aliases produced by the LLM mapped to canonical EdgeType values
        self.edge_type_aliases = {
            "OWNER_OF": EdgeType.OWNS,
            "OWNED_BY": EdgeType.SUBSIDIARY_OF,
            "PARENT_OF": EdgeType.OWNS,
            "PARENT_COMPANY": EdgeType.OWNS,
            "CHILD_OF": EdgeType.SUBSIDIARY_OF,
            "SUBSIDIARY": EdgeType.SUBSIDIARY_OF,
            "PARTNER_OF": EdgeType.PARTNERS_WITH,
            "PARTNERS_WITH": EdgeType.PARTNERS_WITH,
            "PARTNERSHIP_WITH": EdgeType.PARTNERS_WITH,
            "PROVIDES_SERVICES_TO": EdgeType.PROVIDES_SERVICE_FOR,
            "PROVIDES_SERVICE_TO": EdgeType.PROVIDES_SERVICE_FOR,
            "PROVIDES_SERVICE": EdgeType.PROVIDES_SERVICE_FOR,
            "PROVIDES_TO": EdgeType.PROVIDES_SERVICE_FOR,
            "SUPPLIES": EdgeType.SUPPLIES_TO,
            "SUPPLIES_FOR": EdgeType.SUPPLIES_TO,
            "SUPPLIER_OF": EdgeType.SUPPLIES_TO,
            "RECEIVES_SERVICE": EdgeType.RECEIVES_SERVICE_FROM,
            "RECEIVES_SERVICES_FROM": EdgeType.RECEIVES_SERVICE_FROM,
            "CUSTOMER_OF": EdgeType.RECEIVES_SERVICE_FROM,
            "CLIENT_OF": EdgeType.RECEIVES_SERVICE_FROM,
            "INVESTED": EdgeType.INVESTED_IN,
            "INVESTED_INTO": EdgeType.INVESTED_IN,
            "INVESTOR_IN": EdgeType.INVESTED_IN,
            "ACQUIRED_BY": EdgeType.ACQUIRED,
            "ACQUIRES": EdgeType.ACQUIRED,
            "GUARANTEED_BY": EdgeType.GUARANTEES,
            "GUARANTEE_OF": EdgeType.GUARANTEES,
            "GUARANTOR": EdgeType.GUARANTEES,
            "LOANED_BY": EdgeType.FINANCED_BY,
            "FINANCED": EdgeType.FINANCED_BY,
            "FINANCED_BY": EdgeType.FINANCED_BY,
            "BORROWS_FROM": EdgeType.FINANCED_BY,
            "OWES_TO": EdgeType.OWES,
            "OWES_TOWARDS": EdgeType.OWES,
            "DEBT_TO": EdgeType.OWES,
            "ISSUED_TO": EdgeType.ISSUED_BY,
            "REGULATED": EdgeType.REGULATED_BY,
            "REGULATED_BY": EdgeType.REGULATED_BY,
            "REPORTS_ON": EdgeType.REPORTS_ON,
            "REPORTS_ABOUT": EdgeType.REPORTS_ON,
            "REFERENCED_IN": EdgeType.MENTIONED_IN,
            "MENTIONS": EdgeType.REFERENCES,
            "MENTIONED_BY": EdgeType.REFERENCES,
            "DOCUMENTS": EdgeType.REPORTS_ON,
            "CONNECTED_TO": EdgeType.RELATED_TO,
            "ASSOCIATED_TO": EdgeType.ASSOCIATED_WITH,
            "ASSOCIATED_WITH": EdgeType.ASSOCIATED_WITH,
            "RELATES_TO": EdgeType.RELATED_TO,
            "LINKED_TO": EdgeType.RELATED_TO,
        }
    
    async def detect_relationships_chunked(
        self,
        entities: List[Entity],
        graph_id: str,
        chunk_size: int = 20
    ) -> List[Edge]:
        """
        Detect relationships using LLM with chunking strategy.
        
        Args:
            entities: List of all entities
            graph_id: Graph identifier
            chunk_size: Number of entities to process per LLM call
        
        Returns:
            List of detected edges
        """
        all_edges = []
        
        # Chunk entities for efficient processing
        chunks = self._chunk_entities(entities, chunk_size)
        
        logger.info(f"Detecting relationships across {len(chunks)} chunks ({len(entities)} entities)")
        
        for i, chunk in enumerate(chunks):
            try:
                logger.info(f"🤖 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} entities)")
                
                chunk_edges = await self._detect_relationships_in_chunk(
                    chunk, graph_id, all_entities=entities
                )
                
                all_edges.extend(chunk_edges)
                logger.info(f"Chunk {i+1}: Found {len(chunk_edges)} relationships")
                
            except Exception as e:
                logger.warning(f"Failed to process chunk {i+1}: {e}")
                continue
        
        # Deduplicate edges
        all_edges = self._deduplicate_edges(all_edges)
        
        logger.info(f"Total relationships detected: {len(all_edges)}")
        return all_edges
    
    def _chunk_entities(self, entities: List[Entity], chunk_size: int) -> List[List[Entity]]:
        """Split entities into manageable chunks"""
        return [entities[i:i + chunk_size] for i in range(0, len(entities), chunk_size)]

    def _normalize_edge_type(self, raw_edge_type: str) -> EdgeType:
        """
        Map an arbitrary edge type string from the LLM to a canonical EdgeType.
        Falls back to RELATED_TO if no mapping is found.
        """
        if not raw_edge_type:
            logger.warning("Received empty edge_type from LLM; defaulting to RELATED_TO")
            return EdgeType.RELATED_TO

        key = str(raw_edge_type).strip().upper()
        key = key.replace("-", "_").replace(" ", "_")

        if key in self.edge_type_mapping:
            return self.edge_type_mapping[key]

        if key in self.edge_type_aliases:
            canonical = self.edge_type_aliases[key]
            logger.debug(f"Mapped edge type alias '{raw_edge_type}' -> '{canonical.value}'")
            return canonical

        logger.warning(f"Unknown edge type '{raw_edge_type}', defaulting to RELATED_TO")
        return EdgeType.RELATED_TO
    
    async def _detect_relationships_in_chunk(
        self,
        chunk: List[Entity],
        graph_id: str,
        all_entities: List[Entity]
    ) -> List[Edge]:
        """Use LLM to detect relationships within a chunk"""
        
        # Prepare entity data for LLM
        entity_descriptions = []
        for entity in chunk:
            # Include ALL properties for comprehensive relationship detection
            props_summary = dict(entity.properties)  # ALL properties
            
            entity_descriptions.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type.value,
                "properties": props_summary  # Changed from key_properties to properties
            })
        
        # System prompt for relationship detection
        system_prompt = """You are a knowledge graph expert. Analyze entities and identify ALL meaningful relationships between them.

Your goal: Find EVERY relationship where entities are connected through:
1. **Shared Properties**: Entities with same property values (e.g., same county, same industry)
2. **Hierarchical Relationships**: Parent-child, part-of, located-in (city → county → state)
3. **Functional Relationships**: One entity serves/supplies/reports to another
4. **Organizational Relationships**: Ownership, subsidiary, partnership
5. **Financial Relationships**: Has loan, issued by, owes to
6. **Semantic Relationships**: ANY logical connection based on entity types and properties

Available relationship types:
- LOCATED_IN: Entity is in a location (city → county → state → country)
- HAS_METRIC: Entity has associated metrics/measurements
- RELATED_TO: General semantic relationship (use for any meaningful connection)
- ISSUED_BY: Document/loan/debt issued by an entity
- HAS_LOAN: Entity has a loan
- OWNS: Owns a subsidiary/asset
- WORKS_FOR: Employment relationship
- SUBSIDIARY_OF: Is a subsidiary of
- REPORTS_TO: Hierarchical reporting
- SUPPLIES_TO: Vendor/supplier relationship
- MENTIONED_IN: Referenced in document/clause

**IMPORTANT INSTRUCTIONS**:
1. Look at entity NAMES and TYPES for obvious relationships
2. Compare all PROPERTIES - if entities share values, they're related
3. Infer hierarchical relationships from entity types (city LOCATED_IN county)
4. Create RELATED_TO for any meaningful connection not covered by specific types
5. Include ALL relationships - be comprehensive, not conservative
6. Minimum confidence: 0.6 (be inclusive, not restrictive)

Respond with JSON array:
[
  {
    "source_id": "entity_123",
    "target_id": "entity_456",
    "edge_type": "LOCATED_IN",
    "confidence": 0.95,
    "reasoning": "City of Akron is located in Summit County based on county property"
  }
]

GOAL: Maximum relationship discovery! Find EVERYTHING connected!"""

        user_prompt = f"""Analyze these entities and identify relationships between them:

{json.dumps(entity_descriptions, indent=2)}

Provide relationships in JSON format."""

        try:
            # Call Claude
            response = self.bedrock.invoke_model(
                modelId=settings.BEDROCK_MODEL_ID,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2048,
                    "temperature": 0.2,  # Low temp for consistent, conservative analysis
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            
            llm_response = None
            for block in content:
                if block.get('type') == 'text':
                    llm_response = block.get('text', '')
                    break
            
            if not llm_response or not llm_response.strip():
                logger.warning("No LLM response for relationships")
                return []
            
            # Parse relationships from LLM response
            try:
                relationships = self._parse_relationships_json(llm_response)
            except ValueError as e:
                logger.warning(f"Failed to parse relationships JSON: {e}; response snippet: {llm_response[:200]!r}")
                return []
            
            # Convert to Edge objects
            edges = []
            for rel in relationships:
                confidence = rel.get('confidence', 0.8)
                
                # Include relationships with confidence >= 0.6 (inclusive approach)
                if confidence < 0.6:
                    continue
                
                # Map string edge type to enum
                edge_type_str = rel.get('edge_type', 'RELATED_TO')
                edge_type = self._normalize_edge_type(edge_type_str)
                
                edge = Edge(
                    id=f"edge_{uuid.uuid4().hex[:12]}",
                    source=rel['source_id'],
                    target=rel['target_id'],
                    type=edge_type,
                    graph_id=graph_id,
                    properties={
                        "confidence": confidence,
                        "reasoning": rel.get('reasoning', ''),
                        "detected_by": "llm",
                        "raw_edge_type": edge_type_str
                    }
                )
                edges.append(edge)
            
            logger.info(f"LLM detected {len(edges)} relationships (from {len(relationships)} candidates)")
            return edges
            
        except Exception as e:
            logger.error(f"Error in LLM relationship detection: {e}")
            return []
    
    def _parse_relationships_json(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Extract relationship definitions from an LLM response that may include extra prose.
        Returns a list of dictionaries describing relationships.
        """
        if not llm_response:
            return []
        
        text = llm_response.strip()
        if not text:
            return []
        
        json_decoder = json.JSONDecoder()
        candidates = []
        
        # Prefer JSON inside fenced code blocks
        fenced_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text, re.IGNORECASE)
        if fenced_match:
            candidates.append(fenced_match.group(1))
        
        # Strip leading commentary like "Here are..." by finding first JSON character
        candidates.append(text)
        
        def normalize_payload(payload: Any) -> List[Dict[str, Any]]:
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                relationships = payload.get("relationships")
                if isinstance(relationships, list):
                    return relationships
                return [payload]
            raise ValueError("Parsed JSON is not a list or object")
        
        for candidate in candidates:
            candidate_str = candidate.strip()
            if not candidate_str:
                continue
            
            # Direct parse attempt
            try:
                parsed = json.loads(candidate_str)
                return normalize_payload(parsed)
            except json.JSONDecodeError:
                pass
            
            # Try raw decoding from first JSON token
            for start_char, end_char in (('[', ']'), ('{', '}')):
                start_idx = candidate_str.find(start_char)
                if start_idx == -1:
                    continue
                
                substring = candidate_str[start_idx:]
                
                # Attempt raw decode (handles trailing commentary)
                try:
                    parsed, _ = json_decoder.raw_decode(substring)
                    return normalize_payload(parsed)
                except json.JSONDecodeError:
                    pass
                
                # Trim to matching closing bracket and retry
                end_idx = substring.rfind(end_char)
                if end_idx != -1:
                    trimmed = substring[: end_idx + 1]
                    try:
                        parsed = json.loads(trimmed)
                        return normalize_payload(parsed)
                    except json.JSONDecodeError:
                        continue
        
        raise ValueError("No valid JSON array detected")
    
    def _deduplicate_edges(self, edges: List[Edge]) -> List[Edge]:
        """Remove duplicate edges (same source, target, type)"""
        seen = set()
        unique_edges = []
        
        for edge in edges:
            key = (edge.source, edge.target, edge.type)
            if key not in seen:
                seen.add(key)
                unique_edges.append(edge)
        
        return unique_edges
    
    async def enhance_with_heuristics(
        self,
        llm_edges: List[Edge],
        entities: List[Entity],
        graph_id: str,
        existing_narrative_edges: List[Edge] = None
    ) -> List[Edge]:
        """
        Add heuristic-based edges to supplement LLM findings.
        Use for obvious relationships that don't need LLM reasoning.
        
        Args:
            llm_edges: Edges detected by LLM
            entities: All entities
            graph_id: Graph identifier
            existing_narrative_edges: Edges from narrative extraction (to avoid duplicates)
        """
        if existing_narrative_edges is None:
            existing_narrative_edges = []
        
        heuristic_edges = []
        
        # Create entity lookup
        entity_map = {e.id: e for e in entities}
        
        # Find main company (first company)
        companies = [e for e in entities if e.type == EntityType.COMPANY]
        main_company = companies[0] if companies else None
        
        if main_company:
            # Link all metrics to main company (common pattern)
            for entity in entities:
                if entity.type == EntityType.METRIC:
                    # Check if LLM already created this edge
                    existing = any(
                        e.source == main_company.id and e.target == entity.id and e.type == EdgeType.HAS_METRIC
                        for e in llm_edges
                    )
                    if not existing:
                        edge = Edge(
                            id=f"edge_{uuid.uuid4().hex[:12]}",
                            source=main_company.id,
                            target=entity.id,
                            type=EdgeType.HAS_METRIC,
                            graph_id=graph_id,
                            properties={"detected_by": "heuristic"}
                        )
                        heuristic_edges.append(edge)
        
        # Generic Heuristic: Group entities by shared property values
        # This works for ANY document type (locations→county, companies→industry, etc.)
        property_edges = self._create_shared_property_edges(
            entities, llm_edges + heuristic_edges + existing_narrative_edges, graph_id
        )
        heuristic_edges.extend(property_edges)
        
        if len(property_edges) > 0:
            logger.info(f"Added {len(property_edges)} property-based relationships")
        
        logger.info(f"Added {len(heuristic_edges)} heuristic edges total")
        
        # Combine and deduplicate
        all_edges = llm_edges + heuristic_edges
        return self._deduplicate_edges(all_edges)
    
    def _create_shared_property_edges(
        self,
        entities: List[Entity],
        existing_edges: List[Edge],
        graph_id: str
    ) -> List[Edge]:
        """
        Create edges between entities that share meaningful property values.
        Generic approach that works for any document type:
        - Locations with same county/state/country
        - Companies with same industry/sector
        - Loans with same lender/guarantor
        - Contracts with same parties
        """
        new_edges = []
        
        # Properties that indicate grouping relationships
        grouping_properties = [
            "county", "state", "country", "region",  # Locations
            "industry", "sector", "parent_company",   # Companies
            "lender", "guarantor", "creditor",        # Financial
            "party", "vendor", "supplier"             # Contracts/Transactions
        ]
        
        # Group entities by each property
        for prop_name in grouping_properties:
            groups: Dict[str, List[Entity]] = {}
            
            for entity in entities:
                prop_value = (entity.properties or {}).get(prop_name)
                if not prop_value or prop_value in [None, "", 0, "0", "null", "none"]:
                    continue
                
                value_str = str(prop_value).strip()
                if not value_str or value_str.lower() in ['null', 'none', '0', 'n/a']:
                    continue
                
                groups.setdefault(value_str, []).append(entity)
            
            # Create relationships within each group
            for prop_value, group_entities in groups.items():
                if len(group_entities) < 2:
                    continue
                
                logger.debug(f"Found {len(group_entities)} entities with {prop_name}='{prop_value}'")
                
                for i, source in enumerate(group_entities):
                    for target in group_entities[i + 1:]:
                        # Check if edge already exists
                        existing = any(
                            (e.source == source.id and e.target == target.id) or
                            (e.source == target.id and e.target == source.id)
                            for e in existing_edges + new_edges
                        )
                        if existing:
                            continue
                        
                        # Determine relationship type based on property
                        if prop_name in ["county", "state", "country", "region"]:
                            rel_type = EdgeType.LOCATED_IN if prop_name == "county" else EdgeType.RELATED_TO
                            reasoning = f"Both entities share {prop_name}: {prop_value}"
                        elif prop_name in ["industry", "sector"]:
                            rel_type = EdgeType.RELATED_TO
                            reasoning = f"Both operate in {prop_name}: {prop_value}"
                        elif prop_name in ["lender", "guarantor", "creditor"]:
                            rel_type = EdgeType.RELATED_TO
                            reasoning = f"Both involve {prop_name}: {prop_value}"
                        else:
                            rel_type = EdgeType.RELATED_TO
                            reasoning = f"Both share {prop_name}: {prop_value}"
                        
                        edge = Edge(
                            id=f"edge_{uuid.uuid4().hex[:12]}",
                            source=source.id,
                            target=target.id,
                            type=rel_type,
                            graph_id=graph_id,
                            properties={
                                "detected_by": "heuristic",
                                "relationship": f"shared_{prop_name}",
                                prop_name: prop_value,
                                "confidence": 0.9,
                                "reasoning": reasoning
                            }
                        )
                        new_edges.append(edge)
        
        return new_edges


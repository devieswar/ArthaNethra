"""
Narrative text parser for extracting entities AND relationships from unstructured prose
Handles risk disclosures, business descriptions, and other narrative content
"""
import re
import uuid
import json
import boto3
from typing import Dict, Any, List, Tuple, Optional
from bs4 import BeautifulSoup
from loguru import logger

from config import settings
from models.entity import Entity, EntityType
from models.edge import Edge, EdgeType
from models.citation import Citation


class NarrativeParser:
    """Extract entities AND relationships from narrative/prose text using NLP patterns + LLM"""
    
    def __init__(self):
        # Initialize Bedrock client for LLM-based extraction
        self.bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        
        # Use cheaper/faster Haiku for narrative extraction (many chunks)
        # This is ~10x cheaper than Sonnet and faster
        self.narrative_model = "us.anthropic.claude-3-5-haiku-20241022-v1:0"  # Haiku 3.5
        # Fallback to Sonnet if Haiku not available
        self.fallback_model = settings.BEDROCK_MODEL_ID
        
        # Entity patterns for detecting organizations, money, dates, etc.
        self.patterns = {
            "ORGANIZATION": [
                r'\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:Inc\.?|LLC|Ltd\.?|Corporation|Corp\.?|Company|Co\.?)\b',
                r'\b(?:Bitcoin|Ethereum|USDC|DocuSign|Apple|Microsoft|Amazon|Google|Circle)\b',
            ],
            "MONEY": [
                r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:million|billion|trillion|M|B|T))?',
                r'\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars|USD)',
            ],
            "DATE": [
                r'\b\d{4}\b',  # Year
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            ],
            "PERSON": [
                r'\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',
            ],
            "LOCATION": [
                r'\b(?:United States|USA|U\.S\.|California|New York|Texas|London|Singapore)\b',
            ],
        }
        
        # Risk/topic patterns
        self.risk_patterns = [
            r'^##?\s*(.+?)(?:\n|$)',  # Markdown headers
            r'^([A-Z][^.!?]*(?:risk|Risk|RISK)[^.!?]*)[.!?]',  # Sentences with "risk"
            r'^([^.!?]{10,200})[.!?]',  # General sentences (first 200 chars)
        ]
        
        # Edge type mapping
        self.edge_type_mapping = {
            "RELATED_TO": EdgeType.RELATED_TO,
            "HAS_RISK": EdgeType.RELATED_TO,
            "DEPENDS_ON": EdgeType.RELATED_TO,
            "MENTIONED_IN": EdgeType.MENTIONED_IN,
            "PARTNERS_WITH": EdgeType.RELATED_TO,
            "ISSUES": EdgeType.ISSUED_BY,
            "PROVIDES": EdgeType.SUPPLIES_TO,
        }
    
    def extract_entities_from_narrative(
        self,
        markdown: str,
        document_id: str,
        graph_id: str,
        max_entities: int = 200
    ) -> List[Entity]:
        """
        Extract entities from narrative text
        
        Returns:
            List of entities including organizations, money amounts, dates, risks, etc.
        """
        logger.info(f"Parsing narrative text ({len(markdown)} chars)")
        
        soup = BeautifulSoup(markdown, 'html.parser')
        text = soup.get_text()
        
        entities = []
        entity_set = set()  # Prevent duplicates
        
        # Extract named entities (organizations, money, dates, people, locations)
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    entity_text = match.group(0).strip()
                    
                    # Skip if duplicate or too short
                    if entity_text in entity_set or len(entity_text) < 3:
                        continue
                    
                    entity_set.add(entity_text)
                    
                    # Map to our entity types
                    our_type = self._map_entity_type(entity_type)
                    
                    entity = Entity(
                        id=f"entity_{uuid.uuid4().hex[:12]}",
                        name=entity_text,
                        type=our_type,
                        display_type=self._format_display_type(entity_type, our_type, entity_text),
                        original_type=entity_type,
                        properties={
                            "extracted_from": "narrative_text",
                            "source_type": entity_type,
                            "document_id": document_id,
                            "graph_id": graph_id,
                        },
                        document_id=document_id,
                        graph_id=graph_id
                    )
                    
                    entities.append(entity)
                    
                    if len(entities) >= max_entities:
                        break
                
                if len(entities) >= max_entities:
                    break
            
            if len(entities) >= max_entities:
                break
        
        # Extract risk/topic entities from paragraphs
        risk_entities = self._extract_risk_entities(text, document_id, graph_id)
        entities.extend(risk_entities[:max_entities - len(entities)])
        
        logger.info(f"Extracted {len(entities)} entities from narrative text")
        
        return entities
    
    def _extract_risk_entities(
        self,
        text: str,
        document_id: str,
        graph_id: str,
        max_risks: int = 50
    ) -> List[Entity]:
        """Extract risk/topic entities from paragraph text"""
        risks = []
        risk_set = set()
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
        
        for para in paragraphs[:max_risks]:
            # Extract first sentence or first 200 chars as risk description
            first_sentence = re.match(r'^([^.!?]{20,250})[.!?]', para)
            if first_sentence:
                risk_text = first_sentence.group(1).strip()
            else:
                risk_text = para[:200].strip()
            
            # Skip duplicates
            if risk_text in risk_set or len(risk_text) < 20:
                continue
            
            risk_set.add(risk_text)
            
            # Create a CLAUSE entity for each risk/topic
            risk_entity = Entity(
                id=f"risk_{uuid.uuid4().hex[:12]}",
                name=risk_text[:100],  # Use first 100 chars as name
                type=EntityType.CLAUSE,
                display_type="Risk",
                original_type="RISK",
                properties={
                    "description": risk_text,
                    "full_text": para[:500],  # Store up to 500 chars of context
                    "category": "risk" if "risk" in para.lower() else "narrative",
                    "extracted_from": "narrative_paragraph",
                    "document_id": document_id,
                    "graph_id": graph_id,
                },
                document_id=document_id,
                graph_id=graph_id
            )
            
            risks.append(risk_entity)
            
            if len(risks) >= max_risks:
                break
        
        return risks
    
    def _map_entity_type(self, raw_type: str) -> EntityType:
        """Map raw entity types to our EntityType enum"""
        mapping = {
            "ORGANIZATION": EntityType.COMPANY,
            "MONEY": EntityType.METRIC,
            "DATE": EntityType.METRIC,
            "PERSON": EntityType.PERSON,
            "LOCATION": EntityType.LOCATION,
        }
        return mapping.get(raw_type, EntityType.CLAUSE)
    
    async def extract_entities_and_relationships_from_chunks(
        self,
        markdown: str,
        document_id: str,
        graph_id: str,
        chunk_size: int = 1000
    ) -> Tuple[List[Entity], List[Edge]]:
        """
        Extract entities AND relationships directly from text chunks using LLM.
        This preserves the narrative context that connects entities.
        
        Args:
            markdown: Full markdown text
            document_id: Document identifier
            graph_id: Graph identifier
            chunk_size: Characters per chunk
            
        Returns:
            Tuple of (entities, edges) extracted from narrative
        """
        logger.info(f"Extracting entities + relationships from narrative ({len(markdown)} chars)")
        
        soup = BeautifulSoup(markdown, 'html.parser')
        text = soup.get_text()
        
        # Split into manageable chunks (by paragraph boundaries)
        chunks = self._chunk_text(text, chunk_size)
        logger.info(f"Processing {len(chunks)} text chunks")
        
        all_entities = []
        all_edges = []
        entity_map = {}  # Track entities by name to avoid duplicates
        
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # Skip tiny chunks
                continue
            
            logger.info(f"🤖 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            
            try:
                chunk_entities, chunk_edges = await self._extract_from_chunk_with_llm(
                    chunk, document_id, graph_id, entity_map
                )
                
                # Add new entities
                for entity in chunk_entities:
                    if entity.name not in entity_map:
                        entity_map[entity.name] = entity
                        all_entities.append(entity)
                
                all_edges.extend(chunk_edges)
                
                logger.info(f"Chunk {i+1}: {len(chunk_entities)} entities, {len(chunk_edges)} relationships")
                
            except Exception as e:
                logger.warning(f"Failed to process chunk {i+1}: {e}")
                continue
        
        logger.info(f"Extracted {len(all_entities)} entities and {len(all_edges)} relationships from narrative")
        
        return all_entities, all_edges
    
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks at paragraph boundaries"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def _extract_from_chunk_with_llm(
        self,
        chunk: str,
        document_id: str,
        graph_id: str,
        existing_entity_map: Dict[str, Entity]
    ) -> Tuple[List[Entity], List[Edge]]:
        """Use LLM to extract entities and relationships from a single text chunk"""
        
        system_prompt = """You are a financial document analysis expert. Extract entities and relationships from text.

Extract:
1. **Entities**: Organizations, people, locations, monetary amounts, dates, risks/topics
2. **Relationships**: How entities are connected in the text

Respond with JSON:
{
  "entities": [
    {
      "name": "Bitcoin",
      "type": "ORGANIZATION|PERSON|LOCATION|MONEY|DATE|RISK",
      "properties": {"industry": "cryptocurrency", "description": "..."}
    }
  ],
  "relationships": [
    {
      "source_name": "DocuSign",
      "target_name": "USDC",
      "relationship_type": "PARTNERS_WITH|DEPENDS_ON|ISSUES|PROVIDES|HAS_RISK|RELATED_TO",
      "reasoning": "DocuSign partners with Circle for USDC services"
    }
  ]
}

**IMPORTANT**:
- Extract ALL entities mentioned (companies, people, places, amounts, dates, concepts)
- Capture ALL relationships explicitly stated in the text
- Use entity names exactly as they appear
- Provide clear reasoning for each relationship"""

        user_prompt = f"""Analyze this text and extract entities + relationships:

{chunk[:1500]}  

Provide JSON response."""

        try:
            # Try Haiku first (10x cheaper, 2x faster)
            try:
                response = self.bedrock.invoke_model(
                    modelId=self.narrative_model,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2048,
                        "temperature": 0.3,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_prompt}]
                    })
                )
                logger.debug("Using Haiku for narrative extraction (cost-optimized)")
            except Exception as haiku_error:
                logger.warning(f"Haiku failed, falling back to Sonnet: {haiku_error}")
                response = self.bedrock.invoke_model(
                    modelId=self.fallback_model,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2048,
                        "temperature": 0.3,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_prompt}]
                    })
                )
            
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            
            llm_response = None
            for block in content:
                if block.get('type') == 'text':
                    llm_response = block.get('text', '')
                    break
            
            if not llm_response:
                return [], []
            
            # Parse JSON
            data = self._parse_json_response(llm_response)
            
            # Convert to Entity and Edge objects
            entities = []
            edges = []
            
            # Create entities
            for ent_data in data.get("entities", []):
                entity_name = ent_data.get("name", "").strip()
                if not entity_name or entity_name in existing_entity_map:
                    continue  # Skip duplicates
                
                entity_type_str = ent_data.get("type", "RISK")
                entity_type = self._map_llm_entity_type(entity_type_str)
                display_type = ent_data.get("display_type") or self._format_display_type(
                    entity_type_str,
                    entity_type,
                    entity_name
                )
                
                entity = Entity(
                    id=f"entity_{uuid.uuid4().hex[:12]}",
                    name=entity_name,
                    type=entity_type,
                    display_type=display_type,
                    original_type=entity_type_str,
                    properties={
                        **ent_data.get("properties", {}),
                        "extracted_from": "narrative_llm",
                        "document_id": document_id,
                        "graph_id": graph_id,
                    },
                    document_id=document_id,
                    graph_id=graph_id
                )
                entities.append(entity)
            
            # Create temporary map including new entities
            temp_entity_map = {**existing_entity_map}
            for entity in entities:
                temp_entity_map[entity.name] = entity
            
            # Create edges
            for rel_data in data.get("relationships", []):
                source_name = rel_data.get("source_name", "").strip()
                target_name = rel_data.get("target_name", "").strip()
                
                # Find entities
                source_entity = temp_entity_map.get(source_name)
                target_entity = temp_entity_map.get(target_name)
                
                if not source_entity or not target_entity:
                    continue  # Skip if entities not found
                
                edge_type_str = rel_data.get("relationship_type", "RELATED_TO")
                edge_type = self.edge_type_mapping.get(edge_type_str, EdgeType.RELATED_TO)
                
                edge = Edge(
                    id=f"edge_{uuid.uuid4().hex[:12]}",
                    source=source_entity.id,
                    target=target_entity.id,
                    type=edge_type,
                    graph_id=graph_id,
                    properties={
                        "reasoning": rel_data.get("reasoning", ""),
                        "detected_by": "narrative_llm",
                        "confidence": 0.85
                    }
                )
                edges.append(edge)
            
            return entities, edges
            
        except Exception as e:
            logger.error(f"Error in LLM extraction from chunk: {e}")
            return [], []
    
    def _parse_json_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        # Try to find JSON in code blocks
        fenced_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', llm_response, re.IGNORECASE)
        if fenced_match:
            json_str = fenced_match.group(1)
        else:
            json_str = llm_response
        
        # Try to parse
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to find JSON object
            match = re.search(r'\{[\s\S]+\}', json_str)
            if match:
                return json.loads(match.group(0))
            return {"entities": [], "relationships": []}
    
    def _map_llm_entity_type(self, llm_type: str) -> EntityType:
        """Map LLM entity type strings to our EntityType enum"""
        mapping = {
            "ORGANIZATION": EntityType.COMPANY,
            "COMPANY": EntityType.COMPANY,
            "PERSON": EntityType.PERSON,
            "LOCATION": EntityType.LOCATION,
            "MONEY": EntityType.METRIC,
            "DATE": EntityType.METRIC,
            "RISK": EntityType.CLAUSE,
            "TOPIC": EntityType.CLAUSE,
            "CONCEPT": EntityType.CLAUSE,
        }
        return mapping.get(llm_type.upper(), EntityType.CLAUSE)

    def _format_display_type(self, raw_type: Optional[str], fallback: EntityType, name: Optional[str]) -> str:
        if raw_type:
            label = raw_type.strip()
            if label:
                if label.lower().startswith("entitytype."):
                    label = label.split(".", 1)[-1]
                if label.isupper():
                    label = label.replace("_", " ").title()
                return label
        if name:
            return name
        return fallback.value


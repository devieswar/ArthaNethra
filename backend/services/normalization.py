"""
Graph normalization service - converts ADE output to graph entities and edges
"""
import uuid
from typing import Dict, Any, List, Tuple
from loguru import logger

from models.entity import Entity, EntityType
from models.edge import Edge, EdgeType
from models.citation import Citation


class NormalizationService:
    """Converts ADE extraction results to knowledge graph entities and relationships"""
    
    def __init__(self):
        self.entity_type_mapping = {
            "ORGANIZATION": EntityType.COMPANY,
            "COMPANY": EntityType.COMPANY,
            "SUBSIDIARY": EntityType.SUBSIDIARY,
            "LOAN": EntityType.LOAN,
            "DEBT": EntityType.LOAN,
            "INVOICE": EntityType.INVOICE,
            "METRIC": EntityType.METRIC,
            "FINANCIAL_METRIC": EntityType.METRIC,
            "CONTRACT": EntityType.CLAUSE,
            "CLAUSE": EntityType.CLAUSE,
            "PERSON": EntityType.PERSON,
            "LOCATION": EntityType.LOCATION,
            "VENDOR": EntityType.VENDOR
        }
    
    async def normalize_to_graph(
        self,
        ade_output: Dict[str, Any],
        document_id: str
    ) -> Tuple[List[Entity], List[Edge]]:
        """
        Convert ADE output to graph entities and edges
        
        Args:
            ade_output: Parsed ADE extraction results
            document_id: Source document ID
            
        Returns:
            Tuple of (entities, edges)
        """
        logger.info(f"Normalizing ADE output for document: {document_id}")
        
        graph_id = f"graph_{uuid.uuid4().hex[:12]}"
        
        # Create entities
        entities = await self._create_entities(
            ade_output,
            document_id,
            graph_id
        )
        
        # Create relationships
        edges = await self._create_edges(
            entities,
            ade_output,
            graph_id
        )
        
        logger.info(
            f"Normalized graph: {len(entities)} entities, {len(edges)} edges"
        )
        
        return entities, edges
    
    async def _create_entities(
        self,
        ade_output: Dict[str, Any],
        document_id: str,
        graph_id: str
    ) -> List[Entity]:
        """Create entities from ADE output"""
        entities = []
        entity_map = {}
        
        # Process extracted entities
        for entity_data in ade_output.get("entities", []):
            entity_type = self._map_entity_type(entity_data.get("type"))
            
            if not entity_type:
                continue
            
            # Create citations
            citations = [
                Citation(**citation_data)
                for citation_data in entity_data.get("citations", [])
            ]
            
            # Create entity
            entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=entity_type,
                name=entity_data.get("name"),
                properties=entity_data.get("properties", {}),
                citations=citations,
                document_id=document_id,
                graph_id=graph_id
            )
            
            entities.append(entity)
            entity_map[entity.name] = entity
        
        # Extract entities from tables
        for table in ade_output.get("tables", []):
            table_entities = await self._extract_entities_from_table(
                table,
                document_id,
                graph_id
            )
            entities.extend(table_entities)
        
        # Fallback: if no entities and we have key_values (e.g., only a summary),
        # create a summary entity and basic metric entities extracted from text.
        if not entities:
            kvs = ade_output.get("key_values", []) or []
            summary_text = None
            for kv in kvs:
                if isinstance(kv, dict) and kv.get("key") == "summary" and isinstance(kv.get("value"), str):
                    summary_text = kv.get("value").strip()
                    break
            if summary_text:
                # Summary entity
                summary_entity = Entity(
                    id=f"ent_{uuid.uuid4().hex[:12]}",
                    type=EntityType.CLAUSE,
                    name="Document Summary",
                    properties={"text": summary_text},
                    citations=[],
                    document_id=document_id,
                    graph_id=graph_id
                )
                entities.append(summary_entity)
                # Basic metrics from text (percentages, currency amounts)
                metrics = self._extract_metrics_from_text(summary_text)
                for metric in metrics:
                    metric_entity = Entity(
                        id=f"ent_{uuid.uuid4().hex[:12]}",
                        type=EntityType.METRIC,
                        name=metric["name"],
                        properties={"value": metric["value"], "unit": metric.get("unit")},
                        citations=[],
                        document_id=document_id,
                        graph_id=graph_id
                    )
                    entities.append(metric_entity)
                # Map for potential edges
                entity_map[summary_entity.name] = summary_entity
        
        return entities
    
    async def _create_edges(
        self,
        entities: List[Entity],
        ade_output: Dict[str, Any],
        graph_id: str
    ) -> List[Edge]:
        """Create edges (relationships) between entities"""
        edges = []
        
        # Create entity lookup
        entity_lookup = {entity.name: entity for entity in entities}
        
        # Infer relationships based on entity types and proximity
        for i, entity in enumerate(entities):
            # Company-Subsidiary relationships
            if entity.type == EntityType.COMPANY:
                for other in entities[i+1:]:
                    if other.type == EntityType.SUBSIDIARY:
                        edge = Edge(
                            id=f"edge_{uuid.uuid4().hex[:12]}",
                            source=entity.id,
                            target=other.id,
                            type=EdgeType.OWNS,
                            graph_id=graph_id,
                            properties={}
                        )
                        edges.append(edge)
            
            # Company-Loan relationships
            if entity.type == EntityType.COMPANY:
                for other in entities[i+1:]:
                    if other.type == EntityType.LOAN:
                        edge = Edge(
                            id=f"edge_{uuid.uuid4().hex[:12]}",
                            source=entity.id,
                            target=other.id,
                            type=EdgeType.HAS_LOAN,
                            graph_id=graph_id,
                            properties=other.properties
                        )
                        edges.append(edge)
            
            # Company-Metric relationships
            if entity.type == EntityType.COMPANY:
                for other in entities[i+1:]:
                    if other.type == EntityType.METRIC:
                        edge = Edge(
                            id=f"edge_{uuid.uuid4().hex[:12]}",
                            source=entity.id,
                            target=other.id,
                            type=EdgeType.HAS_METRIC,
                            graph_id=graph_id,
                            properties=other.properties
                        )
                        edges.append(edge)

            # Link summary to metrics if present
            if entity.type == EntityType.CLAUSE and entity.name == "Document Summary":
                for other in entities:
                    if other.type == EntityType.METRIC:
                        edge = Edge(
                            id=f"edge_{uuid.uuid4().hex[:12]}",
                            source=entity.id,
                            target=other.id,
                            type=EdgeType.HAS_METRIC,
                            graph_id=graph_id,
                            properties={}
                        )
                        edges.append(edge)
        
        return edges
    
    def _map_entity_type(self, ade_type: str) -> EntityType:
        """Map ADE entity type to internal EntityType"""
        return self.entity_type_mapping.get(ade_type.upper())

    def _extract_metrics_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract simple metrics from free text: percentages and currency amounts."""
        import re
        metrics: List[Dict[str, Any]] = []
        # Percentages (e.g., 8%, 9.2%)
        for match in re.finditer(r"(\d{1,3}(?:\.\d{1,2})?)%", text):
            value = float(match.group(1))
            metrics.append({"name": f"percentage_{match.group(1)}%", "value": value, "unit": "%"})
        # Currency amounts (very simple matcher: $50M, $12M, $8.3M, 50M)
        for match in re.finditer(r"\$?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)(\s*[MBKmbk])?", text):
            raw = match.group(1)
            unit = (match.group(2) or '').strip().upper()
            try:
                num = float(raw.replace(',', ''))
            except Exception:
                continue
            # Normalize units
            multiplier = 1.0
            if unit == 'K':
                multiplier = 1e3
            elif unit == 'M':
                multiplier = 1e6
            elif unit == 'B':
                multiplier = 1e9
            value = num * multiplier
            metrics.append({"name": f"amount_{raw}{unit}", "value": value, "unit": "USD"})
        return metrics
    
    async def _extract_entities_from_table(
        self,
        table: Dict[str, Any],
        document_id: str,
        graph_id: str
    ) -> List[Entity]:
        """Extract entities from table data"""
        entities = []
        
        # Example: Extract loan entities from debt schedule tables
        if "debt" in table.get("caption", "").lower():
            for row in table.get("rows", []):
                # Create loan entity from row
                entity = Entity(
                    id=f"ent_{uuid.uuid4().hex[:12]}",
                    type=EntityType.LOAN,
                    name=row.get("description", "Unknown Loan"),
                    properties={
                        "principal": row.get("principal"),
                        "rate": row.get("interest_rate"),
                        "maturity": row.get("maturity_date")
                    },
                    citations=[Citation(
                        page=table.get("page"),
                        table_id=table.get("id")
                    )],
                    document_id=document_id,
                    graph_id=graph_id
                )
                entities.append(entity)
        
        return entities


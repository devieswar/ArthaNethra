"""
Indexing service for Weaviate and Neo4j
"""
import weaviate
from neo4j import GraphDatabase
from typing import List
from loguru import logger

from config import settings
from models.entity import Entity
from models.edge import Edge


class IndexingService:
    """Handles indexing entities and edges in vector and graph databases"""
    
    def __init__(self):
        # Weaviate client
        self.weaviate_client = weaviate.Client(
            url=settings.WEAVIATE_URL,
            auth_client_secret=weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY) if settings.WEAVIATE_API_KEY else None
        )
        
        # Neo4j driver (optional)
        try:
            self.neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        except Exception as e:
            logger.warning(f"Neo4j not available: {e}")
            self.neo4j_driver = None
        
        self._init_weaviate_schema()
    
    def _init_weaviate_schema(self):
        """Initialize Weaviate schema for entities"""
        schema = {
            "classes": [
                {
                    "class": "FinancialEntity",
                    "description": "Financial entities from documents",
                    "vectorizer": "text2vec-transformers",
                    "properties": [
                        {
                            "name": "entityId",
                            "dataType": ["string"],
                            "description": "Unique entity identifier"
                        },
                        {
                            "name": "entityType",
                            "dataType": ["string"],
                            "description": "Type of entity"
                        },
                        {
                            "name": "name",
                            "dataType": ["string"],
                            "description": "Entity name"
                        },
                        {
                            "name": "properties",
                            "dataType": ["text"],
                            "description": "JSON-encoded properties"
                        },
                        {
                            "name": "citations",
                            "dataType": ["text"],
                            "description": "JSON-encoded citations"
                        },
                        {
                            "name": "documentId",
                            "dataType": ["string"],
                            "description": "Source document ID"
                        },
                        {
                            "name": "graphId",
                            "dataType": ["string"],
                            "description": "Knowledge graph ID"
                        }
                    ]
                }
            ]
        }
        
        try:
            existing_schema = self.weaviate_client.schema.get()
            if not any(c["class"] == "FinancialEntity" for c in existing_schema.get("classes", [])):
                self.weaviate_client.schema.create(schema)
                logger.info("Weaviate schema created")
        except Exception as e:
            logger.error(f"Error initializing Weaviate schema: {e}")
    
    async def index_entities(self, entities: List[Entity]) -> dict:
        """
        Index entities in Weaviate and Neo4j
        
        Args:
            entities: List of entities to index
            
        Returns:
            dict: Indexing statistics
        """
        logger.info(f"Indexing {len(entities)} entities")
        
        weaviate_count = await self._index_to_weaviate(entities)
        neo4j_count = 0
        
        if self.neo4j_driver:
            neo4j_count = await self._index_to_neo4j(entities)
        
        return {
            "weaviate": {"entities_count": weaviate_count},
            "neo4j": {"nodes_count": neo4j_count}
        }
    
    async def index_edges(self, edges: List[Edge]) -> dict:
        """
        Index edges in Neo4j
        
        Args:
            edges: List of edges to index
            
        Returns:
            dict: Indexing statistics
        """
        if not self.neo4j_driver:
            logger.warning("Neo4j not available, skipping edge indexing")
            return {"neo4j": {"relationships_count": 0}}
        
        logger.info(f"Indexing {len(edges)} edges")
        
        with self.neo4j_driver.session() as session:
            for edge in edges:
                session.run(
                    """
                    MATCH (a {entityId: $source})
                    MATCH (b {entityId: $target})
                    CREATE (a)-[r:RELATIONSHIP {
                        edgeId: $edgeId,
                        type: $type,
                        properties: $properties
                    }]->(b)
                    """,
                    source=edge.source,
                    target=edge.target,
                    edgeId=edge.id,
                    type=edge.type.value,
                    properties=str(edge.properties)
                )
        
        return {"neo4j": {"relationships_count": len(edges)}}
    
    async def _index_to_weaviate(self, entities: List[Entity]) -> int:
        """Index entities to Weaviate"""
        import json
        
        batch_size = 100
        indexed_count = 0
        
        with self.weaviate_client.batch as batch:
            batch.batch_size = batch_size
            
            for entity in entities:
                data_object = {
                    "entityId": entity.id,
                    "entityType": entity.type.value,
                    "name": entity.name,
                    "properties": json.dumps(entity.properties),
                    "citations": json.dumps([c.model_dump() for c in entity.citations]),
                    "documentId": entity.document_id,
                    "graphId": entity.graph_id
                }
                
                batch.add_data_object(data_object, "FinancialEntity")
                indexed_count += 1
        
        logger.info(f"Indexed {indexed_count} entities to Weaviate")
        return indexed_count
    
    async def _index_to_neo4j(self, entities: List[Entity]) -> int:
        """Index entities as nodes in Neo4j"""
        with self.neo4j_driver.session() as session:
            for entity in entities:
                session.run(
                    """
                    CREATE (n:Entity {
                        entityId: $entityId,
                        type: $type,
                        name: $name,
                        properties: $properties,
                        documentId: $documentId,
                        graphId: $graphId
                    })
                    """,
                    entityId=entity.id,
                    type=entity.type.value,
                    name=entity.name,
                    properties=str(entity.properties),
                    documentId=entity.document_id,
                    graphId=entity.graph_id
                )
        
        logger.info(f"Indexed {len(entities)} entities to Neo4j")
        return len(entities)
    
    async def query_entities(
        self,
        query_text: str,
        limit: int = 10,
        filters: dict = None
    ) -> List[dict]:
        """
        Semantic search for entities
        
        Args:
            query_text: Search query
            limit: Max results
            filters: Additional filters
            
        Returns:
            List of matching entities
        """
        result = (
            self.weaviate_client.query
            .get("FinancialEntity", ["entityId", "name", "entityType", "properties", "citations"])
            .with_near_text({"concepts": [query_text]})
            .with_limit(limit)
            .do()
        )
        
        entities = result.get("data", {}).get("Get", {}).get("FinancialEntity", [])
        return entities
    
    def __del__(self):
        """Close connections"""
        if self.neo4j_driver:
            self.neo4j_driver.close()


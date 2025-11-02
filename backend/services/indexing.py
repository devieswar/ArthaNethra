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
        # Defaults to None; attempt connections but don't fail startup
        self.weaviate_client = None
        self.neo4j_driver = None
        
        # Weaviate client (optional)
        if getattr(settings, "ENABLE_WEAVIATE", False) and settings.WEAVIATE_URL:
            try:
                # Parse WEAVIATE_URL to extract host and port
                url = settings.WEAVIATE_URL
                if url.startswith("http://"):
                    url = url[7:]
                elif url.startswith("https://"):
                    url = url[8:]
                
                # Extract host and port
                if ":" in url:
                    host, port = url.split(":")
                    port = int(port)
                else:
                    host = url
                    port = 8080
                
                # Connect to Weaviate
                auth = None
                if settings.WEAVIATE_API_KEY:
                    auth = weaviate.auth.Auth.api_key(settings.WEAVIATE_API_KEY)
                
                self.weaviate_client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    grpc_port=50051,
                    auth_credentials=auth
                )
                logger.info(f"Weaviate connected at {host}:{port}")
            except Exception as e:
                logger.warning(f"Weaviate not available: {e}")
                self.weaviate_client = None
        else:
            logger.info("Weaviate indexing disabled by config")
        
        # Neo4j driver (optional)
        if getattr(settings, "ENABLE_NEO4J", False):
            try:
                self.neo4j_driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                logger.info("Neo4j connected")
            except Exception as e:
                logger.warning(f"Neo4j not available: {e}")
                self.neo4j_driver = None
        else:
            logger.info("Neo4j indexing disabled by config")
        
        self._init_weaviate_schema()
    
    def _init_weaviate_schema(self):
        """Initialize Weaviate schema for entities"""
        if not self.weaviate_client:
            return
        
        # Weaviate v4 uses collections API
        try:
            # Check if collection already exists
            if self.weaviate_client.collections.exists("FinancialEntity"):
                logger.info("FinancialEntity collection already exists")
                return
            
            # Create the collection with properties
            collection = self.weaviate_client.collections.create(
                name="FinancialEntity",
                description="Financial entities from documents",
                vector_config=weaviate.classes.config.Configure.Vectors.text2vec_transformers(),
                properties=[
                    weaviate.classes.config.Property(
                        name="entityId",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Unique entity identifier"
                    ),
                    weaviate.classes.config.Property(
                        name="entityType",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Type of entity"
                    ),
                    weaviate.classes.config.Property(
                        name="name",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Entity name"
                    ),
                    weaviate.classes.config.Property(
                        name="properties",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="JSON-encoded properties"
                    ),
                    weaviate.classes.config.Property(
                        name="citations",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="JSON-encoded citations"
                    ),
                    weaviate.classes.config.Property(
                        name="documentId",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Source document ID"
                    ),
                    weaviate.classes.config.Property(
                        name="graphId",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Knowledge graph ID"
                    )
                ]
            )
            logger.info("FinancialEntity collection created successfully")
        except Exception as e:
            logger.error(f"Error initializing Weaviate collection: {e}")
    
    async def index_entities(self, entities: List[Entity]) -> dict:
        """
        Index entities in Weaviate and Neo4j
        
        Args:
            entities: List of entities to index
            
        Returns:
            dict: Indexing statistics
        """
        logger.info(f"Indexing {len(entities)} entities")
        
        weaviate_count = 0
        if self.weaviate_client:
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
        
        try:
            collection = self.weaviate_client.collections.get("FinancialEntity")
            
            with collection.batch.fixed_size(batch_size=100) as batch:
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
                    
                    batch.add_object(data_object)
            
            logger.info(f"Indexed {len(entities)} entities to Weaviate")
            return len(entities)
        except Exception as e:
            logger.error(f"Error indexing to Weaviate: {e}")
            return 0
    
    async def _index_to_neo4j(self, entities: List[Entity]) -> int:
        """Index entities as nodes in Neo4j"""
        try:
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
        except Exception as e:
            logger.error(f"Error indexing to Neo4j: {e}")
            return 0
    
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
        if not self.weaviate_client:
            return []
        
        try:
            collection = self.weaviate_client.collections.get("FinancialEntity")
            
            result = collection.query.near_text(
                query=query_text,
                limit=limit
            )
            
            entities = []
            for obj in result.objects:
                entity = {
                    "entityId": obj.properties.get("entityId"),
                    "name": obj.properties.get("name"),
                    "entityType": obj.properties.get("entityType"),
                    "properties": obj.properties.get("properties"),
                    "citations": obj.properties.get("citations")
                }
                entities.append(entity)
            
            return entities
        except Exception as e:
            logger.error(f"Error querying Weaviate: {e}")
            return []
    
    def __del__(self):
        """Close connections"""
        try:
            if getattr(self, "weaviate_client", None):
                self.weaviate_client.close()
        except Exception:
            pass
        try:
            if getattr(self, "neo4j_driver", None):
                self.neo4j_driver.close()
        except Exception:
            pass

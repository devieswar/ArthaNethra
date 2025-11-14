"""
Indexing service for Weaviate and Neo4j
"""
import weaviate
from neo4j import GraphDatabase
from typing import List
from loguru import logger
import json

from config import settings
from models.entity import Entity
from models.edge import Edge


class IndexingService:
    """Handles indexing entities and edges in vector and graph databases"""
    
    def __init__(self):
        # Defaults to None; attempt connections but don't fail startup
        self.weaviate_client = None
        self.neo4j_driver = None
        
        self._connect_weaviate()
        
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
    
    def _connect_weaviate(self) -> bool:
        """Attempt to establish a connection to Weaviate if enabled."""
        if self.weaviate_client:
            return True
        
        if not (getattr(settings, "ENABLE_WEAVIATE", False) and settings.WEAVIATE_URL):
            logger.info("Weaviate indexing disabled by config")
            self.weaviate_client = None
            return False
        
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
            self._init_weaviate_schema()
            return True
        except Exception as e:
            logger.warning(f"Weaviate not available: {e}")
            self.weaviate_client = None
            return False
    
    def ensure_weaviate_client(self) -> bool:
        """
        Lazily ensure that a Weaviate connection exists.
        Useful when Weaviate was still starting up during backend boot.
        """
        if self.weaviate_client:
            return True
        return self._connect_weaviate()
    
    def _init_weaviate_schema(self):
        """Initialize Weaviate schema for entities and document chunks"""
        if not self.weaviate_client:
            return
        
        # Weaviate v4 uses collections API
        try:
            # Check if FinancialEntity collection exists
            if self.weaviate_client.collections.exists("FinancialEntity"):
                logger.info("FinancialEntity collection already exists")
            else:
                self._create_entity_collection()
            
            # Check if DocumentChunk collection exists
            if self.weaviate_client.collections.exists("DocumentChunk"):
                logger.info("DocumentChunk collection already exists")
            else:
                self._create_document_chunk_collection()
                
        except Exception as e:
            logger.error(f"Error initializing Weaviate schema: {e}")
    
    def _create_entity_collection(self):
        """Create FinancialEntity collection"""
        if not self.weaviate_client:
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
    
    def _create_document_chunk_collection(self):
        """Create DocumentChunk collection for full-text search"""
        collection = self.weaviate_client.collections.create(
            name="DocumentChunk",
            description="Document text chunks for semantic search",
            vector_config=weaviate.classes.config.Configure.Vectors.text2vec_transformers(),
            properties=[
                weaviate.classes.config.Property(
                    name="chunkId",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Unique chunk identifier"
                ),
                weaviate.classes.config.Property(
                    name="documentId",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Source document ID"
                ),
                weaviate.classes.config.Property(
                    name="content",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Chunk text content"
                ),
                weaviate.classes.config.Property(
                    name="chunkIndex",
                    data_type=weaviate.classes.config.DataType.INT,
                    description="Chunk position in document"
                ),
                weaviate.classes.config.Property(
                    name="pageNumber",
                    data_type=weaviate.classes.config.DataType.INT,
                    description="Approximate page number"
                ),
                weaviate.classes.config.Property(
                    name="filename",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Source filename"
                ),
                weaviate.classes.config.Property(
                    name="entityRefs",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="JSON array of entity IDs in this chunk"
                )
            ]
        )
        logger.info("DocumentChunk collection created successfully")
    
    async def index_entities(self, entities: List[Entity]) -> dict:
        """
        Index entities in Weaviate and Neo4j
        
        Args:
            entities: List of entities to index (can be Entity objects or dicts)
            
        Returns:
            dict: Indexing statistics
        """
        if not entities:
            logger.warning("No entities provided to index_entities")
            return {
                "weaviate": {"entities_count": 0},
                "neo4j": {"nodes_count": 0}
            }
        
        logger.info(f"Indexing {len(entities)} entities")
        
        # Check if entities are Entity objects or dicts
        if entities and isinstance(entities[0], dict):
            logger.info("Entities are dicts, converting to Entity objects")
            from models.entity import Entity, EntityType
            entity_objects = []
            for e_dict in entities:
                try:
                    entity = Entity(
                        id=e_dict.get("id", ""),
                        type=EntityType(e_dict.get("type", "")),
                        name=e_dict.get("name", ""),
                        properties=e_dict.get("properties", {}),
                        document_id=e_dict.get("document_id", ""),
                        graph_id=e_dict.get("graph_id", "")
                    )
                    entity_objects.append(entity)
                except Exception as e:
                    logger.warning(f"Failed to convert entity dict to Entity object: {e}")
            entities = entity_objects
        
        weaviate_count = 0
        if self.ensure_weaviate_client():
            weaviate_count = await self._index_to_weaviate(entities)
        
        neo4j_count = 0
        if self.neo4j_driver:
            neo4j_count = await self._index_to_neo4j(entities)
        
        logger.info(f"Indexing complete: {weaviate_count} to Weaviate, {neo4j_count} to Neo4j")
        
        return {
            "weaviate": {"entities_count": weaviate_count},
            "neo4j": {"nodes_count": neo4j_count}
        }
    
    async def index_document_text(self, document_id: str, markdown: str, filename: str, entities: List[Entity] = None, total_pages: int = None) -> dict:
        """
        Chunk and index full document text for semantic search
        
        Args:
            document_id: Document ID
            markdown: Full parsed markdown text
            filename: Original filename
            entities: Optional list of entities to link to chunks
            total_pages: Total number of pages in the document (for accurate page numbering)
            
        Returns:
            dict: Indexing statistics
        """
        if not self.ensure_weaviate_client():
            logger.warning("Weaviate not enabled, skipping document text indexing")
            return {"chunks_indexed": 0}
        
        try:
            chunks = self._chunk_text(markdown)
            logger.info(f"Created {len(chunks)} chunks from document {document_id}")
            
            collection = self.weaviate_client.collections.get("DocumentChunk")
            
            # Calculate page numbers more accurately
            # If total_pages is provided, distribute chunks evenly across pages
            # Otherwise, estimate 2 chunks per page and cap at a reasonable maximum
            if total_pages and total_pages > 0:
                # Distribute chunks evenly across actual pages
                chunks_per_page = max(1, len(chunks) / total_pages)
            else:
                # Fallback: estimate 2 chunks per page
                chunks_per_page = 2.0
                total_pages = max(1, (len(chunks) + 1) // 2)  # Estimate total pages
            
            indexed_count = 0
            with collection.batch.fixed_size(batch_size=50) as batch:
                for idx, chunk in enumerate(chunks):
                    # Find entities mentioned in this chunk
                    entity_refs = []
                    if entities:
                        for entity in entities:
                            if entity.name and entity.name.lower() in chunk.lower():
                                entity_refs.append(entity.id)
                    
                    chunk_id = f"{document_id}_chunk_{idx}"
                    
                    # Calculate page number: distribute chunks across pages
                    # Page numbers are 1-indexed, so add 1
                    estimated_page = int(idx / chunks_per_page) + 1
                    # Cap at total_pages to prevent invalid page numbers
                    page_number = min(estimated_page, total_pages) if total_pages else estimated_page
                    
                    data_object = {
                        "chunkId": chunk_id,
                        "documentId": document_id,
                        "content": chunk,
                        "chunkIndex": idx,
                        "pageNumber": page_number,
                        "filename": filename,
                        "entityRefs": json.dumps(entity_refs)
                    }
                    
                    batch.add_object(data_object)
                    indexed_count += 1
            
            logger.info(f"Indexed {indexed_count} document chunks to Weaviate")
            return {"chunks_indexed": indexed_count}
            
        except Exception as e:
            logger.error(f"Error indexing document text: {e}")
            return {"chunks_indexed": 0, "error": str(e)}
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """
        Split text into overlapping chunks by words
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in words
            overlap: Number of overlapping words between chunks
            
        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            # Take chunk_size words
            chunk_words = words[i:i + chunk_size]
            chunk = ' '.join(chunk_words)
            chunks.append(chunk)
            
            # Move forward by (chunk_size - overlap)
            i += (chunk_size - overlap)
            
            # Stop if we're at the end
            if i >= len(words):
                break
        
        return chunks
    
    async def search_document_chunks(self, query: str, limit: int = 5) -> List[dict]:
        """
        Semantic search over document chunks
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching chunks with metadata
        """
        if not self.ensure_weaviate_client():
            return []
        
        try:
            collection = self.weaviate_client.collections.get("DocumentChunk")
            
            response = collection.query.near_text(
                query=query,
                limit=limit,
                return_properties=["chunkId", "documentId", "content", "chunkIndex", "pageNumber", "filename", "entityRefs"]
            )
            
            results = []
            for obj in response.objects:
                results.append({
                    "chunk_id": obj.properties.get("chunkId"),
                    "document_id": obj.properties.get("documentId"),
                    "content": obj.properties.get("content"),
                    "chunk_index": obj.properties.get("chunkIndex"),
                    "page_number": obj.properties.get("pageNumber"),
                    "filename": obj.properties.get("filename"),
                    "entity_refs": json.loads(obj.properties.get("entityRefs", "[]")),
                    "score": obj.metadata.certainty if hasattr(obj.metadata, 'certainty') else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching document chunks: {e}")
            return []
    
    async def index_edges(self, edges: List[Edge]) -> dict:
        """
        Index edges in Neo4j using dynamic relationship types
        
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
                # Use actual relationship type from EdgeType enum
                rel_type = edge.type.value if hasattr(edge.type, 'value') else str(edge.type)
                
                # Build dynamic Cypher with proper relationship type
                # Neo4j requires relationship types to be identifiers, not parameters
                cypher = f"""
                    MATCH (a {{entityId: $source}})
                    MATCH (b {{entityId: $target}})
                    CREATE (a)-[r:{rel_type} {{
                        edgeId: $edgeId,
                        graphId: $graphId,
                        properties: $properties
                    }}]->(b)
                """
                
                # Convert properties dict to JSON string for Neo4j
                props_json = json.dumps(edge.properties) if edge.properties else "{}"
                
                session.run(
                    cypher,
                    source=edge.source,
                    target=edge.target,
                    edgeId=edge.id,
                    graphId=edge.graph_id,
                    properties=props_json
                )
                
                logger.debug(f"Indexed {rel_type} relationship: {edge.source} -> {edge.target}")
        
        logger.info(f"Indexed {len(edges)} relationships to Neo4j with proper types")
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
        if not entities:
            logger.warning("No entities to index to Neo4j")
            return 0
            
        try:
            import json

            with self.neo4j_driver.session() as session:
                # Use MERGE to avoid duplicates, and commit transaction
                indexed = 0
                for entity in entities:
                    result = session.run(
                        """
                        MERGE (n:Entity {entityId: $entityId})
                        ON CREATE SET 
                            n.type = $type,
                            n.name = $name,
                            n.properties = $properties,
                            n.documentId = $documentId,
                            n.graphId = $graphId,
                            n.citations = $citations
                        ON MATCH SET
                            n.type = $type,
                            n.name = $name,
                            n.properties = $properties,
                            n.documentId = $documentId,
                            n.graphId = $graphId,
                            n.citations = $citations
                        RETURN n
                        """,
                        entityId=entity.id,
                        type=entity.type.value,
                        name=entity.name,
                        properties=json.dumps(entity.properties or {}),
                        documentId=entity.document_id,
                        graphId=entity.graph_id,
                        citations=json.dumps([c.model_dump() for c in entity.citations] if entity.citations else [])
                    )
                    # Consume result to ensure query executes
                    result.consume()
                    indexed += 1
                
                # Commit the transaction
                session.close()
            
            logger.info(f"Indexed {indexed} entities to Neo4j")
            return indexed
        except Exception as e:
            logger.error(f"Error indexing to Neo4j: {e}", exc_info=True)
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

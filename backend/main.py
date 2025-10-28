"""
ArthaNethra FastAPI Application
Main entry point for the backend API
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn

from config import settings
from services import (
    IngestionService,
    ExtractionService,
    NormalizationService,
    IndexingService,
    RiskDetectionService,
    ChatbotService
)
from models import Document, Entity, Edge, Risk
from loguru import logger

# Configure logging
logger.add(
    settings.LOG_FILE,
    rotation="500 MB",
    level=settings.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("🚀 Starting ArthaNethra API")
    yield
    logger.info("👋 Shutting down ArthaNethra API")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered financial investigation platform",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ingestion_service = IngestionService()
extraction_service = ExtractionService()
normalization_service = NormalizationService()
indexing_service = IndexingService()
risk_detection_service = RiskDetectionService()
chatbot_service = ChatbotService()

# In-memory storage (TODO: replace with database)
documents_store = {}
graphs_store = {}


# ============================================================================
# API Routes
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy"
    }


@app.post(f"{settings.API_PREFIX}/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Upload and ingest a financial document
    
    Args:
        file: PDF, ZIP, or Excel file
        
    Returns:
        Document metadata
    """
    try:
        logger.info(f"Ingesting document: {file.filename}")
        
        # Ingest document
        document = await ingestion_service.ingest_document(
            file.file,
            file.filename,
            file.content_type
        )
        
        # Store in memory (TODO: database)
        documents_store[document.id] = document
        
        return document.model_dump()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ingestion error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post(f"{settings.API_PREFIX}/extract")
async def extract_document(document_id: str):
    """
    Extract structured data from document using LandingAI ADE
    
    Args:
        document_id: Document ID to extract
        
    Returns:
        Extraction results with entities and citations
    """
    try:
        # Get document
        document = documents_store.get(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"Extracting document: {document_id}")
        
        # Extract with ADE
        ade_output = await extraction_service.extract_document(document)
        
        # Update document
        document.ade_output = ade_output
        document.status = "extracted"
        document.extraction_id = ade_output["metadata"]["extraction_id"]
        document.total_pages = ade_output["metadata"]["total_pages"]
        document.confidence_score = ade_output["metadata"]["confidence_score"]
        
        documents_store[document_id] = document
        
        return {
            "extraction_id": document.extraction_id,
            "document_id": document_id,
            "status": "completed",
            "entities_count": len(ade_output.get("entities", [])),
            "ade_output": ade_output
        }
        
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/normalize")
async def normalize_to_graph(document_id: str):
    """
    Convert ADE output to knowledge graph entities and edges
    
    Args:
        document_id: Document ID with ADE extraction
        
    Returns:
        Graph entities and edges
    """
    try:
        # Get document
        document = documents_store.get(document_id)
        if not document or not document.ade_output:
            raise HTTPException(
                status_code=404,
                detail="Document not found or not extracted"
            )
        
        logger.info(f"Normalizing document: {document_id}")
        
        # Normalize to graph
        entities, edges = await normalization_service.normalize_to_graph(
            document.ade_output,
            document_id
        )
        
        # Store graph
        graph_id = entities[0].graph_id if entities else None
        if graph_id:
            graphs_store[graph_id] = {
                "id": graph_id,
                "document_id": document_id,
                "entities": entities,
                "edges": edges
            }
            document.graph_id = graph_id
            document.entities_count = len(entities)
            document.edges_count = len(edges)
            document.status = "normalized"
        
        return {
            "graph_id": graph_id,
            "entities": [e.model_dump() for e in entities],
            "edges": [e.model_dump() for e in edges]
        }
        
    except Exception as e:
        logger.error(f"Normalization error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/index")
async def index_graph(graph_id: str):
    """
    Index entities and edges in Weaviate and Neo4j
    
    Args:
        graph_id: Graph ID to index
        
    Returns:
        Indexing statistics
    """
    try:
        # Get graph
        graph = graphs_store.get(graph_id)
        if not graph:
            raise HTTPException(status_code=404, detail="Graph not found")
        
        logger.info(f"Indexing graph: {graph_id}")
        
        # Index entities
        entity_stats = await indexing_service.index_entities(graph["entities"])
        
        # Index edges
        edge_stats = await indexing_service.index_edges(graph["edges"])
        
        # Update document status
        document_id = graph["document_id"]
        if document_id in documents_store:
            documents_store[document_id].status = "indexed"
        
        return {
            "indexed_at": "now",
            **entity_stats,
            **edge_stats
        }
        
    except Exception as e:
        logger.error(f"Indexing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/risk")
async def detect_risks(graph_id: str):
    """
    Detect financial risks in the knowledge graph
    
    Args:
        graph_id: Graph ID to analyze
        
    Returns:
        Risk report with detected risks
    """
    try:
        # Get graph
        graph = graphs_store.get(graph_id)
        if not graph:
            raise HTTPException(status_code=404, detail="Graph not found")
        
        logger.info(f"Detecting risks for graph: {graph_id}")
        
        # Detect risks
        risks = await risk_detection_service.detect_risks(
            graph["entities"],
            graph["document_id"],
            graph_id
        )
        
        # Also check for missing covenants
        covenant_risks = await risk_detection_service.detect_missing_covenants(
            graph["entities"],
            graph["document_id"],
            graph_id
        )
        risks.extend(covenant_risks)
        
        # Calculate summary
        summary = risk_detection_service.calculate_risk_summary(risks)
        
        return {
            "risk_report": {
                **summary,
                "risks": [r.model_dump() for r in risks]
            },
            "generated_at": "now"
        }
        
    except Exception as e:
        logger.error(f"Risk detection error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(f"{settings.API_PREFIX}/ask")
async def chat_with_bot(
    message: str,
    graph_id: Optional[str] = None,
    document_id: Optional[str] = None
):
    """
    Ask the AI chatbot a question
    
    Args:
        message: User question
        graph_id: Optional graph context
        document_id: Optional document context
        
    Returns:
        Streaming AI response
    """
    try:
        logger.info(f"Chat request: {message[:100]}")
        
        context = {
            "graph_id": graph_id,
            "document_id": document_id
        }
        
        async def generate():
            async for chunk in chatbot_service.chat(message, context):
                yield chunk
        
        return StreamingResponse(
            generate(),
            media_type="text/plain"
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_PREFIX}/evidence/{{document_id}}")
async def get_evidence(
    document_id: str,
    page: Optional[int] = Query(None, description="Page number")
):
    """
    Serve PDF document with optional page highlight
    
    Args:
        document_id: Document ID
        page: Optional page number to highlight
        
    Returns:
        PDF file
    """
    try:
        document = documents_store.get(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return FileResponse(
            document.file_path,
            media_type="application/pdf",
            filename=document.filename
        )
        
    except Exception as e:
        logger.error(f"Evidence error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_PREFIX}/graph/{{graph_id}}")
async def get_graph(graph_id: str):
    """
    Retrieve knowledge graph by ID
    
    Args:
        graph_id: Graph ID
        
    Returns:
        Graph with entities and edges
    """
    graph = graphs_store.get(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    return {
        "graph_id": graph["id"],
        "document_id": graph["document_id"],
        "entities": [e.model_dump() for e in graph["entities"]],
        "edges": [e.model_dump() for e in graph["edges"]]
    }


@app.post(f"{settings.API_PREFIX}/graph/query")
async def query_graph(
    query_text: str,
    limit: int = 10
):
    """
    Semantic search in the knowledge graph
    
    Args:
        query_text: Search query
        limit: Max results
        
    Returns:
        Matching entities
    """
    try:
        results = await indexing_service.query_entities(query_text, limit)
        return {"results": results, "total_results": len(results)}
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Run application
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )


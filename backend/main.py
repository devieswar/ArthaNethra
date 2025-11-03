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
from services import schemas as schema_presets
from models import Document, Entity, Edge, Risk
from loguru import logger
import uuid
import json
from pathlib import Path

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
jobs_store = {}


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


@app.get(f"{settings.API_PREFIX}/documents")
async def list_documents():
    """List all uploaded/processed documents (prunes missing files)."""
    import os
    to_delete = []
    results = []
    for doc_id, doc in documents_store.items():
        if not os.path.exists(doc.file_path):
            to_delete.append(doc_id)
            continue
        results.append(doc.model_dump())
    for doc_id in to_delete:
        documents_store.pop(doc_id, None)
        logger.info(f"Pruned missing document from store: {doc_id}")
    return results


@app.get(f"{settings.API_PREFIX}/documents/{{document_id}}")
async def get_document(document_id: str):
    """Get a single document by ID."""
    document = documents_store.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document.model_dump()


@app.delete(f"{settings.API_PREFIX}/documents/{{document_id}}")
async def delete_document(document_id: str):
    """Delete a document and its file (best-effort)."""
    document = documents_store.pop(document_id, None)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        import os
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except Exception as e:
        logger.warning(f"Could not remove file for {document_id}: {e}")
    return {"status": "deleted", "document_id": document_id}


@app.post(f"{settings.API_PREFIX}/extract")
async def extract_document(document_id: str, schema_name: str | None = None, custom_schema: str | None = None):
    """
    Extract structured data from document using LandingAI ADE
    
    Args:
        document_id: Document ID to extract
        
    Returns:
        Extraction results with entities and citations
    """
    try:
        # Get document (fallback to disk if missing from memory)
        document = documents_store.get(document_id)
        if not document:
            document = await ingestion_service.get_document(document_id)
            if document:
                documents_store[document_id] = document
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"Extracting document: {document_id}")

        # Create job
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        jobs_store[job_id] = {
            "job_id": job_id,
            "document_id": document_id,
            "status": "processing",
            "started_at": "now",
            "total": None,
            "completed": 0,
            "failed": 0
        }
        
        # Resolve schema
        selected_schema = None
        if schema_name:
            selected_schema = schema_presets.presets.get(schema_name)
        if custom_schema:
            try:
                selected_schema = json.loads(custom_schema)
            except Exception as e:
                logger.warning(f"Invalid custom_schema: {e}")
        
        # Extract with ADE
        # Large/ZIP routing handled inside service; pass schema for Extract
        ade_output = await extraction_service.extract_document(document) if selected_schema is None else (
            await extraction_service._extract_via_parse_then_extract(document.file_path, document.filename, document.mime_type, selected_schema)
        )
        
        # Update document
        document.ade_output = ade_output
        document.status = "extracted"
        document.extraction_id = ade_output["metadata"]["extraction_id"]
        document.total_pages = ade_output["metadata"]["total_pages"]
        document.confidence_score = ade_output["metadata"]["confidence_score"]
        
        documents_store[document_id] = document
        
        # Update job
        jobs_store[job_id].update({
            "status": "completed",
            "completed_at": "now",
            "total": extraction_service.get_progress(document_id).get("total") if extraction_service.get_progress(document_id) else None,
            "completed": extraction_service.get_progress(document_id).get("completed") if extraction_service.get_progress(document_id) else None,
            "entities_count": len(ade_output.get("entities", [])),
            "schema_name": schema_name or ("custom" if custom_schema else None)
        })
        # Persist result to cache
        try:
            jobs_dir = Path(settings.CACHE_DIR) / "jobs"
            jobs_dir.mkdir(parents=True, exist_ok=True)
            with open(jobs_dir / f"{job_id}.json", "w", encoding="utf-8") as f:
                json.dump({
                    "job": jobs_store[job_id],
                    "response": {
                        "extraction_id": document.extraction_id,
                        "document_id": document_id,
                        "status": "completed",
                        "entities_count": len(ade_output.get("entities", [])),
                        "ade_output": ade_output
                    }
                }, f)
            jobs_store[job_id]["result_path"] = str(jobs_dir / f"{job_id}.json")
        except Exception as e:
            logger.warning(f"Could not persist job {job_id}: {e}")
        
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


@app.get(f"{settings.API_PREFIX}/extract/status")
async def get_extract_status(document_id: str):
    """Return extraction progress for a document (if available)."""
    progress = extraction_service.get_progress(document_id)
    return progress or {"status": "unknown"}


@app.get(f"{settings.API_PREFIX}/extract/jobs")
async def list_extract_jobs():
    """List extraction jobs (in-memory)."""
    return list(jobs_store.values())


@app.get(f"{settings.API_PREFIX}/extract/jobs/{{job_id}}")
async def get_extract_job(job_id: str):
    job = jobs_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # If result persisted, try to read preview
    preview = None
    try:
        if job.get("result_path"):
            with open(job["result_path"], "r", encoding="utf-8") as f:
                data = json.load(f)
                preview = {
                    "entities_count": data.get("response", {}).get("entities_count"),
                    "total_pages": data.get("response", {}).get("ade_output", {}).get("metadata", {}).get("total_pages")
                }
    except Exception:
        pass
    return {"job": job, "preview": preview}


@app.get(f"{settings.API_PREFIX}/extract/stream")
async def stream_extract_status(document_id: str):
    """Server-Sent Events stream for extraction progress."""
    async def event_generator():
        import asyncio
        last = None
        while True:
            progress = extraction_service.get_progress(document_id) or {"status": "unknown"}
            if progress != last:
                try:
                    payload = json.dumps(progress)
                except Exception:
                    payload = "{}"
                yield f"data: {payload}\n\n"
                last = progress
            # End when completed or failed
            status = str(progress.get("status", "")).lower()
            if status in {"completed", "failed"}:
                break
            await asyncio.sleep(0.5)
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get(f"{settings.API_PREFIX}/extract/jobs/{{job_id}}/result")
async def get_extract_job_result(job_id: str):
    job = jobs_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = None
    try:
        if job.get("result_path"):
            with open(job["result_path"], "r", encoding="utf-8") as f:
                result = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job result not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result or {"job": job}


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
        # Get document (fallback to disk if missing from memory)
        document = documents_store.get(document_id)
        if not document:
            document = await ingestion_service.get_document(document_id)
            if document:
                documents_store[document_id] = document
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
            document = await ingestion_service.get_document(document_id)
            if document:
                documents_store[document_id] = document
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


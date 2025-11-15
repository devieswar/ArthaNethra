"""
ArthaNethra FastAPI Application
Main entry point for the backend API
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
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
from models import Document, Entity, Edge, Risk, ChatSession, ChatMessage
from models.document import DocumentStatus
from loguru import logger
import uuid
import json
from pathlib import Path
from datetime import datetime

# Configure logging
logger.add(
    settings.LOG_FILE,
    rotation="500 MB",
    level=settings.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


# Initialize services (before app creation so they're available in lifespan)
ingestion_service = IngestionService()
extraction_service = ExtractionService()
normalization_service = NormalizationService()
indexing_service = IndexingService()
risk_detection_service = RiskDetectionService()
chatbot_service = ChatbotService()

# Import persistence service
from services.persistence import PersistenceService
persistence_service = PersistenceService()


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - handles startup and shutdown"""
    # Startup
    logger.info("Starting ArthaNethra API")
    
    # Load persisted state from disk
    global documents_store, graphs_store, entities_store, chat_sessions_store, chat_messages_store, jobs_store, risks_store
    
    # Initialize stores
    documents_store = {}
    graphs_store = {}
    entities_store = {}
    chat_sessions_store = {}
    chat_messages_store = {}
    jobs_store = {}
    risks_store = {}
    
    try:
        docs, graphs, entities, sessions, messages, risks = persistence_service.load_all()
        documents_store.update(docs)
        graphs_store.update(graphs)
        entities_store.update(entities)
        chat_sessions_store.update(sessions)
        chat_messages_store.update(messages)
        risks_store.update(risks)
        
        # Restore entities into graphs_store for consistency
        for graph_id, entity_list in entities.items():
            if graph_id in graphs_store:
                # Graph exists, just update entities
                graphs_store[graph_id]["entities"] = entity_list
            else:
                # Graph doesn't exist (lost during save), reconstruct it
                logger.warning(f"Reconstructing missing graph {graph_id} from entities")
                # Find document_id from entities or documents
                document_id = entity_list[0].document_id if entity_list else ""
                graphs_store[graph_id] = {
                    "id": graph_id,
                    "graph_id": graph_id,
                    "document_id": document_id,
                    "entities": entity_list,
                    "edges": [],  # Edges lost, will be empty
                    "metadata": {}
                }
        
        logger.info(f"Restored state: {len(docs)} documents, {len(graphs_store)} graphs, {sum(len(e) for e in entities.values())} entities, {len(sessions)} sessions, {len(risks)} risk graphs")
        
        # Skip auto-indexing on startup (entities already in Weaviate/Neo4j volumes)
        # Only index when new documents are uploaded
        logger.info(f"Skipping auto-index: {len(entities_store)} graphs already persisted in Weaviate/Neo4j")
        
    except Exception as e:
        logger.warning(f"Could not load persisted state: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ArthaNethra API")
    
    # Save state to disk before shutdown
    try:
        persistence_service.save_all(
            documents_store, 
            graphs_store, 
            entities_store,
            chat_sessions_store,
            chat_messages_store,
            risks_store
        )
        logger.info("State saved to disk")
    except Exception as e:
        logger.error(f"Failed to save state: {e}")
    
    # Cleanup services
    await extraction_service.close()


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

# In-memory storage (TODO: replace with database)
# Stores are initialized in lifespan context


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


@app.get(f"{settings.API_PREFIX}/health")
async def health_check():
    """Detailed health check for frontend"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "services": {
            "weaviate": indexing_service.weaviate_client is not None,
            "neo4j": indexing_service.neo4j_driver is not None,
            "bedrock": chatbot_service.bedrock is not None
        }
    }


@app.get(f"{settings.API_PREFIX}/documents")
async def get_all_documents():
    """
    Get all documents from the store
    
    Returns:
        List of all document metadata with entity/edge counts
    """
    try:
        documents = []
        for doc_id, doc in documents_store.items():
            doc_dict = doc.model_dump()
            # The document already has entities_count and edges_count from normalization
            # But ensure they're up to date with latest data
            if doc.graph_id and doc.graph_id in graphs_store:
                graph = graphs_store[doc.graph_id]
                doc_dict['entities_count'] = len(graph.get("entities", []))
                doc_dict['edges_count'] = len(graph.get("edges", []))
            elif not doc.graph_id:
                # Document not yet normalized
                doc_dict['entities_count'] = 0
                doc_dict['edges_count'] = 0
            
            documents.append(doc_dict)
        
        logger.info(f"Returning {len(documents)} documents")
        return documents
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    """Get a single document by ID with markdown content"""
    document = documents_store.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Serialize document
    doc_dict = document.model_dump()
    
    # Add markdown content from ADE output or metadata if available
    markdown_content = None
    if document.ade_output and isinstance(document.ade_output, dict):
        markdown_content = document.ade_output.get("markdown")
    if not markdown_content and isinstance(document.metadata, dict):
        markdown_content = document.metadata.get("markdown")
    doc_dict["markdown_content"] = markdown_content
    
    return doc_dict


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
async def extract_document(
    document_id: str,
    use_adaptive_schema: bool = True
):
    """
    Extract structured data from document using LandingAI ADE.
    
    Args:
        document_id: Document ID to extract
        use_adaptive_schema: Use deterministic schema analysis (default: True)
        
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
        
        # Extract with ADE (use adaptive schema for best results)
        if use_adaptive_schema:
            ade_output = await extraction_service.extract_document_with_adaptive_schema(document)
        else:
            ade_output = await extraction_service.extract_document(document)
        
        # Update document
        document.ade_output = ade_output
        document.status = DocumentStatus.EXTRACTED
        document.extraction_id = ade_output["metadata"]["extraction_id"]
        document.total_pages = ade_output["metadata"]["total_pages"]
        document.confidence_score = ade_output["metadata"]["confidence_score"]
        
        documents_store[document_id] = document
        
        # Update job
        progress = extraction_service.get_progress(document_id)
        jobs_store[job_id].update({
            "status": "completed",
            "completed_at": "now",
            "total": progress.get("total") if progress else None,
            "completed": progress.get("completed") if progress else None,
            "entities_count": len(ade_output.get("entities", [])),
            "schema_mode": "adaptive" if use_adaptive_schema else "default"
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
                response = data.get("response", {})
                ade_output = response.get("ade_output", {}) if isinstance(response, dict) else {}
                metadata = ade_output.get("metadata", {}) if isinstance(ade_output, dict) else {}
                preview = {
                    "entities_count": response.get("entities_count") if isinstance(response, dict) else None,
                    "total_pages": metadata.get("total_pages") if isinstance(metadata, dict) else None
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

        # Track any existing graphs tied to this document so we can clean them up after regeneration
        existing_graph_ids = [
            gid for gid, graph in graphs_store.items()
            if graph.get("document_id") == document_id
        ]

        # Normalize to graph
        # Include markdown from document metadata in ade_output for narrative extraction
        ade_output_with_markdown = dict(document.ade_output)
        if document.metadata and isinstance(document.metadata, dict):
            if markdown_text := document.metadata.get("markdown"):
                ade_output_with_markdown["markdown"] = markdown_text
        
        entities, edges = await normalization_service.normalize_to_graph(
            ade_output_with_markdown,
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
            # Also store entities in entities_store for persistence
            entities_store[graph_id] = entities
            document.graph_id = graph_id
            document.entities_count = len(entities)
            document.edges_count = len(edges)
            document.status = DocumentStatus.NORMALIZED
            documents_store[document_id] = document

            # Remove any stale graphs previously associated with this document
            stale_graph_ids = [gid for gid in existing_graph_ids if gid != graph_id]
            for stale_id in stale_graph_ids:
                removed_graph = graphs_store.pop(stale_id, None)
                removed_entities = entities_store.pop(stale_id, None)
                removed_risks = risks_store.pop(stale_id, None)
                entities_count = len(removed_entities or [])
                risk_count = len(removed_risks or [])
                logger.info(
                    f"🧹 Removed stale graph {stale_id} for document {document_id}"
                    f" (entities: {entities_count}, risks: {risk_count})"
                )
            
            # Run risk detection
            logger.info(f"Running risk detection for document: {document_id}")
            try:
                # Rule-based detection
                rule_risks = await risk_detection_service.detect_risks(entities, document_id, graph_id)
                
                # LLM-based anomaly detection
                llm_risks = await risk_detection_service.detect_llm_anomalies(entities, document_id, graph_id)
                
                # Combine all risks
                all_risks = rule_risks + llm_risks
                
                # Generate graph data for each risk
                if all_risks:
                    graph = graphs_store.get(graph_id, {})
                    relationships = graph.get("edges", [])
                    logger.info(f"Generating graph data for {len(all_risks)} risks...")
                    
                    for risk in all_risks:
                        try:
                            graph_data = await risk_detection_service.generate_risk_graph_data(
                                risk=risk,
                                entities=entities,
                                relationships=relationships
                            )
                            risk.graph_data = graph_data
                        except Exception as e:
                            logger.warning(f"Failed to generate graph data for risk {risk.id}: {e}")
                            risk.graph_data = {"entities": [], "relationships": [], "reasoning": "Error generating graph data"}
                
                # Store risks
                if all_risks:
                    risks_store[graph_id] = all_risks
                    logger.info(f"Detected {len(all_risks)} risks ({len(rule_risks)} rule-based, {len(llm_risks)} LLM-based)")
                    
                    # Save risks to disk immediately
                    try:
                        persistence_service.save_risks(risks_store)
                        logger.info(f"Saved {len(all_risks)} risks to disk")
                    except Exception as save_error:
                        logger.error(f"Failed to save risks: {save_error}")
                else:
                    logger.info("No risks detected")
            except Exception as risk_error:
                logger.error(f"Risk detection failed: {risk_error}")
                # Continue even if risk detection fails

            # Persist updated document + graph state (including cleanup)
            try:
                persistence_service.save_documents(documents_store)
                persistence_service.save_graphs(graphs_store)
                persistence_service.save_entities(entities_store)
                persistence_service.save_risks(risks_store)
                logger.debug("Persisted updated document and graph state after normalization")
            except Exception as persist_error:
                logger.error(f"Failed to persist updated normalization state: {persist_error}")
        
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
        entities = graph.get("entities", [])
        if not entities:
            raise HTTPException(status_code=400, detail="Graph has no entities to index")
        entity_stats = await indexing_service.index_entities(entities)
        
        # Index edges
        edges = graph.get("edges", [])
        edge_stats = await indexing_service.index_edges(edges)
        
        # Index full document text for semantic search
        document_id = graph.get("document_id", "")
        chunk_stats = {"chunks_indexed": 0}
        if document_id in documents_store:
            document = documents_store[document_id]
            markdown = document.metadata.get("markdown", "")
            if markdown:
                logger.info(f"Indexing document text chunks for: {document_id}")
                chunk_stats =                 await indexing_service.index_document_text(
                    document_id=document_id,
                    markdown=markdown,
                    filename=document.filename,
                    entities=entities,
                    total_pages=document.total_pages  # Pass actual page count for accurate page numbering
                )
            documents_store[document_id].status = DocumentStatus.INDEXED
        
        return {
            "indexed_at": "now",
            **entity_stats,
            **edge_stats,
            **chunk_stats
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
        entities = graph.get("entities", [])
        document_id = graph.get("document_id", "")
        
        risks = await risk_detection_service.detect_risks(
            entities,
            document_id,
            graph_id
        )
        
        # Also check for missing covenants
        covenant_risks = await risk_detection_service.detect_missing_covenants(
            entities,
            document_id,
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
    document_id: Optional[str] = None,
    stream: bool = True
):
    """
    Ask the AI chatbot a question with full graph context
    
    Args:
        message: User question
        graph_id: Optional graph context
        document_id: Optional document context
        stream: Whether to stream response (default: True)
        
    Returns:
        Streaming AI response (Server-Sent Events) with graph-augmented context
    """
    try:
        logger.info(f"Chat request: {message[:100]}")
        
        # Build rich context from knowledge graph
        context = {
            "graph_id": graph_id,
            "document_id": document_id,
            "entities": [],
            "documents": [],
            "risks": []
        }
        
        # Add all available entities to context
        all_entities = []
        for graph in graphs_store.values():
            all_entities.extend(graph.get("entities", []))
        
        if all_entities:
            # Convert entities to simple dict for LLM context
            context["entities"] = [
                {
                    "id": e.id,
                    "type": e.type.value if hasattr(e.type, 'value') else str(e.type),
                    "name": e.name,
                    "properties": e.properties
                }
                for e in all_entities[:50]  # Limit to 50 for token efficiency
            ]
        
        # Add document metadata
        context["documents"] = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.status.value if hasattr(doc.status, 'value') else str(doc.status)
            }
            for doc in documents_store.values()
        ]
        
        # Add risk information (if we had risks_store)
        context["total_entities"] = len(all_entities)
        context["total_documents"] = len(documents_store)
        context["total_graphs"] = len(graphs_store)
        
        if stream:
            # Stream response using Server-Sent Events
            async def generate():
                try:
                    async for chunk in chatbot_service.chat(message, context):
                        # SSE format: data: {content}\n\n
                        yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                    # Send completion signal
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                except Exception as e:
                    logger.error(f"Stream error: {str(e)}")
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    yield f"data: {json.dumps({'content': error_msg, 'error': True, 'done': True})}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Non-streaming fallback
            response_text = ""
            async for chunk in chatbot_service.chat(message, context):
                response_text += chunk
        
            return {
                "response": response_text,
                "message": message,
                "timestamp": "now"
            }
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        # Return error as SSE if streaming, else JSON
        if stream:
            async def error_stream():
                error_msg = "I'm having trouble processing that request. Try asking about specific companies, loans, or financial metrics."
                yield f"data: {json.dumps({'content': error_msg, 'error': True, 'done': True})}\n\n"
            return StreamingResponse(error_stream(), media_type="text/event-stream")
        else:
            return {
                "response": "I'm having trouble processing that request.",
                "message": message,
                "error": str(e),
                "timestamp": "now"
            }


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
        "graph_id": graph.get("id", graph_id),
        "document_id": graph.get("document_id", ""),
        "entities": [e.model_dump() for e in graph.get("entities", [])],
        "edges": [e.model_dump() for e in graph.get("edges", [])]
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


@app.get(f"{settings.API_PREFIX}/entities")
async def list_entities():
    """
    List all entities from all graphs
    
    Returns:
        List of all entities
    """
    all_entities = []
    for graph in graphs_store.values():
        entities = graph.get("entities", [])
        all_entities.extend([e.model_dump() for e in entities])
    return all_entities


@app.get(f"{settings.API_PREFIX}/entities/graph/{{graph_id}}")
async def get_entities_by_graph(graph_id: str):
    """
    Get all entities for a specific graph
    
    Args:
        graph_id: Knowledge graph identifier
        
    Returns:
        List of entities in the graph
    """
    try:
        if graph_id not in graphs_store:
            raise HTTPException(status_code=404, detail="Graph not found")
        
        graph = graphs_store[graph_id]
        entities = graph.get("entities", [])
        
        # Convert to dict format
        entities_list = []
        for entity in entities:
            entity_dict = {
                "id": entity.id,
                "type": entity.type.value if hasattr(entity.type, 'value') else str(entity.type),
                "display_type": entity.display_type,
                "original_type": entity.original_type,
                "name": entity.name,
                "properties": entity.properties,
                "document_id": entity.document_id,
                "graph_id": entity.graph_id
            }
            entities_list.append(entity_dict)
        
        logger.info(f"Returning {len(entities_list)} entities for graph {graph_id}")
        return entities_list
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching entities for graph {graph_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_PREFIX}/entities/{{entity_id}}")
async def get_entity(entity_id: str):
    """
    Get a single entity by ID
    
    Args:
        entity_id: Entity ID
        
    Returns:
        Entity details
    """
    for graph in graphs_store.values():
        entities = graph.get("entities", [])
        for entity in entities:
            if entity.id == entity_id:
                return entity.model_dump()
    raise HTTPException(status_code=404, detail="Entity not found")


@app.get(f"{settings.API_PREFIX}/entities/search")
async def search_entities(q: str = Query(..., description="Search query")):
    """
    Search entities by name or properties
    
    Args:
        q: Search query string
        
    Returns:
        Matching entities
    """
    query_lower = q.lower()
    matching_entities = []
    
    for graph in graphs_store.values():
        entities = graph.get("entities", [])
        for entity in entities:
            # Search in name and properties
            if query_lower in entity.name.lower():
                matching_entities.append(entity.model_dump())
            elif any(query_lower in str(v).lower() for v in entity.properties.values()):
                matching_entities.append(entity.model_dump())
    
    return matching_entities


@app.get(f"{settings.API_PREFIX}/risks/{{risk_id}}")
async def get_risk(risk_id: str):
    """
    Get a single risk by ID
    
    Args:
        risk_id: Risk ID
        
    Returns:
        Risk details
    """
    # TODO: Implement risk storage and retrieval
    raise HTTPException(status_code=404, detail="Risk not found")


@app.get(f"{settings.API_PREFIX}/risks/entity/{{entity_id}}")
async def get_risks_by_entity(entity_id: str):
    """
    Get all risks associated with an entity
    
    Args:
        entity_id: Entity ID
        
    Returns:
        List of risks for this entity
    """
    # TODO: Implement risk-entity association
    return []


@app.get(f"{settings.API_PREFIX}/relationships")
async def get_relationships(
    limit: int = Query(100, ge=1, le=1000)
) -> List[Dict[str, Any]]:
    """Get all relationships/edges from the knowledge graph"""
    try:
        # Collect all edges from all graphs
        relationships = []
        for graph in graphs_store.values():
            for edge in graph.get("edges", []):
                # Edge model uses: source, target, type (EdgeType enum)
                # Convert to frontend-friendly format
                edge_dict = edge.model_dump() if hasattr(edge, 'model_dump') else edge
                
                rel_data = {
                    "id": edge_dict.get("id", ""),
                    "from_entity_id": edge_dict.get("source", ""),  # Edge.source -> from_entity_id
                    "to_entity_id": edge_dict.get("target", ""),    # Edge.target -> to_entity_id
                    "relationship_type": edge_dict.get("type", "") if isinstance(edge_dict.get("type"), str) else str(edge_dict.get("type", "")),  # EdgeType enum -> string
                    "properties": edge_dict.get("properties", {})
                }
                relationships.append(rel_data)
                if len(relationships) >= limit:
                    break
            if len(relationships) >= limit:
                break
        
        return relationships[:limit]
    except Exception as e:
        logger.error(f"Error fetching relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_PREFIX}/relationships/graph/{{graph_id}}")
async def get_relationships_by_graph(graph_id: str) -> List[Dict[str, Any]]:
    """Get all relationships/edges for a specific knowledge graph"""
    try:
        if graph_id not in graphs_store:
            raise HTTPException(status_code=404, detail="Graph not found")
        
        graph = graphs_store[graph_id]
        relationships = []
        
        for edge in graph.get("edges", []):
            # Edge model uses: source, target, type (EdgeType enum)
            # Convert to frontend-friendly format
            edge_dict = edge.model_dump() if hasattr(edge, 'model_dump') else edge
            
            rel_data = {
                "id": edge_dict.get("id", ""),
                "from_entity_id": edge_dict.get("source", ""),  # Edge.source -> from_entity_id
                "to_entity_id": edge_dict.get("target", ""),    # Edge.target -> to_entity_id
                "relationship_type": edge_dict.get("type", "") if isinstance(edge_dict.get("type"), str) else str(edge_dict.get("type", "")),  # EdgeType enum -> string
                "properties": edge_dict.get("properties", {})
            }
            relationships.append(rel_data)
        
        logger.info(f"Returning {len(relationships)} relationships for graph {graph_id}")
        return relationships
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching relationships for graph {graph_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{settings.API_PREFIX}/analytics/dashboard")
async def get_dashboard_analytics():
    """
    Get dashboard analytics and statistics
    
    Returns:
        Dashboard statistics
    """
    total_documents = len(documents_store)
    total_graphs = len(graphs_store)
    
    # Count entities and edges
    total_entities = 0
    total_edges = 0
    entity_types = {}
    
    for graph in graphs_store.values():
        entities = graph.get("entities", [])
        edges = graph.get("edges", [])
        total_entities += len(entities)
        total_edges += len(edges)
        
        for entity in entities:
            entity_type = entity.type.value
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    # Count documents by status
    status_counts = {}
    for doc in documents_store.values():
        status = doc.status.value
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return {
        "total_documents": total_documents,
        "total_graphs": total_graphs,
        "total_entities": total_entities,
        "total_edges": total_edges,
        "entity_types": entity_types,
        "document_status": status_counts,
        "total_risks": 0  # TODO: Track risks
    }


@app.get(f"{settings.API_PREFIX}/analytics/risk-trends")
async def get_risk_trends():
    """
    Get risk trends over time
    
    Returns:
        Risk trend data
    """
    # TODO: Implement risk tracking over time
    return {
        "trends": [],
        "severity_distribution": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
    }


# ============================================================================
# CHAT SESSION ENDPOINTS
# ============================================================================

@app.get(f"{settings.API_PREFIX}/chat/sessions")
async def get_chat_sessions() -> List[Dict[str, Any]]:
    """Get all chat sessions"""
    return list(chat_sessions_store.values())


@app.post(f"{settings.API_PREFIX}/chat/sessions")
async def create_chat_session(name: str = "New Chat") -> Dict[str, Any]:
    """Create a new chat session"""
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    session = {
        "id": session_id,
        "name": name,
        "document_ids": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "message_count": 0
    }
    chat_sessions_store[session_id] = session
    chat_messages_store[session_id] = []
    logger.info(f"Created chat session: {session_id}")
    return session


@app.get(f"{settings.API_PREFIX}/chat/sessions/{{session_id}}")
async def get_chat_session(session_id: str) -> Dict[str, Any]:
    """Get a specific chat session"""
    if session_id not in chat_sessions_store:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat_sessions_store[session_id]


class UpdateSessionRequest(BaseModel):
    name: Optional[str] = None
    document_ids: Optional[List[str]] = None


@app.put(f"{settings.API_PREFIX}/chat/sessions/{{session_id}}")
async def update_chat_session(
    session_id: str,
    update_data: UpdateSessionRequest
) -> Dict[str, Any]:
    """Update a chat session (name and/or document_ids)"""
    if session_id not in chat_sessions_store:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    session = chat_sessions_store[session_id]
    if update_data.name is not None:
        session["name"] = update_data.name
    if update_data.document_ids is not None:
        session["document_ids"] = update_data.document_ids
    session["updated_at"] = datetime.utcnow().isoformat()
    
    return session


@app.delete(f"{settings.API_PREFIX}/chat/sessions/{{session_id}}")
async def delete_chat_session(session_id: str):
    """Delete a chat session"""
    if session_id not in chat_sessions_store:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    del chat_sessions_store[session_id]
    if session_id in chat_messages_store:
        del chat_messages_store[session_id]
    
    logger.info(f"Deleted chat session: {session_id}")
    return {"message": "Chat session deleted"}


@app.get(f"{settings.API_PREFIX}/chat/sessions/{{session_id}}/messages")
async def get_chat_messages(session_id: str) -> List[Dict[str, Any]]:
    """Get all messages in a chat session"""
    if session_id not in chat_sessions_store:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat_messages_store.get(session_id, [])


@app.post(f"{settings.API_PREFIX}/chat/sessions/{{session_id}}/messages")
async def send_message(
    session_id: str,
    request: Dict[str, Any]
) -> Dict[str, Any]:
    """Send a message in a chat session"""
    if session_id not in chat_sessions_store:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    message = request.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    session = chat_sessions_store[session_id]
    
    # Ensure messages list exists (might not if session restored from old state)
    if session_id not in chat_messages_store:
        chat_messages_store[session_id] = []
    
    # Add user message
    user_msg = {
        "id": f"msg_{uuid.uuid4().hex[:12]}",
        "session_id": session_id,
        "role": "user",
        "content": message,
        "created_at": datetime.utcnow().isoformat()
    }
    chat_messages_store[session_id].append(user_msg)
    
    # Get response from chatbot (only for documents in this session)
    document_ids = session.get("document_ids", [])
    
    # Get graph_ids for all documents in session
    graph_ids = []
    for doc_id in document_ids:
        if doc_id in documents_store:
            doc = documents_store[doc_id]
            # Find graph_id for this document
            for gid, graph in graphs_store.items():
                if graph.get("document_id") == doc_id:
                    graph_ids.append(gid)
                    break
    
    logger.info(f"Chat session {session_id}: {len(document_ids)} documents, {len(graph_ids)} graphs")
    
    try:
        # Use first graph_id if available
        graph_id = graph_ids[0] if graph_ids else None
        document_id = document_ids[0] if document_ids else None
        
        if not graph_id:
            logger.warning(f"No graph_id found for session {session_id}")
            assistant_response = "Please upload or add a document to this chat session first."
        else:
            logger.info(f"Sending to chatbot: graph_id={graph_id}, document_id={document_id}")
            
            # Build rich context from knowledge graph
            context = {
                "graph_id": graph_id,
                "document_id": document_id,
                "document_ids": document_ids,  # CRITICAL: Pass document_ids for filtering
                "entities": [],
                "documents": []
            }
            
            # Add entities from all graphs in session
            for gid in graph_ids:
                if gid in graphs_store:
                    graph = graphs_store[gid]
                    entities = graph.get("entities", [])
                    # Convert entities to simple dict for LLM context
                    context["entities"].extend([
                        {
                            "id": e.id,
                            "type": e.type.value if hasattr(e.type, 'value') else str(e.type),
                            "name": e.name,
                            "properties": e.properties
                        }
                        for e in entities[:50]  # Limit for token efficiency
                    ])
            
            # Add document metadata
            context["documents"] = [
                {"id": doc_id, "filename": documents_store[doc_id].filename}
                for doc_id in document_ids if doc_id in documents_store
            ]
            
            context["total_entities"] = len(context["entities"])
            context["total_documents"] = len(document_ids)
            context["total_graphs"] = len(graph_ids)
            
            # Collect streaming response into single string
            assistant_response = ""
            async for chunk in chatbot_service.chat(message, context):
                assistant_response += chunk
            
            if not assistant_response:
                assistant_response = "I couldn't generate a response."
        
        # Parse graph data from response if present
        graph_data = None
        display_content = assistant_response
        
        if "---GRAPH_DATA---" in assistant_response and "---END_GRAPH_DATA---" in assistant_response:
            try:
                # Extract graph JSON
                start_marker = "---GRAPH_DATA---"
                end_marker = "---END_GRAPH_DATA---"
                start_idx = assistant_response.index(start_marker) + len(start_marker)
                end_idx = assistant_response.index(end_marker)
                graph_json_str = assistant_response[start_idx:end_idx].strip()
                
                # Parse JSON
                import json
                graph_data = json.loads(graph_json_str)
                
                # Remove graph data from display content
                display_content = assistant_response[:assistant_response.index(start_marker)].strip()
                
                logger.info(f"Extracted graph data: {len(graph_data.get('entities', []))} entities, {len(graph_data.get('relationships', []))} relationships")
            except Exception as e:
                logger.warning(f"Failed to parse graph data: {e}")
                # Continue without graph data
                pass
        
        assistant_msg = {
            "id": f"msg_{uuid.uuid4().hex[:12]}",
            "session_id": session_id,
            "role": "assistant",
            "content": display_content,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Add graph data if available
        if graph_data:
            assistant_msg["graphData"] = graph_data
        
        chat_messages_store[session_id].append(assistant_msg)
        
        # Update session
        session["message_count"] += 2
        session["updated_at"] = datetime.utcnow().isoformat()
        
        return assistant_msg
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        error_msg = {
            "id": f"msg_{uuid.uuid4().hex[:12]}",
            "session_id": session_id,
            "role": "assistant",
            "content": f"Error: {str(e)}",
            "created_at": datetime.utcnow().isoformat()
        }
        chat_messages_store[session_id].append(error_msg)
        return error_msg


@app.post(f"{settings.API_PREFIX}/chat/sessions/{{session_id}}/documents/{{document_id}}")
async def add_document_to_session(session_id: str, document_id: str):
    """Add a document to a chat session"""
    if session_id not in chat_sessions_store:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if document_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    session = chat_sessions_store[session_id]
    if document_id not in session["document_ids"]:
        session["document_ids"].append(document_id)
        session["updated_at"] = datetime.utcnow().isoformat()
    
    return session


@app.delete(f"{settings.API_PREFIX}/chat/sessions/{{session_id}}/documents/{{document_id}}")
async def remove_document_from_session(session_id: str, document_id: str):
    """Remove a document from a chat session"""
    if session_id not in chat_sessions_store:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    session = chat_sessions_store[session_id]
    if document_id in session["document_ids"]:
        session["document_ids"].remove(document_id)
        session["updated_at"] = datetime.utcnow().isoformat()
    
    return session


# ============================================================================
# Risk Detection Endpoints
# ============================================================================

@app.get(f"{settings.API_PREFIX}/risks")
async def get_all_risks() -> List[Dict[str, Any]]:
    """Get all detected risks across all documents"""
    all_risks = []
    for graph_id, risks in risks_store.items():
        for risk in risks:
            all_risks.append(risk.model_dump())
    
    logger.info(f"Returning {len(all_risks)} risks")
    return all_risks


@app.get(f"{settings.API_PREFIX}/risks/graph/{{graph_id}}")
async def get_risks_by_graph(graph_id: str) -> List[Dict[str, Any]]:
    """Get risks for a specific knowledge graph"""
    risks = risks_store.get(graph_id, [])
    return [r.model_dump() for r in risks]


@app.get(f"{settings.API_PREFIX}/risks/document/{{document_id}}")
async def get_risks_by_document(document_id: str) -> Dict[str, Any]:
    """Get risks for a specific document with summary"""
    # Get document to find its current graph_id
    document = documents_store.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Use the graph_id from the document (most recent/current)
    graph_id = document.graph_id
    
    if not graph_id:
        return {
            "document_id": document_id,
            "risks": [],
            "summary": risk_detection_service.calculate_risk_summary([])
        }
    
    risks = risks_store.get(graph_id, [])
    summary = risk_detection_service.calculate_risk_summary(risks)
    
    logger.info(f"Fetched {len(risks)} risks for document {document_id} (graph: {graph_id})")
    
    return {
        "document_id": document_id,
        "graph_id": graph_id,
        "risks": [r.model_dump() for r in risks],
        "summary": summary
    }


@app.post(f"{settings.API_PREFIX}/risks/analyze/{{graph_id}}")
async def analyze_risks(graph_id: str, run_llm: bool = True) -> Dict[str, Any]:
    """
    Run risk analysis on an existing graph
    
    Args:
        graph_id: Knowledge graph ID
        run_llm: Whether to run LLM-based anomaly detection (default: True)
    """
    if graph_id not in graphs_store:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    graph = graphs_store[graph_id]
    entities = graph.get("entities", [])
    document_id = graph.get("document_id", "")
    
    if not entities:
        raise HTTPException(status_code=400, detail="No entities in graph")
    
    logger.info(f"Running risk analysis on graph: {graph_id}")
    
    # Rule-based detection
    rule_risks = await risk_detection_service.detect_risks(entities, document_id, graph_id)
    
    llm_risks = []
    if run_llm:
        # LLM-based anomaly detection
        llm_risks = await risk_detection_service.detect_llm_anomalies(entities, document_id, graph_id)
    
    # Combine and store
    all_risks = rule_risks + llm_risks
    
    # Generate graph data for each risk
    graph = graphs_store[graph_id]
    relationships = graph.get("edges", [])
    logger.info(f"Generating graph data for {len(all_risks)} risks...")
    
    for risk in all_risks:
        try:
            graph_data = await risk_detection_service.generate_risk_graph_data(
                risk=risk,
                entities=entities,
                relationships=relationships
            )
            risk.graph_data = graph_data
            logger.debug(f"Generated graph data for risk {risk.id}: {len(graph_data.get('entities', []))} entities, {len(graph_data.get('relationships', []))} relationships")
        except Exception as e:
            logger.warning(f"Failed to generate graph data for risk {risk.id}: {e}")
            risk.graph_data = {"entities": [], "relationships": [], "reasoning": "Error generating graph data"}
    
    risks_store[graph_id] = all_risks
    
    # Save risks to disk immediately
    try:
        persistence_service.save_risks(risks_store)
        logger.info(f"Saved {len(all_risks)} risks to disk")
    except Exception as save_error:
        logger.error(f"Failed to save risks: {save_error}")
    
    summary = risk_detection_service.calculate_risk_summary(all_risks)
    
    logger.info(f"Risk analysis complete: {len(all_risks)} risks detected")
    
    return {
        "graph_id": graph_id,
        "risks": [r.model_dump() for r in all_risks],
        "summary": summary,
        "rule_based_count": len(rule_risks),
        "llm_based_count": len(llm_risks)
    }


@app.post(f"{settings.API_PREFIX}/risks/update-graph-data")
async def update_all_risks_graph_data() -> Dict[str, Any]:
    """
    Update all existing risks with graph_data (for risks created before graph_data was added)
    """
    updated_count = 0
    error_count = 0
    
    for graph_id, risks in risks_store.items():
        graph = graphs_store.get(graph_id)
        if not graph:
            continue
        
        entities = entities_store.get(graph_id, [])
        relationships = graph.get("edges", [])
        
        if not entities:
            continue
        
        logger.info(f"Updating graph data for {len(risks)} risks in graph {graph_id}...")
        
        for risk in risks:
            # Skip if graph_data already exists
            if risk.graph_data and risk.graph_data.get("entities"):
                continue
            
            try:
                graph_data = await risk_detection_service.generate_risk_graph_data(
                    risk=risk,
                    entities=entities,
                    relationships=relationships
                )
                risk.graph_data = graph_data
                updated_count += 1
                logger.debug(f"Updated graph data for risk {risk.id}")
            except Exception as e:
                logger.warning(f"Failed to update graph data for risk {risk.id}: {e}")
                error_count += 1
                risk.graph_data = {"entities": [], "relationships": [], "reasoning": "Error generating graph data"}
    
    # Save updated risks to disk
    if updated_count > 0:
        try:
            persistence_service.save_risks(risks_store)
            logger.info(f"Saved {updated_count} updated risks to disk")
        except Exception as e:
            logger.error(f"Failed to save updated risks: {e}")
    
    return {
        "updated": updated_count,
        "errors": error_count,
        "message": f"Updated graph data for {updated_count} risks"
    }


@app.post(f"{settings.API_PREFIX}/risks/{{risk_id}}/graph")
async def generate_risk_graph(risk_id: str) -> Dict[str, Any]:
    """
    Use LLM to generate risk-specific graph elements (entities and relationships)
    """
    import boto3
    import json
    from config import settings
    
    # Find the risk
    risk = None
    graph_id = None
    for gid, risks in risks_store.items():
        for r in risks:
            if r.id == risk_id:
                risk = r
                graph_id = gid
                break
        if risk:
            break
    
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    
    # Get all entities and relationships for the graph
    graph = graphs_store.get(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    entities = entities_store.get(graph_id, [])
    relationships = []
    if graph.get("edges"):
        relationships = graph["edges"]
    
    # Prepare entity descriptions for LLM
    entity_descriptions = []
    for entity in entities[:100]:  # Limit to first 100 for LLM context
        entity_dict = {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type.value if hasattr(entity.type, 'value') else str(entity.type),
            "display_type": getattr(entity, 'display_type', None),
            "properties": entity.properties or {}
        }
        entity_descriptions.append(entity_dict)
    
    # Prepare relationship descriptions
    relationship_descriptions = []
    for edge in relationships[:50]:  # Limit to first 50
        # Handle both Edge objects and dicts
        if hasattr(edge, 'source'):
            # Edge object
            rel_dict = {
                "source_id": edge.source,
                "target_id": edge.target,
                "type": edge.type.value if hasattr(edge.type, 'value') else str(edge.type),
                "properties": edge.properties or {}
            }
        else:
            # Dict
            rel_dict = {
                "source_id": edge.get("source") or edge.get("source_id"),
                "target_id": edge.get("target") or edge.get("target_id"),
                "type": edge.get("type") or edge.get("relationship_type"),
                "properties": edge.get("properties", {})
            }
        relationship_descriptions.append(rel_dict)
    
    # LLM prompt to identify risk-relevant entities and relationships
    system_prompt = """You are a financial risk analysis expert. Given a specific risk, identify which entities and relationships from the knowledge graph are most relevant to understanding and visualizing this risk.

Your task:
1. Identify entities that are DIRECTLY affected by the risk (from affected_entity_ids)
2. Identify entities that are INDIRECTLY related (connected through relationships, contextually relevant)
3. Identify relationships that help explain how the risk impacts entities or how entities relate to the risk
4. Focus on entities and relationships that provide context for understanding the risk's scope and impact

Respond with JSON:
{
  "relevant_entity_ids": ["entity_id_1", "entity_id_2", ...],
  "relevant_relationship_indices": [0, 1, 2, ...],
  "reasoning": "Brief explanation of why these entities/relationships are relevant"
}

Be comprehensive but focused - include entities that help visualize the risk's impact."""

    user_prompt = f"""Risk Details:
- Type: {risk.type}
- Severity: {risk.severity}
- Description: {risk.description}
- Affected Entity IDs: {risk.affected_entity_ids}
- Score: {risk.score}
- Recommendation: {risk.recommendation}

Available Entities ({len(entity_descriptions)}):
{json.dumps(entity_descriptions, indent=2)}

Available Relationships ({len(relationship_descriptions)}):
{json.dumps(relationship_descriptions, indent=2)}

Identify which entity IDs and relationship indices (0-based) are most relevant to understanding this risk. Include:
1. All affected_entity_ids (they are directly relevant)
2. Entities connected to affected entities through relationships
3. Entities mentioned in the risk description or recommendation
4. Relationships that connect relevant entities

Respond with JSON only."""

    try:
        bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        
        response = bedrock.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "temperature": 0.3,
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
        
        if not llm_response:
            # Fallback: use affected entities and their connections
            relevant_ids = set(risk.affected_entity_ids or [])
            relevant_edges = []
            for idx, edge in enumerate(relationships):
                # Handle both Edge objects and dicts
                if hasattr(edge, 'source'):
                    source = edge.source
                    target = edge.target
                else:
                    source = edge.get("source") or edge.get("source_id")
                    target = edge.get("target") or edge.get("target_id")
                
                if source in relevant_ids or target in relevant_ids:
                    relevant_edges.append(idx)
                    if source:
                        relevant_ids.add(source)
                    if target:
                        relevant_ids.add(target)
            
            relevant_entities = [e for e in entities if e.id in relevant_ids]
            relevant_relationships = []
            for i in relevant_edges:
                if i < len(relationships):
                    edge = relationships[i]
                    # Convert Edge object to dict if needed
                    if hasattr(edge, 'model_dump'):
                        relevant_relationships.append(edge.model_dump())
                    elif hasattr(edge, 'source'):
                        relevant_relationships.append({
                            "id": edge.id,
                            "source": edge.source,
                            "target": edge.target,
                            "type": edge.type.value if hasattr(edge.type, 'value') else str(edge.type),
                            "properties": edge.properties or {}
                        })
                    else:
                        relevant_relationships.append(edge)
            
            return {
                "entities": [e.model_dump() if hasattr(e, 'model_dump') else {
                    "id": e.id,
                    "name": e.name,
                    "type": e.type.value if hasattr(e.type, 'value') else str(e.type),
                    "display_type": getattr(e, 'display_type', None),
                    "properties": e.properties or {}
                } for e in relevant_entities],
                "relationships": relevant_relationships,
                "reasoning": "Fallback: using affected entities and direct connections"
            }
        
        # Parse LLM response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = llm_response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            llm_result = json.loads(json_str)
            relevant_entity_ids = set(llm_result.get("relevant_entity_ids", []))
            relevant_rel_indices = set(llm_result.get("relevant_relationship_indices", []))
            
            # Always include affected entities
            relevant_entity_ids.update(risk.affected_entity_ids or [])
            
            # Get relevant entities
            relevant_entities = [e for e in entities if e.id in relevant_entity_ids]
            
            # Get relevant relationships
            relevant_relationships = []
            seen_edge_ids = set()
            
            for idx in relevant_rel_indices:
                if 0 <= idx < len(relationships):
                    edge = relationships[idx]
                    # Convert Edge object to dict if needed
                    if hasattr(edge, 'id'):
                        edge_id = edge.id
                    elif isinstance(edge, dict):
                        edge_id = edge.get("id", f"{idx}")
                    else:
                        edge_id = f"{idx}"
                    
                    if edge_id not in seen_edge_ids:
                        seen_edge_ids.add(edge_id)
                        if hasattr(edge, 'model_dump'):
                            relevant_relationships.append(edge.model_dump())
                        elif hasattr(edge, 'source'):
                            relevant_relationships.append({
                                "id": edge.id,
                                "source": edge.source,
                                "target": edge.target,
                                "type": edge.type.value if hasattr(edge.type, 'value') else str(edge.type),
                                "properties": edge.properties or {}
                            })
                        else:
                            relevant_relationships.append(edge)
            
            # Also include relationships connecting relevant entities
            for edge in relationships:
                # Handle both Edge objects and dicts
                if hasattr(edge, 'source'):
                    source = edge.source
                    target = edge.target
                    edge_id = edge.id
                else:
                    source = edge.get("source") or edge.get("source_id")
                    target = edge.get("target") or edge.get("target_id")
                    edge_id = edge.get("id", "")
                
                if source in relevant_entity_ids and target in relevant_entity_ids:
                    # Avoid duplicates
                    if edge_id not in seen_edge_ids:
                        seen_edge_ids.add(edge_id)
                        if hasattr(edge, 'model_dump'):
                            relevant_relationships.append(edge.model_dump())
                        elif hasattr(edge, 'source'):
                            relevant_relationships.append({
                                "id": edge.id,
                                "source": edge.source,
                                "target": edge.target,
                                "type": edge.type.value if hasattr(edge.type, 'value') else str(edge.type),
                                "properties": edge.properties or {}
                            })
                        else:
                            relevant_relationships.append(edge)
            
            return {
                "entities": [e.model_dump() if hasattr(e, 'model_dump') else {
                    "id": e.id,
                    "name": e.name,
                    "type": e.type.value if hasattr(e.type, 'value') else str(e.type),
                    "display_type": getattr(e, 'display_type', None),
                    "properties": e.properties or {}
                } for e in relevant_entities],
                "relationships": relevant_relationships,
                "reasoning": llm_result.get("reasoning", "LLM-generated risk graph")
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"LLM response: {llm_response[:500]}")
            raise HTTPException(status_code=500, detail="Failed to parse LLM response")
            
    except Exception as e:
        logger.error(f"Error generating risk graph: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating risk graph: {str(e)}")


# ============================================================================
# Document PDF Serving
# ============================================================================

@app.get(f"{settings.API_PREFIX}/documents/{{document_id}}/pdf")
async def get_document_pdf(document_id: str):
    """Serve the original PDF document"""
    document = documents_store.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=document.filename
    )


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


"""
ADE (Agentic Document Extraction) service for LandingAI integration
"""
import io
import json
import asyncio
import os
import mimetypes
import zipfile
import httpx
from typing import Dict, Any, List, Optional
from loguru import logger

from config import settings
from models.document import Document
from services.markdown_analyzer import MarkdownSchemaAnalyzer


class ExtractionService:
    """Handles document extraction using LandingAI ADE API.
    
    Features:
    - Parse documents to markdown using ADE
    - Deterministic schema generation from table structure
    - Automatic retry with exponential backoff
    - Support for single files and ZIP archives
    """
    
    def __init__(self):
        self.api_url = settings.LANDINGAI_API_URL.rstrip("/")
        self.api_key = settings.LANDINGAI_API_KEY
        self.auth_header = {"Authorization": f"Bearer {self.api_key}"}
        # In-memory progress tracking for extractions keyed by document_id
        self._progress: Dict[str, Dict[str, Any]] = {}
        # Create reusable httpx client with retry support
        self.timeout = httpx.Timeout(480.0, connect=10.0)  # 8min total, 10s connect
        self._client: httpx.AsyncClient | None = None
        # Deterministic schema analyzer (no LLM needed)
        self.schema_analyzer = MarkdownSchemaAnalyzer()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared httpx client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, limits=httpx.Limits(max_connections=20))
        return self._client
    
    async def _retry_request(
        self,
        method: str,
        url: str,
        max_retries: int = 2,
        initial_delay: float = 0.5,
        max_delay: float = 8.0,
        **kwargs
    ) -> httpx.Response:
        """
        Execute HTTP request with exponential backoff retry logic.
        
        Retries on:
        - Connection errors (APIConnectionError)
        - 429 Rate Limit
        - 408 Request Timeout
        - 409 Conflict
        - >= 500 Server errors
        
        Based on LandingAI SDK retry patterns.
        """
        client = await self._get_client()
        last_exception = None
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                resp = await client.request(method, url, **kwargs)
                
                # Check if response is retryable
                status = resp.status_code
                if status < 400:
                    return resp
                
                # Don't retry on most client errors
                if 400 <= status < 500:
                    if status not in {408, 409, 429}:  # Non-retryable 4xx
                        resp.raise_for_status()  # Raise immediately for non-retryable
                    # Retryable 4xx - fall through to raise_for_status in except
                
                # 5xx errors and retryable 4xx - raise to trigger retry
                resp.raise_for_status()
                
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                
                # If this was the last attempt, raise
                if attempt >= max_retries:
                    logger.error(f"Request failed after {max_retries + 1} attempts: {e}")
                    raise
                
                # Calculate backoff delay
                delay = min(initial_delay * (2 ** attempt), max_delay)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)
        
        # Should never reach here, but for type safety
        if last_exception:
            raise last_exception
        raise httpx.HTTPError("Request failed without exception")
    
    async def generate_adaptive_schema(
        self,
        markdown: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an optimal extraction schema by analyzing the document structure.
        Uses deterministic markdown analysis - no LLM needed!
        
        Args:
            markdown: Parsed markdown from ADE Parse
            metadata: Optional document metadata (filename, page count, etc.)
            
        Returns:
            JSON Schema dict optimized for the document structure
        """
        try:
            logger.info(f"DETERMINISTIC SCHEMA ANALYSIS - Starting...")
            logger.info(f"Markdown length: {len(markdown)} chars")
            
            # Use deterministic analyzer to understand structure
            logger.info("Calling markdown analyzer...")
            schema = self.schema_analyzer.analyze_and_generate_schema(markdown)
            logger.info(f"Schema analyzer returned schema with {len(schema.get('properties', {}))} properties")
            
            # Log the generated schema
            logger.info(f"SCHEMA GENERATED:")
            logger.info(f"{'='*60}")
            logger.info(json.dumps(schema, indent=2))
            logger.info(f"{'='*60}")
            
            # Save schema to /tmp for inspection
            import time
            timestamp = int(time.time())
            schema_file = f"/tmp/adaptive_schema_{timestamp}.json"
            try:
                with open(schema_file, "w", encoding="utf-8") as sf:
                    json.dump({
                        "document_metadata": metadata,
                        "markdown_length": len(markdown),
                        "generated_schema": schema,
                        "timestamp": timestamp,
                        "method": "deterministic_analysis"
                    }, sf, indent=2)
                logger.info(f"Schema saved to: {schema_file}")
            except Exception as e:
                logger.warning(f"Could not save schema: {e}")
            
            return schema
            
        except Exception as e:
            logger.error(f"Error in schema analysis: {e}", exc_info=True)
            return self._get_default_schema()
    
    def _get_default_schema(self) -> Dict[str, Any]:
        """Fallback default schema if adaptive generation fails"""
        return {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Executive summary of the document"}
            }
        }
    
    async def extract_document_with_adaptive_schema(self, document: Document) -> Dict[str, Any]:
        """
        Extract using AI-generated adaptive schema.
        
        Workflow:
        1. Parse document with ADE → get markdown
        2. Call Claude with markdown → generate optimal schema
        3. Use schema for ADE Extract → get structured data
        
        This is the most intelligent extraction mode.
        """
        logger.info(f"Starting adaptive schema extraction for document: {document.id}")
        
        try:
            if self._is_zip(document.file_path):
                logger.warning("Adaptive schema not supported for ZIP files yet, using default extraction")
                return await self.extract_document(document)
            
            # Parse first to get markdown
            with open(document.file_path, "rb") as f:
                content = f.read()
            
            parse_json = await self._ade_parse(document.filename, content, document.mime_type)
            markdown = parse_json.get("markdown", "")
            metadata = parse_json.get("metadata", {})
            
            # Store markdown in document for later use (chunking, search)
            document.metadata["markdown"] = markdown
            document.metadata["parse_metadata"] = metadata
            
            if not markdown:
                logger.warning("No markdown from ADE Parse, falling back to default extraction")
                return await self.extract_document(document)
            
            # Generate adaptive schema using Claude
            logger.info("Generating adaptive schema with Claude...")
            adaptive_schema = await self.generate_adaptive_schema(markdown, metadata)
            
            # Use the generated schema for extraction
            logger.info(f"Extracting with adaptive schema: {len(adaptive_schema.get('properties', {}))} properties")
            extract_json = await self._ade_extract(markdown, adaptive_schema)
            
            # Merge results
            result = self._merge_parse_and_extract(parse_json, extract_json)
            
            logger.info(
                f"Adaptive extraction completed for {document.id}: "
                f"{len(result.get('entities', []))} entities, "
                f"{len(result.get('key_values', []))} key-values"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Adaptive extraction error for {document.id}: {str(e)}")
            logger.info("Falling back to default extraction")
            return await self.extract_document(document)
    
    async def extract_document(self, document: Document) -> Dict[str, Any]:
        """Extract structured data using ADE: Parse -> Extract (schema over markdown).

        If Extract returns a 4xx (e.g., schema mismatch), fall back to Parse-only
        output so the pipeline can proceed.
        """
        logger.info(f"Starting ADE extraction for document: {document.id}")
        try:
            if self._is_zip(document.file_path):
                # Initialize progress for ZIP: count supported files first
                total = self._count_supported_in_zip(document.file_path)
                self._progress[document.id] = {"status": "processing", "total": total, "completed": 0, "failed": 0}
                results = await self._extract_from_zip(document.file_path, progress_key=document.id)
                parsed = self._aggregate_results(results)
                logger.info(
                    f"Aggregated ADE extraction for ZIP {document.id}: "
                    f"{len(parsed.get('entities', []))} entities"
                )
                self._progress[document.id]["status"] = "completed"
                return parsed
            else:
                # Route based on file size: large files use async jobs path
                if document.file_size and document.file_size > settings.ADE_SYNC_MAX_BYTES:
                    self._progress[document.id] = {"status": "processing", "total": 1, "completed": 0, "failed": 0}
                    with open(document.file_path, "rb") as f:
                        content = f.read()
                    parsed = await self._extract_via_jobs_bytes(
                        filename=document.filename,
                        content=content,
                        mime_type=document.mime_type
                    )
                    logger.info(
                        f"ADE extraction (async) completed for {document.id}: "
                        f"{len(parsed.get('entities', []))} entities"
                    )
                    self._progress[document.id]["completed"] = 1
                    self._progress[document.id]["status"] = "completed"
                    return parsed

                # Single file progress
                self._progress[document.id] = {"status": "processing", "total": 1, "completed": 0, "failed": 0}
                parsed = await self._extract_via_parse_then_extract(
                    file_path=document.file_path,
                    filename=document.filename,
                    mime_type=document.mime_type
                )
                logger.info(
                    f"ADE extraction completed for {document.id}: "
                    f"{len(parsed.get('entities', []))} entities"
                )
                self._progress[document.id]["completed"] = 1
                self._progress[document.id]["status"] = "completed"
                return parsed
        except httpx.HTTPError as e:
            logger.error(f"ADE API error for {document.id}: {str(e)}")
            raise Exception(f"ADE extraction failed: {str(e)}")
        except Exception as e:
            logger.error(f"Extraction error for {document.id}: {str(e)}")
            raise
    
    def _is_zip(self, file_path: str) -> bool:
        return file_path.lower().endswith(".zip")

    async def _extract_from_zip(self, zip_path: str, progress_key: str | None = None) -> List[Dict[str, Any]]:
        """Extract supported files within a ZIP and run ADE Extract on each."""
        results: List[Dict[str, Any]] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            tasks: List[asyncio.Task] = []
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                mime_type, _ = mimetypes.guess_type(name)
                if not self._is_supported_mime(mime_type):
                    logger.debug(f"Skipping unsupported file in ZIP: {name}")
                    continue
                with zf.open(name) as file_member:
                    file_bytes = file_member.read()
                # submit each file as an async job path (faster for large docs)
                task = asyncio.create_task(
                    self._extract_via_jobs_bytes(
                        filename=os.path.basename(name),
                        content=file_bytes,
                        mime_type=mime_type or "application/octet-stream",
                    )
                )
                if progress_key:
                    def _inc(_):
                        try:
                            self._progress[progress_key]["completed"] += 1
                        except Exception:
                            pass
                    task.add_done_callback(_inc)
                tasks.append(task)
            if tasks:
                results = await asyncio.gather(*tasks)
        return results

    def _count_supported_in_zip(self, zip_path: str) -> int:
        count = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                mime_type, _ = mimetypes.guess_type(name)
                if self._is_supported_mime(mime_type):
                    count += 1
        return count

    async def _extract_via_parse_then_extract(self, file_path: str, filename: str, mime_type: str, schema: Dict[str, Any] | None = None) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            content = f.read()
        return await self._extract_via_parse_then_extract_bytes(filename, content, mime_type, schema)

    async def _extract_via_parse_then_extract_bytes(self, filename: str, content: bytes, mime_type: str, schema: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Run ADE Parse on the binary, then ADE Extract on the returned markdown.

        Reference: ADE Extract requires 'schema' and 'markdown' per docs:
        https://docs.landing.ai/api-reference/tools/ade-extract
        """
        # Step 1: Parse document -> markdown
        parse_json = await self._ade_parse(filename, content, mime_type)
        markdown = parse_json.get("markdown") or ""
        # Step 2: Extract using a default financial schema over markdown
        try:
            extract_json = await self._ade_extract(markdown, schema)
        except httpx.HTTPStatusError:
            # Fallback to parse-only output if schema extraction fails
            logger.warning("ADE Extract failed; falling back to Parse-only output")
            return self._from_parse_only(parse_json)
        # Merge parse + extract into normalized shape
        return self._merge_parse_and_extract(parse_json, extract_json)

    async def _ade_parse(self, filename: str, content: bytes, mime_type: str) -> Dict[str, Any]:
        url = f"{self.api_url}/ade/parse"
        files = {"document": (filename, io.BytesIO(content), mime_type)}
        resp = await self._retry_request("POST", url, headers=self.auth_header, files=files)
        result = resp.json()
        
        # Log and save parsed markdown for inspection
        if "markdown" in result:
            markdown_content = result["markdown"]
            logger.info(f"ADE PARSE SUCCESS for '{filename}'")
            logger.info(f"Markdown length: {len(markdown_content)} characters")
            logger.info(f"First 500 chars of markdown:\n{'='*60}\n{markdown_content[:500]}...\n{'='*60}")
            
            # Save full markdown to /tmp for inspection
            safe_filename = filename.replace("/", "_").replace(" ", "_")
            markdown_file = f"/tmp/ade_parsed_{safe_filename}.md"
            try:
                with open(markdown_file, "w", encoding="utf-8") as mf:
                    mf.write(f"# ADE Parse Result for: {filename}\n\n")
                    mf.write(f"**File:** {filename}\n")
                    mf.write(f"**MIME:** {mime_type}\n")
                    mf.write(f"**Length:** {len(markdown_content)} characters\n\n")
                    mf.write("---\n\n")
                    mf.write(markdown_content)
                logger.info(f"Full markdown saved to: {markdown_file}")
            except Exception as e:
                logger.warning(f"Could not save markdown file: {e}")
        else:
            logger.warning(f"⚠️  ADE Parse returned no markdown for '{filename}'")
        
        return result

    async def _ade_extract(self, markdown: str, schema: Dict[str, Any] | None = None, model: str = "extract-20251024") -> Dict[str, Any]:
        url = f"{self.api_url}/ade/extract"
        # Minimal default schema that extracts a free-form summary and any fields it can map.
        default_schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"}
            }
        }
        
        used_schema = schema or default_schema
        
        # Log schema being used
        logger.info(f"ADE EXTRACT - Using Model: {model}")
        logger.info(f"ADE EXTRACT - Using Schema:")
        logger.info(f"{'='*60}")
        logger.info(json.dumps(used_schema, indent=2))
        logger.info(f"{'='*60}")
        logger.info(f"Markdown input length: {len(markdown)} characters")
        
        data = {
            "schema": json.dumps(used_schema),  # send schema as JSON string per docs
            "markdown": markdown,
            "model": model  # Use the new extract model for better extraction
        }
        resp = await self._retry_request("POST", url, headers=self.auth_header, data=data)
        result = resp.json()
        
        # Log extraction results
        logger.info(f"ADE EXTRACT SUCCESS")
        logger.info(f"Extraction result keys: {list(result.keys())}")
        logger.info(f"Full extraction result:")
        logger.info(f"{'='*60}")
        logger.info(json.dumps(result, indent=2))
        logger.info(f"{'='*60}")
        
        # Save extraction result to /tmp for inspection
        import time
        timestamp = int(time.time())
        result_file = f"/tmp/ade_extract_result_{timestamp}.json"
        try:
            with open(result_file, "w", encoding="utf-8") as rf:
                json.dump({
                    "schema_used": used_schema,
                    "markdown_length": len(markdown),
                    "extraction_result": result,
                    "timestamp": timestamp
                }, rf, indent=2)
            logger.info(f"Extraction result saved to: {result_file}")
        except Exception as e:
            logger.warning(f"Could not save extraction result: {e}")
        
        return result

    # ------------------------ ASYNC JOB HELPERS ------------------------
    async def _ade_parse_job(self, filename: str, content: bytes, mime_type: str) -> str:
        """Submit a parse job; returns job_id."""
        url = f"{self.api_url}/ade/parse/jobs"
        files = {"document": (filename, io.BytesIO(content), mime_type)}
        data = {"split": "page"}
        resp = await self._retry_request("POST", url, headers=self.auth_header, files=files, data=data)
        body = resp.json()
        # Try multiple shapes defensively
        job_id = (
            body.get("job_id")
            or body.get("metadata", {}).get("job_id")
            or (body.get("job") or {}).get("id")
        )
        if not job_id:
            logger.error(f"ADE parse job response missing job_id: {body}")
            raise httpx.HTTPStatusError("Missing job_id in response", request=resp.request, response=resp)
        return job_id

    async def _ade_get_job(self, job_id: str) -> Dict[str, Any]:
        url = f"{self.api_url}/ade/jobs/{job_id}"
        try:
            resp = await self._retry_request("GET", url, headers=self.auth_header)
            return resp.json()
        except httpx.HTTPStatusError as e:
            # Some backends exhibit eventual consistency; treat early 404 as pending
            if e.response is not None and e.response.status_code == 404:
                return {"status": "pending"}
            raise

    async def _extract_via_jobs_bytes(self, filename: str, content: bytes, mime_type: str) -> Dict[str, Any]:
        """Submit parse job, poll until complete, then extract with schema."""
        job_id = await self._ade_parse_job(filename, content, mime_type)
        # Polling with backoff
        delay = 1.0
        max_delay = 8.0
        for _ in range(60):  # ~1-2 minutes max
            job = await self._ade_get_job(job_id)
            status = (job.get("status") or job.get("metadata", {}).get("status") or "").lower()
            if status in {"completed", "succeeded", "success"}:
                markdown = job.get("markdown") or job.get("result", {}).get("markdown", "")
                try:
                    extract_json = await self._ade_extract(markdown)
                except httpx.HTTPStatusError:
                    logger.warning("ADE Extract failed for job; falling back to Parse-only output")
                    return self._from_parse_only(job)
                return self._merge_parse_and_extract(job, extract_json)
            if status in {"failed", "error"}:
                logger.error(f"ADE parse job failed: {job}")
                return self._from_parse_only(job)
            await asyncio.sleep(delay)
            delay = min(max_delay, delay * 1.5)
        logger.warning("ADE parse job polling timed out; returning parse-only")
        job = await self._ade_get_job(job_id)
        return self._from_parse_only(job)

    def _from_parse_only(self, parse_json: Dict[str, Any]) -> Dict[str, Any]:
        # Keep entities/tables empty; surface metadata and markdown as key_values summary
        return {
            "entities": [],
            "tables": [],
            "key_values": [],
            "metadata": {
                "total_pages": (parse_json.get("metadata", {}) or {}).get("page_count", 0),
                "confidence_score": None,
                "extraction_id": None,
            }
        }

    def _merge_parse_and_extract(self, parse_json: Dict[str, Any], extract_json: Dict[str, Any]) -> Dict[str, Any]:
        key_values = []
        extraction = extract_json.get("extraction") or {}
        if isinstance(extraction, dict):
            for k, v in extraction.items():
                key_values.append({"key": k, "value": v})
        return {
            "entities": [],
            "tables": [],
            "key_values": key_values,
            "metadata": {
                "total_pages": (parse_json.get("metadata", {}) or {}).get("page_count", 0),
                "confidence_score": None,
                "extraction_id": None,
            }
        }

    # ------------------------ PUBLIC PROGRESS API ------------------------
    def get_progress(self, document_id: str) -> Dict[str, Any] | None:
        return self._progress.get(document_id)

    def _is_supported_mime(self, mime_type: str | None) -> bool:
        supported = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.presentation",
            "image/jpeg",
            "image/png",
        }
        return (mime_type or "") in supported

    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate ADE outputs from multiple files into a single normalized structure."""
        combined_entities: List[Dict[str, Any]] = []
        combined_tables: List[Dict[str, Any]] = []
        combined_key_values: List[Dict[str, Any]] = []
        total_pages = 0
        confidences: List[float] = []
        for r in results:
            parsed = self._parse_ade_output(r)
            combined_entities.extend(parsed.get("entities", []))
            combined_tables.extend(parsed.get("tables", []))
            combined_key_values.extend(parsed.get("key_values", []))
            meta = parsed.get("metadata", {})
            total_pages += int(meta.get("total_pages", 0) or 0)
            if meta.get("confidence_score") is not None:
                confidences.append(float(meta.get("confidence_score") or 0.0))
        avg_conf = sum(confidences) / len(confidences) if confidences else None
        return {
            "entities": combined_entities,
            "tables": combined_tables,
            "key_values": combined_key_values,
            "metadata": {
                "total_pages": total_pages,
                "confidence_score": avg_conf,
                "extraction_id": None,
            },
        }

    def _parse_ade_output(self, ade_output: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and normalize ADE output into entities/tables/key_values + metadata.

        This is a defensive mapper to keep our downstream normalizer stable while
        ADE evolves. It attempts reasonable defaults if fields are missing.
        """
        entities: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []
        key_values: List[Dict[str, Any]] = []

        # Entities
        for ent in ade_output.get("entities", []):
            entities.append({
                "type": ent.get("type") or ent.get("entity_type"),
                "name": ent.get("name") or ent.get("text"),
                "properties": ent.get("attributes") or ent.get("properties") or {},
                "citations": self._extract_citations(ent),
            })

        # Tables
        for tbl in ade_output.get("tables", []):
            tables.append({
                "id": tbl.get("id"),
                "page": tbl.get("page"),
                "headers": tbl.get("headers", []),
                "rows": tbl.get("rows", []),
                "caption": tbl.get("caption"),
            })

        # Key-Values (defensive: ensure list)
        key_values_raw = ade_output.get("key_values", [])
        key_values = key_values_raw if isinstance(key_values_raw, list) else []
        
        # Metadata (page_count / confidence fields vary by endpoint)
        meta = ade_output.get("metadata", {})
        total_pages = meta.get("page_count") or ade_output.get("page_count") or 0
        confidence = meta.get("confidence") or ade_output.get("confidence")
        extraction_id = ade_output.get("extraction_id") or meta.get("extraction_id")
        
        return {
            "entities": entities,
            "tables": tables,
            "key_values": key_values,
            "metadata": {
                "total_pages": total_pages or 0,
                "confidence_score": confidence,
                "extraction_id": extraction_id,
            },
        }
    
    def _extract_citations(self, entity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        citations: List[Dict[str, Any]] = []
        locations = entity_data.get("locations") or entity_data.get("citations") or []
        for loc in locations:
            citations.append({
                "page": loc.get("page"),
                "section": loc.get("section"),
                "table_id": loc.get("table_id"),
                "cell": loc.get("cell"),
                "confidence": loc.get("confidence"),
            })
        return citations
    
    async def close(self):
        """Close the httpx client and cleanup resources"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("ExtractionService: closed httpx client")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


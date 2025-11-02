"""
ADE (Agentic Document Extraction) service for LandingAI integration
"""
import io
import json
import os
import zipfile
import mimetypes
import httpx
from typing import Dict, Any, List, Tuple
from loguru import logger

from config import settings
from models.document import Document


class ExtractionService:
    """Handles document extraction using LandingAI ADE API (synchronous Extract).

    This implementation uses POST /v1/ade/extract for single files. If the source is a
    ZIP archive, it will extract supported files and aggregate their results.
    Docs: https://docs.landing.ai/api-reference/tools/
    """
    
    def __init__(self):
        self.api_url = settings.LANDINGAI_API_URL.rstrip("/")
        self.api_key = settings.LANDINGAI_API_KEY
        self.auth_header = {"Authorization": f"Bearer {self.api_key}"}
        # Default schema name; can be adjusted later or made configurable
        self.default_schema = "financial_entities"
    
    async def extract_document(self, document: Document) -> Dict[str, Any]:
        """Extract structured data using ADE: Parse -> Extract (schema over markdown).

        If Extract returns a 4xx (e.g., schema mismatch), fall back to Parse-only
        output so the pipeline can proceed.
        """
        logger.info(f"Starting ADE extraction for document: {document.id}")
        try:
            if self._is_zip(document.file_path):
                results = await self._extract_from_zip(document.file_path)
                parsed = self._aggregate_results(results)
                logger.info(
                    f"Aggregated ADE extraction for ZIP {document.id}: "
                    f"{len(parsed.get('entities', []))} entities"
                )
                return parsed
            else:
                parsed = await self._extract_via_parse_then_extract(
                    file_path=document.file_path,
                    filename=document.filename,
                    mime_type=document.mime_type
                )
                logger.info(
                    f"ADE extraction completed for {document.id}: "
                    f"{len(parsed.get('entities', []))} entities"
                )
                return parsed
        except httpx.HTTPError as e:
            logger.error(f"ADE API error for {document.id}: {str(e)}")
            raise Exception(f"ADE extraction failed: {str(e)}")
        except Exception as e:
            logger.error(f"Extraction error for {document.id}: {str(e)}")
            raise

    def _is_zip(self, file_path: str) -> bool:
        return file_path.lower().endswith(".zip")

    async def _extract_from_zip(self, zip_path: str) -> List[Dict[str, Any]]:
        """Extract supported files within a ZIP and run ADE Extract on each."""
        results: List[Dict[str, Any]] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                mime_type, _ = mimetypes.guess_type(name)
                if not self._is_supported_mime(mime_type):
                    logger.debug(f"Skipping unsupported file in ZIP: {name}")
                    continue
                with zf.open(name) as file_member:
                    file_bytes = file_member.read()
                    ade_json = await self._extract_via_parse_then_extract_bytes(
                        filename=os.path.basename(name),
                        content=file_bytes,
                        mime_type=mime_type or "application/octet-stream",
                    )
                    results.append(ade_json)
        return results

    async def _extract_via_parse_then_extract(self, file_path: str, filename: str, mime_type: str) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            content = f.read()
        return await self._extract_via_parse_then_extract_bytes(filename, content, mime_type)

    async def _extract_via_parse_then_extract_bytes(self, filename: str, content: bytes, mime_type: str) -> Dict[str, Any]:
        """Run ADE Parse on the binary, then ADE Extract on the returned markdown.

        Reference: ADE Extract requires 'schema' and 'markdown' per docs:
        https://docs.landing.ai/api-reference/tools/ade-extract
        """
        # Step 1: Parse document -> markdown
        parse_json = await self._ade_parse(filename, content, mime_type)
        markdown = parse_json.get("markdown") or ""
        # Step 2: Extract using a default financial schema over markdown
        try:
            extract_json = await self._ade_extract(markdown)
        except httpx.HTTPStatusError:
            # Fallback to parse-only output if schema extraction fails
            logger.warning("ADE Extract failed; falling back to Parse-only output")
            return self._from_parse_only(parse_json)
        # Merge parse + extract into normalized shape
        return self._merge_parse_and_extract(parse_json, extract_json)

    async def _ade_parse(self, filename: str, content: bytes, mime_type: str) -> Dict[str, Any]:
        url = f"{self.api_url}/ade/parse"
        files = {"document": (filename, io.BytesIO(content), mime_type)}
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(url, headers=self.auth_header, files=files)
            resp.raise_for_status()
            return resp.json()

    async def _ade_extract(self, markdown: str) -> Dict[str, Any]:
        url = f"{self.api_url}/ade/extract"
        # Minimal default schema that extracts a free-form summary and any fields it can map.
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"}
            }
        }
        data = {
            "schema": json.dumps(schema),  # send schema as JSON string per docs
            "markdown": markdown
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(url, headers=self.auth_header, data=data)
            resp.raise_for_status()
            return resp.json()

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

        # Key-Values
        if "key_values" in ade_output:
            key_values = ade_output.get("key_values", [])

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


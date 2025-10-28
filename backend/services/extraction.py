"""
ADE (Agentic Document Extraction) service for LandingAI integration
"""
import httpx
from typing import Dict, Any, List
from loguru import logger

from config import settings
from models.document import Document, DocumentStatus
from models.citation import Citation


class ExtractionService:
    """Handles document extraction using LandingAI ADE API"""
    
    def __init__(self):
        self.api_url = settings.LANDINGAI_API_URL
        self.api_key = settings.LANDINGAI_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def extract_document(self, document: Document) -> Dict[str, Any]:
        """
        Extract structured data from document using ADE
        
        Args:
            document: Document to extract
            
        Returns:
            dict: ADE extraction results with entities and citations
        """
        logger.info(f"Starting ADE extraction for document: {document.id}")
        
        try:
            # Read document file
            with open(document.file_path, "rb") as f:
                file_content = f.read()
            
            # Call LandingAI ADE API
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Upload document
                upload_response = await client.post(
                    f"{self.api_url}/documents",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"file": (document.filename, file_content, document.mime_type)}
                )
                upload_response.raise_for_status()
                upload_data = upload_response.json()
                
                # Extract with ADE
                extraction_response = await client.post(
                    f"{self.api_url}/extract",
                    headers=self.headers,
                    json={
                        "document_id": upload_data["document_id"],
                        "schema": "financial_entities",
                        "extract_tables": True,
                        "extract_key_values": True,
                        "extract_sections": True
                    }
                )
                extraction_response.raise_for_status()
                ade_output = extraction_response.json()
            
            logger.info(
                f"ADE extraction completed for {document.id}: "
                f"{len(ade_output.get('entities', []))} entities found"
            )
            
            # Parse ADE output
            parsed_output = self._parse_ade_output(ade_output)
            
            return parsed_output
            
        except httpx.HTTPError as e:
            logger.error(f"ADE API error for {document.id}: {str(e)}")
            raise Exception(f"ADE extraction failed: {str(e)}")
        except Exception as e:
            logger.error(f"Extraction error for {document.id}: {str(e)}")
            raise
    
    def _parse_ade_output(self, ade_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and normalize ADE output
        
        Args:
            ade_output: Raw ADE API response
            
        Returns:
            dict: Normalized extraction data
        """
        entities = []
        
        # Extract entities from ADE response
        for entity_data in ade_output.get("entities", []):
            entity = {
                "type": entity_data.get("type"),
                "name": entity_data.get("text"),
                "properties": entity_data.get("attributes", {}),
                "citations": self._extract_citations(entity_data)
            }
            entities.append(entity)
        
        # Extract tables
        tables = []
        for table_data in ade_output.get("tables", []):
            table = {
                "id": table_data.get("id"),
                "page": table_data.get("page"),
                "headers": table_data.get("headers", []),
                "rows": table_data.get("rows", []),
                "caption": table_data.get("caption")
            }
            tables.append(table)
        
        # Extract key-value pairs
        key_values = ade_output.get("key_values", [])
        
        return {
            "entities": entities,
            "tables": tables,
            "key_values": key_values,
            "metadata": {
                "total_pages": ade_output.get("page_count", 0),
                "confidence_score": ade_output.get("confidence", 0.0),
                "extraction_id": ade_output.get("extraction_id")
            }
        }
    
    def _extract_citations(self, entity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract citation information from entity data"""
        citations = []
        
        for location in entity_data.get("locations", []):
            citation = {
                "page": location.get("page"),
                "section": location.get("section"),
                "table_id": location.get("table_id"),
                "cell": location.get("cell"),
                "confidence": location.get("confidence")
            }
            citations.append(citation)
        
        return citations


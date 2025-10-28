"""
Document ingestion service
"""
import os
import uuid
from pathlib import Path
from typing import BinaryIO
from datetime import datetime

from models.document import Document, DocumentStatus
from config import settings
from loguru import logger


class IngestionService:
    """Handles document upload and validation"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def ingest_document(
        self,
        file: BinaryIO,
        filename: str,
        mime_type: str
    ) -> Document:
        """
        Ingest a document file
        
        Args:
            file: File binary stream
            filename: Original filename
            mime_type: MIME type of the file
            
        Returns:
            Document: Created document object
        """
        # Generate unique document ID
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        # Validate file type
        if not self._is_valid_file_type(mime_type):
            raise ValueError(f"Unsupported file type: {mime_type}")
        
        # Save file
        file_extension = Path(filename).suffix
        safe_filename = f"{doc_id}{file_extension}"
        file_path = self.upload_dir / safe_filename
        
        # Write file to disk
        file_size = 0
        with open(file_path, "wb") as f:
            content = file.read()
            file_size = len(content)
            
            # Check file size
            if file_size > settings.MAX_UPLOAD_SIZE:
                raise ValueError(
                    f"File too large: {file_size} bytes "
                    f"(max: {settings.MAX_UPLOAD_SIZE})"
                )
            
            f.write(content)
        
        logger.info(f"Ingested document: {doc_id} ({filename}, {file_size} bytes)")
        
        # Create document object
        document = Document(
            id=doc_id,
            filename=filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=mime_type,
            status=DocumentStatus.UPLOADED,
            uploaded_at=datetime.utcnow()
        )
        
        return document
    
    def _is_valid_file_type(self, mime_type: str) -> bool:
        """Check if file type is supported"""
        valid_types = [
            "application/pdf",
            "application/zip",
            "application/x-zip-compressed",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/csv"
        ]
        return mime_type in valid_types
    
    async def get_document(self, document_id: str) -> Document:
        """
        Retrieve document by ID
        
        TODO: Implement database storage
        For now, this is a placeholder
        """
        raise NotImplementedError("Database integration pending")
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and its associated files
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            bool: True if deleted successfully
        """
        # TODO: Implement database lookup and deletion
        logger.info(f"Deleting document: {document_id}")
        return True


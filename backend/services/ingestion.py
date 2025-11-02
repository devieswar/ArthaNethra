"""
Document ingestion service
"""
import os
import mimetypes
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
            # Documents
            "application/pdf",
            "application/msword",  # .doc
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/vnd.ms-powerpoint",  # .ppt
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
            "application/vnd.oasis.opendocument.text",  # .odt
            "application/vnd.oasis.opendocument.presentation",  # .odp
            # Images
            "image/jpeg",
            "image/png",
            # Archives
            "application/zip",
            "application/x-zip-compressed",
            # Optional tabular types if needed later
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/csv",
        ]
        return mime_type in valid_types
    
    async def get_document(self, document_id: str) -> Document | None:
        """
        Retrieve document by ID.
        If not tracked in memory by the caller, attempt to reconstruct from disk
        by locating a file named like {document_id}.* in the uploads directory.
        """
        # Find a file that starts with the document_id in the upload dir
        for path in self.upload_dir.glob(f"{document_id}.*"):
            try:
                stat = path.stat()
                mime_type, _ = mimetypes.guess_type(str(path))
                document = Document(
                    id=document_id,
                    filename=path.name,
                    file_path=str(path),
                    file_size=stat.st_size,
                    mime_type=mime_type or "application/octet-stream",
                    status=DocumentStatus.UPLOADED,
                    uploaded_at=datetime.utcfromtimestamp(stat.st_mtime)
                )
                logger.info(f"Loaded document from disk: {document_id} -> {path}")
                return document
            except Exception as e:
                logger.warning(f"Failed to load document {document_id} from {path}: {e}")
        return None
    
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


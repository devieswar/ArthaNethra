"""
Document model
"""
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional


class DocumentStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    NORMALIZING = "normalizing"
    NORMALIZED = "normalized"
    INDEXING = "indexing"
    INDEXED = "indexed"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BaseModel):
    """Document data model"""
    
    id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Path to stored file")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING)
    
    # Processing results
    extraction_id: Optional[str] = None
    graph_id: Optional[str] = None
    entities_count: int = 0
    edges_count: int = 0
    
    # Metadata
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # ADE results
    ade_output: Optional[dict] = None
    confidence_score: Optional[float] = None
    total_pages: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_abc123",
                "filename": "10K_2025.pdf",
                "file_path": "./uploads/doc_abc123.pdf",
                "file_size": 2048576,
                "mime_type": "application/pdf",
                "status": "completed",
                "entities_count": 156,
                "edges_count": 234
            }
        }


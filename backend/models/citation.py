"""
Citation model for evidence linking
"""
from pydantic import BaseModel, Field
from typing import Optional


class Citation(BaseModel):
    """Citation linking insights to source documents"""
    
    page: int = Field(..., description="Page number in document")
    section: Optional[str] = Field(None, description="Section or heading name")
    table_id: Optional[str] = Field(None, description="Table identifier")
    cell: Optional[str] = Field(None, description="Cell coordinate (e.g., 'B5')")
    clause: Optional[str] = Field(None, description="Clause or paragraph identifier")
    confidence: Optional[float] = Field(None, description="Extraction confidence score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": 89,
                "section": "Note 8: Debt",
                "table_id": "T3.2.1",
                "cell": "B5",
                "confidence": 0.94
            }
        }


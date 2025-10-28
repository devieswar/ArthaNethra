"""
Entity model for knowledge graph
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime


class EntityType(str, Enum):
    """Types of financial entities"""
    COMPANY = "Company"
    SUBSIDIARY = "Subsidiary"
    LOAN = "Loan"
    INVOICE = "Invoice"
    METRIC = "Metric"
    CLAUSE = "Clause"
    INSTRUMENT = "Instrument"
    VENDOR = "Vendor"
    PERSON = "Person"
    LOCATION = "Location"


class Entity(BaseModel):
    """Entity in the knowledge graph"""
    
    id: str = Field(..., description="Unique entity identifier")
    type: EntityType = Field(..., description="Entity type")
    name: str = Field(..., description="Entity name")
    
    # Properties extracted from documents
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Citations (source evidence)
    citations: List["Citation"] = Field(default_factory=list)
    
    # Vector embedding for semantic search
    embedding: Optional[List[float]] = None
    
    # Graph metadata
    document_id: str = Field(..., description="Source document ID")
    graph_id: str = Field(..., description="Knowledge graph ID")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "ent_1",
                "type": "Company",
                "name": "ACME Corporation",
                "properties": {
                    "industry": "Technology",
                    "fiscal_year": 2025,
                    "revenue": 1000000000
                },
                "citations": [
                    {
                        "page": 47,
                        "section": "Business Overview"
                    }
                ],
                "document_id": "doc_abc123",
                "graph_id": "graph_xyz789"
            }
        }


from .citation import Citation
Entity.model_rebuild()


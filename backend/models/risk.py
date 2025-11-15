"""
Risk model
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from .citation import Citation


class RiskSeverity(str, Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Risk(BaseModel):
    """Risk detected in financial documents"""
    
    id: str = Field(..., description="Unique risk identifier")
    type: str = Field(..., description="Risk type or category")
    severity: RiskSeverity = Field(..., description="Risk severity level")
    description: str = Field(..., description="Human-readable risk description")
    
    # Affected entities
    affected_entity_ids: List[str] = Field(default_factory=list)
    
    # Evidence
    citations: List[Citation] = Field(default_factory=list)
    
    # Risk metrics
    score: float = Field(..., ge=0.0, le=1.0, description="Risk score (0-1)")
    threshold: float = Field(..., description="Threshold that triggered this risk")
    actual_value: float = Field(..., description="Actual measured value")
    
    # Recommendations
    recommendation: str = Field(..., description="Suggested action or mitigation")
    
    # Graph visualization data (entities and relationships relevant to this risk)
    graph_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Graph elements (entities and relationships) relevant to this risk for visualization"
    )
    
    # Metadata
    document_id: str = Field(..., description="Source document ID")
    graph_id: str = Field(..., description="Knowledge graph ID")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "risk_1",
                "type": "Interest Rate Risk",
                "severity": "high",
                "description": "Variable-rate debt exceeds 8% threshold",
                "affected_entity_ids": ["ent_2"],
                "citations": [
                    {
                        "page": 89,
                        "section": "Note 8: Debt",
                        "table_id": "T3.2.1"
                    }
                ],
                "score": 0.85,
                "threshold": 0.08,
                "actual_value": 0.0875,
                "recommendation": "Consider hedging strategies or refinancing",
                "document_id": "doc_abc123",
                "graph_id": "graph_xyz789"
            }
        }


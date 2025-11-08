"""
Edge (relationship) model for knowledge graph
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Dict, Any
from datetime import datetime


class EdgeType(str, Enum):
    """Types of relationships between entities"""
    HAS_LOAN = "HAS_LOAN"
    OWNS = "OWNS"
    PARTY_TO = "PARTY_TO"
    HAS_METRIC = "HAS_METRIC"
    CONTAINS = "CONTAINS"
    REPORTS_TO = "REPORTS_TO"
    ISSUED_BY = "ISSUED_BY"
    GUARANTEES = "GUARANTEES"
    RELATED_TO = "RELATED_TO"
    LOCATED_IN = "LOCATED_IN"
    WORKS_FOR = "WORKS_FOR"
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    SUPPLIES_TO = "SUPPLIES_TO"
    MENTIONED_IN = "MENTIONED_IN"
    ACQUIRED = "ACQUIRED"
    INVESTED_IN = "INVESTED_IN"
    PARTNERS_WITH = "PARTNERS_WITH"
    PROVIDES_SERVICE_FOR = "PROVIDES_SERVICE_FOR"
    RECEIVES_SERVICE_FROM = "RECEIVES_SERVICE_FROM"
    OWES = "OWES"
    HAS_RISK = "HAS_RISK"
    REGULATED_BY = "REGULATED_BY"
    FINANCED_BY = "FINANCED_BY"
    REPORTS_ON = "REPORTS_ON"
    REFERENCES = "REFERENCES"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"


class Edge(BaseModel):
    """Relationship between entities"""
    
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source entity ID")
    target: str = Field(..., description="Target entity ID")
    type: EdgeType = Field(..., description="Relationship type")
    
    # Relationship properties
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Graph metadata
    graph_id: str = Field(..., description="Knowledge graph ID")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "edge_1",
                "source": "ent_1",
                "target": "ent_2",
                "type": "HAS_LOAN",
                "properties": {
                    "amount": 50000000,
                    "rate": 0.0875,
                    "maturity": "2030-01-15"
                },
                "graph_id": "graph_xyz789"
            }
        }


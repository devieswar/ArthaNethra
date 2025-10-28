"""
Risk detection service using rules and LLM reasoning
"""
import uuid
from typing import List, Dict, Any
from loguru import logger

from models.entity import Entity, EntityType
from models.risk import Risk, RiskSeverity
from models.citation import Citation


class RiskDetectionService:
    """Detects financial risks using hybrid approach: rules + LLM"""
    
    def __init__(self):
        self.rules = [
            {
                "name": "high_variable_rate",
                "description": "Variable-rate debt exceeds 8% threshold",
                "entity_type": EntityType.LOAN,
                "property": "rate",
                "threshold": 0.08,
                "severity": RiskSeverity.HIGH,
                "recommendation": "Consider hedging strategies or refinancing to fixed-rate debt"
            },
            {
                "name": "high_debt_ratio",
                "description": "Debt-to-equity ratio exceeds 0.6 threshold",
                "entity_type": EntityType.METRIC,
                "property": "debt_ratio",
                "threshold": 0.6,
                "severity": RiskSeverity.MEDIUM,
                "recommendation": "Consider debt restructuring or equity raising"
            },
            {
                "name": "negative_cash_flow",
                "description": "Negative operating cash flow",
                "entity_type": EntityType.METRIC,
                "property": "cash_flow",
                "threshold": 0.0,
                "severity": RiskSeverity.HIGH,
                "recommendation": "Review operational efficiency and cost structure"
            },
            {
                "name": "approaching_maturity",
                "description": "Debt maturity within 12 months",
                "entity_type": EntityType.LOAN,
                "property": "days_to_maturity",
                "threshold": 365,
                "severity": RiskSeverity.MEDIUM,
                "recommendation": "Prepare refinancing plan or cash reserves"
            }
        ]
    
    async def detect_risks(
        self,
        entities: List[Entity],
        document_id: str,
        graph_id: str
    ) -> List[Risk]:
        """
        Detect risks in entities using rules
        
        Args:
            entities: List of entities to analyze
            document_id: Source document ID
            graph_id: Knowledge graph ID
            
        Returns:
            List of detected risks
        """
        logger.info(f"Running risk detection on {len(entities)} entities")
        
        risks = []
        
        # Apply rule-based detection
        for rule in self.rules:
            rule_risks = await self._apply_rule(
                rule,
                entities,
                document_id,
                graph_id
            )
            risks.extend(rule_risks)
        
        logger.info(f"Detected {len(risks)} risks")
        
        return risks
    
    async def _apply_rule(
        self,
        rule: Dict[str, Any],
        entities: List[Entity],
        document_id: str,
        graph_id: str
    ) -> List[Risk]:
        """Apply a single rule to entities"""
        risks = []
        
        for entity in entities:
            # Check if entity matches rule criteria
            if entity.type != rule["entity_type"]:
                continue
            
            property_name = rule["property"]
            if property_name not in entity.properties:
                continue
            
            actual_value = entity.properties[property_name]
            threshold = rule["threshold"]
            
            # Check threshold
            is_risk = False
            if property_name == "rate" and actual_value > threshold:
                is_risk = True
            elif property_name == "debt_ratio" and actual_value > threshold:
                is_risk = True
            elif property_name == "cash_flow" and actual_value < threshold:
                is_risk = True
            elif property_name == "days_to_maturity" and actual_value < threshold:
                is_risk = True
            
            if is_risk:
                # Calculate risk score
                if property_name in ["rate", "debt_ratio"]:
                    score = min(actual_value / threshold, 1.0)
                elif property_name == "cash_flow":
                    score = min(abs(actual_value) / 1000000, 1.0)
                else:
                    score = min((threshold - actual_value) / threshold, 1.0)
                
                risk = Risk(
                    id=f"risk_{uuid.uuid4().hex[:12]}",
                    type=rule["name"].replace("_", " ").title(),
                    severity=rule["severity"],
                    description=f"{rule['description']} - {entity.name}",
                    affected_entity_ids=[entity.id],
                    citations=entity.citations,
                    score=score,
                    threshold=threshold,
                    actual_value=actual_value,
                    recommendation=rule["recommendation"],
                    document_id=document_id,
                    graph_id=graph_id
                )
                risks.append(risk)
        
        return risks
    
    async def detect_missing_covenants(
        self,
        entities: List[Entity],
        document_id: str,
        graph_id: str
    ) -> List[Risk]:
        """
        Detect missing required clauses/covenants
        
        This would use LLM to analyze document structure
        """
        risks = []
        
        # Check for loan entities without associated clause entities
        loan_entities = [e for e in entities if e.type == EntityType.LOAN]
        clause_entities = [e for e in entities if e.type == EntityType.CLAUSE]
        
        required_clauses = [
            "material adverse change",
            "covenant",
            "default",
            "financial covenant"
        ]
        
        for loan in loan_entities:
            # Simple check: are there any clause entities?
            if not clause_entities:
                risk = Risk(
                    id=f"risk_{uuid.uuid4().hex[:12]}",
                    type="Missing Covenants",
                    severity=RiskSeverity.MEDIUM,
                    description=f"No covenant clauses found for loan: {loan.name}",
                    affected_entity_ids=[loan.id],
                    citations=loan.citations,
                    score=0.7,
                    threshold=1.0,
                    actual_value=0.0,
                    recommendation="Review loan agreement for required covenant clauses",
                    document_id=document_id,
                    graph_id=graph_id
                )
                risks.append(risk)
        
        return risks
    
    def calculate_risk_summary(self, risks: List[Risk]) -> Dict[str, Any]:
        """Calculate risk summary statistics"""
        if not risks:
            return {
                "total_risks": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0,
                "critical_severity": 0
            }
        
        summary = {
            "total_risks": len(risks),
            "high_severity": len([r for r in risks if r.severity == RiskSeverity.HIGH]),
            "medium_severity": len([r for r in risks if r.severity == RiskSeverity.MEDIUM]),
            "low_severity": len([r for r in risks if r.severity == RiskSeverity.LOW]),
            "critical_severity": len([r for r in risks if r.severity == RiskSeverity.CRITICAL])
        }
        
        return summary


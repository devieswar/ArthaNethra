"""
Risk detection service using rules and LLM reasoning
"""
import uuid
import json
from typing import List, Dict, Any
from loguru import logger
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from models.entity import Entity, EntityType
from models.risk import Risk, RiskSeverity
from models.citation import Citation
from config import settings


class RiskDetectionService:
    """Detects financial risks using hybrid approach: rules + LLM"""
    
    def __init__(self):
        self.bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            region_name=settings.AWS_REGION
        )
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
    
    async def detect_llm_anomalies(
        self,
        entities: List[Entity],
        document_id: str,
        graph_id: str
    ) -> List[Risk]:
        """
        Use LLM to detect anomalies and unusual patterns in entities
        
        This complements rule-based detection with semantic understanding
        """
        logger.info(f"Running LLM-based anomaly detection on {len(entities)} entities")
        
        # Prepare entity summary for LLM
        entity_summary = self._prepare_entity_summary(entities)
        
        prompt = f"""Analyze these financial entities and detect potential risks, anomalies, or compliance gaps.

Entity Data:
{entity_summary}

Identify:
1. **Unusual patterns** - Values significantly outside normal ranges
2. **Missing required information** - Expected fields that are absent
3. **Inconsistencies** - Data that doesn't align across entities
4. **Compliance risks** - Potential regulatory or covenant violations
5. **Financial red flags** - Signs of financial distress or mismanagement

For each risk detected, provide:
- type: Brief risk category
- severity: critical/high/medium/low
- description: What the risk is
- affected_entities: List of entity IDs
- score: Risk score 0-1
- recommendation: Suggested action

Return as JSON array of risks. If no risks detected, return empty array []."""

        try:
            # Call Claude via Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=settings.BEDROCK_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "temperature": 0.1,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            llm_output = response_body['content'][0]['text']
            
            # Parse LLM response
            risks = self._parse_llm_risks(
                llm_output,
                entities,
                document_id,
                graph_id
            )
            
            logger.info(f"LLM detected {len(risks)} anomalies")
            return risks
            
        except (BotoCoreError, ClientError) as e:
            logger.error(f"LLM anomaly detection failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error in LLM anomaly detection: {e}")
            return []
    
    def _prepare_entity_summary(self, entities: List[Entity], max_entities: int = 50) -> str:
        """Prepare a concise summary of entities for LLM analysis"""
        summary_lines = []
        
        # Group entities by type
        entities_by_type: Dict[str, List[Entity]] = {}
        for entity in entities:
            type_str = entity.type.value if hasattr(entity.type, 'value') else str(entity.type)
            if type_str not in entities_by_type:
                entities_by_type[type_str] = []
            entities_by_type[type_str].append(entity)
        
        # Summarize each type
        for entity_type, type_entities in entities_by_type.items():
            summary_lines.append(f"\n**{entity_type.upper()} ({len(type_entities)} total):**")
            
            # Show first few entities of each type
            for entity in type_entities[:5]:
                props = ", ".join([f"{k}={v}" for k, v in entity.properties.items() if v is not None][:5])
                summary_lines.append(f"  - ID: {entity.id}, Name: {entity.name}, Properties: {{{props}}}")
            
            if len(type_entities) > 5:
                summary_lines.append(f"  ... and {len(type_entities) - 5} more")
        
        return "\n".join(summary_lines)
    
    def _parse_llm_risks(
        self,
        llm_output: str,
        entities: List[Entity],
        document_id: str,
        graph_id: str
    ) -> List[Risk]:
        """Parse LLM output into Risk objects"""
        risks = []
        
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in llm_output:
                json_start = llm_output.find("```json") + 7
                json_end = llm_output.find("```", json_start)
                json_str = llm_output[json_start:json_end].strip()
            elif "```" in llm_output:
                json_start = llm_output.find("```") + 3
                json_end = llm_output.find("```", json_start)
                json_str = llm_output[json_start:json_end].strip()
            else:
                # Try to find JSON array
                json_start = llm_output.find("[")
                json_end = llm_output.rfind("]") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = llm_output[json_start:json_end]
                else:
                    logger.warning("No JSON found in LLM output")
                    return []
            
            llm_risks = json.loads(json_str)
            
            # Convert to Risk objects
            for llm_risk in llm_risks:
                # Map severity
                severity_str = llm_risk.get("severity", "medium").lower()
                severity = RiskSeverity.MEDIUM
                if severity_str == "critical":
                    severity = RiskSeverity.CRITICAL
                elif severity_str == "high":
                    severity = RiskSeverity.HIGH
                elif severity_str == "low":
                    severity = RiskSeverity.LOW
                
                # Get affected entities
                affected_ids = llm_risk.get("affected_entities", [])
                citations = []
                for entity_id in affected_ids:
                    entity = next((e for e in entities if e.id == entity_id), None)
                    if entity and entity.citations:
                        citations.extend(entity.citations)
                
                risk = Risk(
                    id=f"risk_{uuid.uuid4().hex[:12]}",
                    type=llm_risk.get("type", "LLM Detected Risk"),
                    severity=severity,
                    description=llm_risk.get("description", ""),
                    affected_entity_ids=affected_ids,
                    citations=citations[:3],  # Limit to top 3 citations
                    score=float(llm_risk.get("score", 0.5)),
                    threshold=1.0,
                    actual_value=float(llm_risk.get("score", 0.5)),
                    recommendation=llm_risk.get("recommendation", "Review and investigate"),
                    document_id=document_id,
                    graph_id=graph_id
                )
                risks.append(risk)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM risks JSON: {e}")
            logger.debug(f"LLM output: {llm_output[:500]}")
        except Exception as e:
            logger.error(f"Error parsing LLM risks: {e}")
        
        return risks


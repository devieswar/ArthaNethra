"""
Generic analytics service for financial knowledge graph analysis.

This service provides:
1. Entity-agnostic aggregation and comparison metrics
2. Config-driven metric definitions
3. Support for Location, Company, Loan, Invoice entities
4. Flexible filtering, grouping, and threshold-based analytics
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class EntityRecord:
    """Simplified view of an entity pulled from Neo4j"""

    id: str
    name: str
    type: str
    properties: Dict[str, Any]
    graph_id: Optional[str] = None


@dataclass
class MetricDefinition:
    """Configuration for a reusable analytics metric"""

    name: str
    description: str
    handler: Callable
    entity_types: List[str] = field(default_factory=list)
    default_params: Dict[str, Any] = field(default_factory=dict)


class AnalyticsService:
    """Provides higher-order analytics that combine multiple entity metrics."""

    # Common financial field categories (can be extended)
    FIELD_CATEGORIES = {
        "receivables": (
            "accounts_receivable",
            "accrued_interest_receivable",
            "intergovernmental_receivable",
            "income_tax_receivable",
            "property_taxes_receivable",
            "special_assessments_receivable",
            "revenue_in_lieu_of_taxes_receivable",
            "due_from_other_governments",
            "notes_receivable",
            "loans_receivable",
        ),
        "liabilities": (
            "accounts_payable",
            "accrued_wages_and_benefits",
            "contracts_payable",
            "retainage_payable",
            "intergovernmental_payable",
            "accrued_interest_payable",
            "matured_compensated_absences_payable",
            "claims_payable",
            "due_to_other_governments",
            "unearned_revenue",
            "long_term_liabilities_due_within_one_year",
            "long_term_liabilities_due_in_more_than_one_year",
            "net_pension_liability",
            "net_opeb_liability",
            "total_liabilities",
        ),
        "deferred_inflows": (
            "deferred_inflows_pension_related",
            "deferred_inflows_opeb_related",
            "deferred_inflows_property_taxes",
            "deferred_inflows_special_assessments",
            "deferred_inflows_other_amounts",
            "total_deferred_inflows_of_resources",
        ),
        "assets": (
            "cash_and_cash_equivalents",
            "investments",
            "inventory_held_for_resale",
            "materials_and_supplies_inventory",
            "restricted_assets",
            "nondepreciable_capital_assets",
            "depreciable_capital_assets",
            "total_assets",
        ),
        "debt": (
            "total_debt",
            "long_term_debt",
            "short_term_debt",
            "bonds_payable",
            "notes_payable",
            "loan_principal",
        ),
    }

    def __init__(self, indexing_service):
        self.indexing_service = indexing_service
        self.metrics = self._register_metrics()

    def _register_metrics(self) -> Dict[str, MetricDefinition]:
        """Register all available metrics (extensible registry pattern)"""
        return {
            # Generic comparison metrics
            "property_threshold": MetricDefinition(
                name="property_threshold",
                description="Find entities where a property meets threshold criteria",
                handler=self._metric_property_threshold,
                entity_types=["Location", "Company", "Loan", "Invoice"],
                default_params={"operator": "gt", "threshold": 0},
            ),
            "property_comparison": MetricDefinition(
                name="property_comparison",
                description="Compare two properties within entities",
                handler=self._metric_property_comparison,
                entity_types=["Location", "Company", "Loan", "Invoice"],
                default_params={"comparison_type": "ratio", "threshold": 0.0},
            ),
            "grouped_aggregation": MetricDefinition(
                name="grouped_aggregation",
                description="Group entities by a field and aggregate properties",
                handler=self._metric_grouped_aggregation,
                entity_types=["Location", "Company", "Loan", "Invoice"],
                default_params={"operation": "sum"},
            ),
            "sequential_drop": MetricDefinition(
                name="sequential_drop",
                description="Detect drops between consecutive entities in ordered groups",
                handler=self._metric_sequential_drop,
                entity_types=["Location", "Company"],
                default_params={"drop_threshold": 0.30, "order_by": "total_assets"},
            ),
            # Specific financial health metrics
            "liquidity_analysis": MetricDefinition(
                name="liquidity_analysis",
                description="Analyze cash vs assets for liquidity concerns",
                handler=self._metric_liquidity_analysis,
                entity_types=["Location", "Company"],
                default_params={
                    "asset_threshold": 50_000_000,
                    "cash_threshold": 3_000_000,
                },
            ),
            "debt_risk": MetricDefinition(
                name="debt_risk",
                description="Identify high debt-to-asset ratios",
                handler=self._metric_debt_risk,
                entity_types=["Location", "Company"],
                default_params={"debt_ratio_threshold": 0.70},
            ),
            "loan_maturity": MetricDefinition(
                name="loan_maturity",
                description="Find loans approaching maturity with high balances",
                handler=self._metric_loan_maturity,
                entity_types=["Loan"],
                default_params={"months_threshold": 12, "balance_threshold": 1_000_000},
            ),
        }

    def list_metrics(self) -> List[Dict[str, Any]]:
        """Return list of available metrics for discovery"""
        return [
            {
                "name": m.name,
                "description": m.description,
                "entity_types": m.entity_types,
                "default_params": m.default_params,
            }
            for m in self.metrics.values()
        ]

    def compute_metric(
        self,
        metric_name: str,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Dispatch analytics computation by metric name."""

        if not metric_name:
            return {"error": "metric_name is required"}

        params = params or {}
        context = context or {}

        # Check if metric exists
        metric_def = self.metrics.get(metric_name)
        if not metric_def:
            return {
                "metric_name": metric_name,
                "error": f"Unsupported metric '{metric_name}'. Available: {list(self.metrics.keys())}",
                "available_metrics": list(self.metrics.keys()),
            }

        # Check Neo4j availability
        if not getattr(self.indexing_service, "neo4j_driver", None):
            return {
                "metric_name": metric_name,
                "error": "Neo4j not available for analytics",
            }

        # Merge default params with provided params
        merged_params = {**metric_def.default_params, **params}

        try:
            return metric_def.handler(merged_params, context)
        except Exception as e:
            logger.error(f"Error computing metric '{metric_name}': {e}", exc_info=True)
            return {
                "metric_name": metric_name,
                "error": f"Computation failed: {str(e)}",
            }

    # ------------------------------------------------------------------
    # Generic metric implementations
    # ------------------------------------------------------------------

    def _metric_property_threshold(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Find entities where a property meets threshold criteria."""

        entity_type = params.get("entity_type", "Location")
        property_name = params.get("property_name")
        threshold = float(params.get("threshold", 0))
        operator = params.get("operator", "gt")  # gt, lt, gte, lte, eq
        limit = int(params.get("limit", 100))
        graph_id = params.get("graph_id") or context.get("graph_id")

        if not property_name:
            return {"error": "property_name is required"}

        entities = self._fetch_entities_by_type(
            entity_type, graph_id=graph_id, limit=limit
        )
        logger.info(
            f"Analytics: loaded {len(entities)} {entity_type} for threshold analysis"
        )

        if not entities:
            return {
                "metric_name": "property_threshold",
                "entity_type": entity_type,
                "property_name": property_name,
                "operator": operator,
                "threshold": threshold,
                "results": [],
                "count": 0,
                "message": f"No {entity_type} entities found. Please upload and index documents first.",
            }

        matches = []
        for entity in entities:
            value = self._to_float(entity.properties.get(property_name))
            if value is None:
                continue

            match = False
            if operator == "gt":
                match = value > threshold
            elif operator == "lt":
                match = value < threshold
            elif operator == "gte":
                match = value >= threshold
            elif operator == "lte":
                match = value <= threshold
            elif operator == "eq":
                match = value == threshold

            if match:
                matches.append(
                    {
                        "id": entity.id,
                        "name": entity.name,
                        "type": entity.type,
                        property_name: value,
                        "properties": entity.properties,
                    }
                )

        return {
            "metric_name": "property_threshold",
            "entity_type": entity_type,
            "property_name": property_name,
            "operator": operator,
            "threshold": threshold,
            "results": matches,
            "count": len(matches),
        }

    def _metric_property_comparison(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compare two properties within entities (ratio, difference, percentage)."""

        entity_type = params.get("entity_type", "Location")
        property_a = params.get("property_a")
        property_b = params.get("property_b")
        comparison_type = params.get("comparison_type", "ratio")  # ratio, diff, pct
        threshold = float(params.get("threshold", 0.0))
        operator = params.get("operator", "gt")
        limit = int(params.get("limit", 100))
        graph_id = params.get("graph_id") or context.get("graph_id")

        if not property_a or not property_b:
            return {"error": "property_a and property_b are required"}

        entities = self._fetch_entities_by_type(
            entity_type, graph_id=graph_id, limit=limit
        )

        matches = []
        for entity in entities:
            val_a = self._to_float(entity.properties.get(property_a))
            val_b = self._to_float(entity.properties.get(property_b))

            if val_a is None or val_b is None:
                continue

            if comparison_type == "ratio" and val_b != 0:
                result = val_a / val_b
            elif comparison_type == "diff":
                result = val_a - val_b
            elif comparison_type == "pct" and val_b != 0:
                result = ((val_a - val_b) / val_b) * 100
            else:
                continue

            match = False
            if operator == "gt":
                match = result > threshold
            elif operator == "lt":
                match = result < threshold
            elif operator == "gte":
                match = result >= threshold
            elif operator == "lte":
                match = result <= threshold

            if match:
                matches.append(
                    {
                        "id": entity.id,
                        "name": entity.name,
                        property_a: val_a,
                        property_b: val_b,
                        "comparison_result": result,
                        "properties": entity.properties,
                    }
                )

        return {
            "metric_name": "property_comparison",
            "entity_type": entity_type,
            "comparison": f"{property_a} {comparison_type} {property_b}",
            "threshold": threshold,
            "results": matches,
            "count": len(matches),
        }

    def _metric_grouped_aggregation(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Group entities by a field and aggregate properties."""

        entity_type = params.get("entity_type", "Location")
        group_by = params.get("group_by", "county")
        aggregate_property = params.get("aggregate_property", "total_assets")
        operation = params.get("operation", "sum")  # sum, avg, max, min, count
        limit = int(params.get("limit", 1000))
        graph_id = params.get("graph_id") or context.get("graph_id")

        entities = self._fetch_entities_by_type(
            entity_type, graph_id=graph_id, limit=limit
        )

        groups: Dict[str, List[EntityRecord]] = {}
        for entity in entities:
            group_val = entity.properties.get(group_by)
            if not group_val:
                continue
            groups.setdefault(str(group_val), []).append(entity)

        results = []
        for group_name, group_entities in groups.items():
            values = [
                self._to_float(e.properties.get(aggregate_property))
                for e in group_entities
            ]
            values = [v for v in values if v is not None]

            if not values:
                continue

            if operation == "sum":
                agg_value = sum(values)
            elif operation == "avg":
                agg_value = sum(values) / len(values)
            elif operation == "max":
                agg_value = max(values)
            elif operation == "min":
                agg_value = min(values)
            elif operation == "count":
                agg_value = len(values)
            else:
                agg_value = sum(values)

            results.append(
                {
                    "group": group_name,
                    "count": len(group_entities),
                    "aggregate_value": agg_value,
                    "entities": [
                        {"id": e.id, "name": e.name} for e in group_entities
                    ],
                }
            )

        # Sort by aggregate value
        results.sort(key=lambda x: x["aggregate_value"], reverse=True)

        return {
            "metric_name": "grouped_aggregation",
            "entity_type": entity_type,
            "group_by": group_by,
            "aggregate_property": aggregate_property,
            "operation": operation,
            "results": results,
            "count": len(results),
        }

    def _metric_sequential_drop(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Detect drops between consecutive entities in ordered groups."""

        entity_type = params.get("entity_type", "Location")
        group_by = params.get("group_by", "county")
        order_by = params.get("order_by", "total_assets")
        drop_threshold = float(params.get("drop_threshold", 0.30))
        limit = int(params.get("limit", 1000))
        graph_id = params.get("graph_id") or context.get("graph_id")

        entities = self._fetch_entities_by_type(
            entity_type, graph_id=graph_id, limit=limit
        )
        logger.info(
            f"Analytics: loaded {len(entities)} {entity_type} for sequential drop analysis"
        )

        # Return early if no data
        if not entities:
            return {
                "metric_name": "sequential_drop",
                "entity_type": entity_type,
                "group_by": group_by,
                "order_by": order_by,
                "drop_threshold": drop_threshold,
                "results": [],
                "count": 0,
                "message": f"No {entity_type} entities found in knowledge graph. Please upload and index documents first.",
                "graph_id": graph_id,
            }

        groups: Dict[str, List[EntityRecord]] = {}
        for entity in entities:
            group_val = entity.properties.get(group_by)
            if not group_val:
                continue
            groups.setdefault(str(group_val), []).append(entity)

        results = []

        for group_name, group_entities in groups.items():
            enriched = [
                {
                    "id": e.id,
                    "name": e.name,
                    order_by: self._to_float(e.properties.get(order_by)),
                    "properties": e.properties,
                }
                for e in group_entities
            ]

            enriched = [e for e in enriched if e[order_by] is not None]
            if len(enriched) < 2:
                continue

            enriched.sort(key=lambda x: x[order_by], reverse=True)

            drops = []
            for idx in range(len(enriched) - 1):
                first = enriched[idx]
                second = enriched[idx + 1]
                if not first[order_by]:
                    continue
                drop = first[order_by] - (second[order_by] or 0.0)
                if drop <= 0:
                    continue
                drop_ratio = drop / first[order_by]
                if drop_ratio >= drop_threshold:
                    drops.append(
                        {
                            "from_entity": first["name"],
                            "to_entity": second["name"],
                            "from_value": first[order_by],
                            "to_value": second[order_by],
                            "drop_amount": drop,
                            "drop_ratio": drop_ratio,
                        }
                    )

            if drops:
                # Include additional context
                additional_fields = self._collect_field_summary(
                    enriched, order_by, ["receivables", "liabilities"]
                )
                results.append(
                    {
                        "group": group_name,
                        "ordered_entities": enriched,
                        "drops": drops,
                        "additional_context": additional_fields,
                    }
                )

        return {
            "metric_name": "sequential_drop",
            "entity_type": entity_type,
            "group_by": group_by,
            "order_by": order_by,
            "drop_threshold": drop_threshold,
            "results": results,
            "count": len(results),
        }

    # ------------------------------------------------------------------
    # Specific financial health metrics
    # ------------------------------------------------------------------

    def _metric_liquidity_analysis(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze cash vs assets for liquidity concerns (asset rich, cash poor)."""

        entity_type = params.get("entity_type", "Location")
        asset_threshold = float(params.get("asset_threshold", 50_000_000))
        cash_threshold = float(params.get("cash_threshold", 3_000_000))
        graph_id = params.get("graph_id") or context.get("graph_id")

        entities = self._fetch_entities_by_type(
            entity_type, graph_id=graph_id, limit=1000
        )
        logger.info(
            f"Analytics: loaded {len(entities)} {entity_type} for liquidity analysis"
        )

        matches = []
        for entity in entities:
            props = entity.properties or {}
            total_assets = self._to_float(props.get("total_assets"))
            cash = self._to_float(
                props.get("cash_and_cash_equivalents") or props.get("cash")
            )

            if total_assets is None or cash is None:
                continue
            if total_assets <= asset_threshold or cash >= cash_threshold:
                continue

            liquidity_ratio = cash / total_assets if total_assets else 0

            liabilities = self._collect_nonzero_fields(
                props, self.FIELD_CATEGORIES.get("liabilities", ())
            )
            deferred = self._collect_nonzero_fields(
                props, self.FIELD_CATEGORIES.get("deferred_inflows", ())
            )

            matches.append(
                {
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.type,
                    "total_assets": total_assets,
                    "cash": cash,
                    "liquidity_ratio": liquidity_ratio,
                    "long_term_liabilities": liabilities,
                    "deferred_inflows": deferred,
                    "risk_level": "high" if liquidity_ratio < 0.02 else "medium",
                }
            )

        matches.sort(key=lambda x: x["total_assets"], reverse=True)

        return {
            "metric_name": "liquidity_analysis",
            "entity_type": entity_type,
            "asset_threshold": asset_threshold,
            "cash_threshold": cash_threshold,
            "results": matches,
            "count": len(matches),
        }

    def _metric_debt_risk(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Identify high debt-to-asset ratios."""

        entity_type = params.get("entity_type", "Location")
        debt_ratio_threshold = float(params.get("debt_ratio_threshold", 0.70))
        graph_id = params.get("graph_id") or context.get("graph_id")

        entities = self._fetch_entities_by_type(
            entity_type, graph_id=graph_id, limit=1000
        )

        matches = []
        for entity in entities:
            props = entity.properties or {}
            total_assets = self._to_float(props.get("total_assets"))
            total_liabilities = self._to_float(props.get("total_liabilities"))

            if total_assets is None or total_liabilities is None:
                continue
            if total_assets == 0:
                continue

            debt_ratio = total_liabilities / total_assets

            if debt_ratio >= debt_ratio_threshold:
                matches.append(
                    {
                        "id": entity.id,
                        "name": entity.name,
                        "type": entity.type,
                        "total_assets": total_assets,
                        "total_liabilities": total_liabilities,
                        "debt_ratio": debt_ratio,
                        "risk_level": "critical" if debt_ratio > 0.90 else "high",
                    }
                )

        matches.sort(key=lambda x: x["debt_ratio"], reverse=True)

        return {
            "metric_name": "debt_risk",
            "entity_type": entity_type,
            "debt_ratio_threshold": debt_ratio_threshold,
            "results": matches,
            "count": len(matches),
        }

    def _metric_loan_maturity(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Find loans approaching maturity with high balances."""

        months_threshold = int(params.get("months_threshold", 12))
        balance_threshold = float(params.get("balance_threshold", 1_000_000))
        graph_id = params.get("graph_id") or context.get("graph_id")

        loans = self._fetch_entities_by_type("Loan", graph_id=graph_id, limit=1000)

        matches = []
        for loan in loans:
            props = loan.properties or {}
            balance = self._to_float(
                props.get("principal_balance")
                or props.get("outstanding_balance")
                or props.get("balance")
            )
            maturity_months = self._to_float(props.get("maturity_months"))

            if balance is None or maturity_months is None:
                continue

            if balance >= balance_threshold and maturity_months <= months_threshold:
                matches.append(
                    {
                        "id": loan.id,
                        "name": loan.name,
                        "balance": balance,
                        "maturity_months": maturity_months,
                        "interest_rate": self._to_float(props.get("interest_rate")),
                        "borrower": props.get("borrower"),
                        "lender": props.get("lender"),
                    }
                )

        matches.sort(key=lambda x: (x["maturity_months"], -x["balance"]))

        return {
            "metric_name": "loan_maturity",
            "months_threshold": months_threshold,
            "balance_threshold": balance_threshold,
            "results": matches,
            "count": len(matches),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch_entities_by_type(
        self,
        entity_type: str,
        graph_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[EntityRecord]:
        """Fetch entities from Neo4j by type"""
        driver = getattr(self.indexing_service, "neo4j_driver", None)
        if not driver:
            logger.warning("Neo4j driver not available for entity fetch")
            return []

        # Try with graph_id first, fallback to all if none found
        cypher_with_graph = (
            "MATCH (e:Entity) "
            "WHERE e.type = $entity_type "
            "AND e.graphId = $graph_id "
            "RETURN e.entityId AS id, e.name AS name, e.type AS type, "
            "e.properties AS properties, e.graphId AS graphId "
            "LIMIT $limit"
        )
        
        cypher_all = (
            "MATCH (e:Entity) "
            "WHERE e.type = $entity_type "
            "RETURN e.entityId AS id, e.name AS name, e.type AS type, "
            "e.properties AS properties, e.graphId AS graphId "
            "LIMIT $limit"
        )

        logger.info(f"Fetching entities: type={entity_type}, graph_id={graph_id}, limit={limit}")

        with driver.session() as session:
            # Try with graph_id filter first if provided
            if graph_id:
                result = session.run(
                    cypher_with_graph,
                    entity_type=entity_type,
                    graph_id=graph_id,
                    limit=max(limit, 1),
                )
                entities_raw = list(result)
                
                # If no results with graph_id, try without filter
                if not entities_raw:
                    logger.warning(f"No entities found with graph_id={graph_id}, trying without filter...")
                    result = session.run(
                        cypher_all,
                        entity_type=entity_type,
                        limit=max(limit, 1),
                    )
                    entities_raw = list(result)
            else:
                # No graph_id provided, query all
                result = session.run(
                    cypher_all,
                    entity_type=entity_type,
                    limit=max(limit, 1),
                )
                entities_raw = list(result)

            entities: List[EntityRecord] = []
            for record in entities_raw:
                props_raw = record.get("properties")
                props: Dict[str, Any]
                if isinstance(props_raw, str):
                    try:
                        props = json.loads(props_raw)
                    except json.JSONDecodeError:
                        props = {}
                elif isinstance(props_raw, dict):
                    props = props_raw
                else:
                    props = {}

                entities.append(
                    EntityRecord(
                        id=record.get("id"),
                        name=record.get("name"),
                        type=record.get("type"),
                        properties=props,
                        graph_id=record.get("graphId"),
                    )
                )

        logger.info(f"Fetched {len(entities)} entities of type {entity_type}")
        return entities

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        """Safe conversion to float"""
        if value is None or value == "" or value == "null":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _collect_nonzero_fields(
        self,
        properties: Dict[str, Any],
        fields: Tuple[str, ...],
    ) -> Dict[str, float]:
        """Collect non-zero values for specified fields"""
        collected: Dict[str, float] = {}
        for field in fields:
            value = self._to_float(properties.get(field))
            if value is None or value == 0:
                continue
            collected[field] = value
        return collected

    def _collect_field_summary(
        self,
        entities: List[Dict[str, Any]],
        exclude_field: str,
        categories: List[str],
    ) -> Dict[str, Any]:
        """Collect summary of additional fields from entity properties"""
        summary = {}
        for category in categories:
            fields = self.FIELD_CATEGORIES.get(category, ())
            category_data = {}
            for entity in entities:
                props = entity.get("properties", {})
                for field in fields:
                    if field == exclude_field:
                        continue
                    value = self._to_float(props.get(field))
                    if value:
                        category_data.setdefault(field, []).append(value)
            if category_data:
                summary[category] = {
                    k: {"sum": sum(v), "avg": sum(v) / len(v), "count": len(v)}
                    for k, v in category_data.items()
                }
        return summary

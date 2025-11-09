"""
Graph normalization service - converts ADE output to graph entities and edges
"""
import uuid
import json
from typing import Dict, Any, List, Tuple
from loguru import logger

from models.entity import Entity, EntityType
from models.edge import Edge, EdgeType
from models.citation import Citation
from services.relationship_detector import RelationshipDetector
from services.markdown_parser import MarkdownTableParser
from services.document_type_detector import DocumentTypeDetector
from services.invoice_parser import InvoiceParser
from services.contract_parser import ContractParser
from services.loan_parser import LoanParser
from services.narrative_parser import NarrativeParser


class NormalizationService:
    """Converts ADE extraction results to knowledge graph entities and relationships"""
    
    def __init__(self):
        self.entity_type_mapping = {
            "ORGANIZATION": EntityType.COMPANY,
            "COMPANY": EntityType.COMPANY,
            "SUBSIDIARY": EntityType.SUBSIDIARY,
            "LOAN": EntityType.LOAN,
            "DEBT": EntityType.LOAN,
            "INVOICE": EntityType.INVOICE,
            "METRIC": EntityType.METRIC,
            "FINANCIAL_METRIC": EntityType.METRIC,
            "CONTRACT": EntityType.CLAUSE,
            "CLAUSE": EntityType.CLAUSE,
            "PERSON": EntityType.PERSON,
            "LOCATION": EntityType.LOCATION,
            "VENDOR": EntityType.VENDOR,
            "OTHER": EntityType.CLAUSE  # Generic fallback
        }
        self.relationship_detector = RelationshipDetector()
        self.markdown_parser = MarkdownTableParser()
        self.doc_type_detector = DocumentTypeDetector()
        self.invoice_parser = InvoiceParser()
        self.contract_parser = ContractParser()
        self.loan_parser = LoanParser()
        self.narrative_parser = NarrativeParser()
    
    async def normalize_to_graph(
        self,
        ade_output: Dict[str, Any],
        document_id: str
    ) -> Tuple[List[Entity], List[Edge]]:
        """
        Convert ADE output to graph entities and edges
        
        Args:
            ade_output: Parsed ADE extraction results
            document_id: Source document ID
            
        Returns:
            Tuple of (entities, edges)
        """
        logger.info(f"Normalizing ADE output for document: {document_id}")
        
        graph_id = f"graph_{uuid.uuid4().hex[:12]}"
        
        # Create entities
        entities = await self._create_entities(
            ade_output,
            document_id,
            graph_id
        )
        
        # Special handling for narrative documents
        # If we got entities from narrative parser, also extract relationships from chunks
        narrative_edges = []
        # Try multiple locations for markdown (different ADE output formats)
        markdown = ade_output.get("markdown") or ade_output.get("metadata", {}).get("markdown", "")
        
        if entities and markdown:
            # Check if entities came from narrative parser AND already have relationships
            has_narrative_entities = any(
                e.properties.get("extracted_from") in ["narrative_text", "narrative_paragraph", "narrative_llm"] 
                for e in entities
            )
            
            # Check if relationships were already extracted (attached to entities)
            if has_narrative_entities and hasattr(entities[0], '_narrative_relationships'):
                logger.info("Using relationships already extracted with narrative entities (no re-extraction needed)")
                narrative_edges = entities[0]._narrative_relationships
            elif has_narrative_entities:
                logger.info("Detected narrative document - extracting relationships from text chunks")
                try:
                    # Extract relationships directly from narrative chunks
                    _, narrative_edges = await self.narrative_parser.extract_entities_and_relationships_from_chunks(
                        markdown, document_id, graph_id
                    )
                    logger.info(f"Narrative parser extracted {len(narrative_edges)} relationships from text")
                except Exception as e:
                    logger.warning(f"Narrative relationship extraction failed: {e}")
        
        # Create relationships using standard method
        # Skip LLM-based relationship detection for narrative entities (already have context-based relationships)
        has_narrative_entities = any(
            e.properties.get("extracted_from") in ["narrative_text", "narrative_paragraph", "narrative_llm"] 
            for e in entities
        )
        
        edges = await self._create_edges(
            entities,
            ade_output,
            graph_id,
            skip_llm_detection=has_narrative_entities,  # Skip redundant LLM analysis
            existing_narrative_edges=narrative_edges  # Pass narrative edges to avoid duplicates
        )
        
        # Combine with narrative edges
        if narrative_edges:
            edges.extend(narrative_edges)
            # Deduplicate
            seen = set()
            unique_edges = []
            for edge in edges:
                key = (edge.source, edge.target, edge.type)
                if key not in seen:
                    seen.add(key)
                    unique_edges.append(edge)
            edges = unique_edges
            logger.info(f"Combined edges: {len(edges)} total (including {len(narrative_edges)} from narrative)")
        
        logger.info(
            f"Normalized graph: {len(entities)} entities, {len(edges)} edges"
        )
        
        return entities, edges
    
    async def _create_entities(
        self,
        ade_output: Dict[str, Any],
        document_id: str,
        graph_id: str
    ) -> List[Entity]:
        """
        Create entities using ADE new model FIRST, then deterministic parser as fallback
        
        Strategy:
        1. PRIMARY: Try ADE schema extraction with new model (extract-20251024)
        2. FALLBACK: Use deterministic parser if ADE fails or yields too few entities
        """
        entities = []
        # Try multiple locations for markdown (different ADE output formats)
        markdown = ade_output.get("markdown") or ade_output.get("metadata", {}).get("markdown", "")
        logger.info(f"DEBUG ade_output keys: {list(ade_output.keys())}")
        if "metadata" in ade_output:
            logger.info(f"DEBUG metadata keys: {list(ade_output['metadata'].keys())}")
        
        # STEP 1: Try ADE schema extraction FIRST (with new model)
        logger.info("PRIMARY EXTRACTION: Trying ADE with new model (extract-20251024)")
        
        ade_entities = await self._extract_entities_from_ade_schema(
            ade_output,
            document_id,
            graph_id
        )
        
        logger.info(f"ADE extracted {len(ade_entities)} entities")
        
        # Always compute deterministic parser entities for enrichment
        deterministic_entities = await self._extract_entities_from_tables(
            ade_output,
            document_id,
            graph_id
        )
        deterministic_map = {}
        for det_entity in deterministic_entities:
            key = det_entity.properties.get("city") if det_entity.properties else None
            if key:
                deterministic_map[str(key)] = det_entity
            deterministic_map.setdefault(det_entity.name, det_entity)
        
        # Derive counties from markdown as a last resort
        county_lookup: Dict[str, str] = {}
        if markdown:
            try:
                import re
                # Simple regex to capture city and county from HTML table rows
                rows = re.findall(
                    r"<tr>(.*?)</tr>",
                    markdown,
                    flags=re.DOTALL | re.IGNORECASE
                )
                for row_html in rows[2:]:  # skip header rows
                    cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.DOTALL | re.IGNORECASE)
                    if len(cells) < 2:
                        continue
                    city_text = re.sub(r"<.*?>", "", cells[0]).strip()
                    county_text = re.sub(r"<.*?>", "", cells[1]).strip()
                    if city_text and county_text and county_text.lower() not in {"", "county"}:
                        county_lookup[city_text] = county_text
                if county_lookup:
                    logger.debug(f"Derived counties for {len(county_lookup)} cities from markdown")
            except Exception as e:
                logger.warning(f"Failed to derive counties from markdown: {e}")
        
        def merge_with_deterministic(entities_to_merge: List[Entity]) -> List[Entity]:
            """Merge deterministic properties (like county/column) into ADE entities."""
            for entity in entities_to_merge:
                city_name = entity.properties.get("city") if entity.properties else None
                if city_name:
                    entity.name = str(city_name)
                det_entity = deterministic_map.get(entity.name) or (deterministic_map.get(str(city_name)) if city_name else None)
                det_props = det_entity.properties or {} if det_entity else {}
                
                # If county missing/null, pull from deterministic data or markdown
                # Try multiple sources: det_props["county"], det_props["column"], markdown lookup
                if not entity.properties.get("county"):
                    county_value = det_props.get("county") or det_props.get("column")
                    if county_value:
                        entity.properties["county"] = county_value
                        logger.debug(f"Merged county '{county_value}' for {entity.name}")
                    elif city_name:
                        county_from_md = county_lookup.get(str(city_name))
                        if county_from_md:
                            entity.properties["county"] = county_from_md
                            logger.debug(f"Merged county '{county_from_md}' from markdown for {entity.name}")
                
                # Merge other deterministic properties if not already present
                for key, value in det_props.items():
                    if key in ["column"]:  # column already used as county
                        continue
                    if key not in entity.properties or entity.properties[key] is None:
                        entity.properties[key] = value
            return entities_to_merge
        
        # Check if ADE extraction was successful
        if len(ade_entities) >= 20:  # Good extraction threshold
            logger.info(f"Using ADE extraction: {len(ade_entities)} entities (good quality)")
            return merge_with_deterministic(ade_entities)
        
        # STEP 2: Fallback to deterministic parser
        logger.warning(f"ADE only extracted {len(ade_entities)} entities, falling back to deterministic parser")
        logger.info("FALLBACK: Using deterministic parser")
        
        # Detect document type
        if markdown:
            doc_type_info = self.doc_type_detector.detect_document_type(markdown)
            doc_type = doc_type_info["type"]
            logger.info(f"Document type: {doc_type} (confidence: {doc_type_info['confidence']:.2f})")
            
            # Use specialized parser based on document type
            if doc_type == "invoice":
                entities = self.invoice_parser.extract_entities_from_invoice(
                    markdown, document_id, graph_id
                )
            elif doc_type == "contract":
                entities = self.contract_parser.extract_entities_from_contract(
                    markdown, document_id, graph_id
                )
            elif doc_type == "loan_document":
                entities = self.loan_parser.extract_entities_from_loan(
                    markdown, document_id, graph_id
                )
            else:
                # Default to table parser for financial statements and generic docs
                entities = await self._extract_entities_from_tables(
                    ade_output,
                    document_id,
                    graph_id
                )
        else:
            # No markdown, try table parser
            entities = await self._extract_entities_from_tables(
                ade_output,
                document_id,
                graph_id
            )
        
        logger.info(f"Deterministic parser extracted {len(entities)} entities")
        
        # STEP 3: If both ADE and deterministic gave very few entities, try narrative parser
        # Threshold: < 5 entities suggests a narrative document rather than structured data
        total_entities = max(len(entities), len(ade_entities))
        logger.info(f"DEBUG: entities={len(entities)}, ade_entities={len(ade_entities)}, markdown={len(markdown) if markdown else 0} chars")
        if total_entities < 5 and len(markdown) > 10000:  # Long narrative document with few structured entities
            logger.warning(f"Only {total_entities} entities found from structured extraction, but document has {len(markdown)} chars")
            logger.info("NARRATIVE DOCUMENT DETECTED: Using LLM-based narrative parser")
            
            # Use the advanced LLM-based extraction (extracts entities + relationships)
            # Store relationships too so we don't have to extract twice
            try:
                narrative_entities, narrative_relationships = await self.narrative_parser.extract_entities_and_relationships_from_chunks(
                    markdown, document_id, graph_id
                )
                logger.info(f"Narrative parser (LLM) extracted {len(narrative_entities)} entities and {len(narrative_relationships)} relationships")
            except Exception as e:
                logger.warning(f"LLM narrative parser failed: {e}, trying regex fallback")
                # Fallback to regex-based extraction
                narrative_entities = self.narrative_parser.extract_entities_from_narrative(
                    markdown, document_id, graph_id
                )
                logger.info(f"Narrative parser (regex) extracted {len(narrative_entities)} entities")
            
            if len(narrative_entities) > 0:
                logger.info(f"Using narrative parser: {len(narrative_entities)} entities")
                # Store narrative relationships to use later (avoid re-extraction)
                merged_entities = merge_with_deterministic(narrative_entities)
                # Attach the relationships as a temporary attribute
                for entity in merged_entities:
                    if not hasattr(entity, '_narrative_relationships'):
                        entity._narrative_relationships = narrative_relationships
                return merged_entities
        
        # Use whichever gave us more entities
        if len(entities) > len(ade_entities):
            logger.info(f"Using deterministic parser: {len(entities)} entities (better than ADE's {len(ade_entities)})")
            return merge_with_deterministic(entities)
        else:
            logger.info(f"Using ADE extraction: {len(ade_entities)} entities (better than deterministic's {len(entities)})")
            return merge_with_deterministic(ade_entities)
    
    async def _extract_entities_from_ade_schema(
        self,
        ade_output: Dict[str, Any],
        document_id: str,
        graph_id: str
    ) -> List[Entity]:
        """Extract entities using ADE's schema-based extraction"""
        entities = []
        entity_map = {}
        
        # Process extracted entities
        for entity_data in ade_output.get("entities", []):
            entity_type = self._map_entity_type(entity_data.get("type"))
            
            if not entity_type:
                continue
            
            # Create citations
            citations = [
                Citation(**citation_data)
                for citation_data in entity_data.get("citations", [])
            ]
            
            # Create entity
            entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=entity_type,
                name=entity_data.get("name"),
                properties=entity_data.get("properties", {}),
                citations=citations,
                document_id=document_id,
                graph_id=graph_id
            )
            
            entities.append(entity)
            entity_map[entity.name] = entity
        
        # Extract entities from key_values (schema-based extraction results)
        kv_entities, kv_entity_map = await self._extract_entities_from_key_values(
            ade_output,
            document_id,
            graph_id
        )
        entities.extend(kv_entities)
        entity_map.update(kv_entity_map)
        
        # Extract entities from tables
        for table in ade_output.get("tables", []):
            table_entities = await self._extract_entities_from_table(
                table,
                document_id,
                graph_id
            )
            entities.extend(table_entities)
        
        # Last resort: if no entities and we have key_values (e.g., only a summary),
        # create a summary entity and basic metric entities extracted from text.
        if not entities:
            kvs = ade_output.get("key_values", []) or []
            summary_text = None
            for kv in kvs:
                if isinstance(kv, dict) and kv.get("key") == "summary" and isinstance(kv.get("value"), str):
                    summary_text = kv.get("value").strip()
                    break
            if summary_text:
                # Summary entity
                summary_entity = Entity(
                    id=f"ent_{uuid.uuid4().hex[:12]}",
                    type=EntityType.CLAUSE,
                    name="Document Summary",
                    properties={"text": summary_text},
                    citations=[],
                    document_id=document_id,
                    graph_id=graph_id
                )
                entities.append(summary_entity)
                # Basic metrics from text (percentages, currency amounts)
                metrics = self._extract_metrics_from_text(summary_text)
                for metric in metrics:
                    metric_entity = Entity(
                        id=f"ent_{uuid.uuid4().hex[:12]}",
                        type=EntityType.METRIC,
                        name=metric["name"],
                        properties={"value": metric["value"], "unit": metric.get("unit")},
                        citations=[],
                        document_id=document_id,
                        graph_id=graph_id
                    )
                    entities.append(metric_entity)
                # Map for potential edges
                entity_map[summary_entity.name] = summary_entity
        
        return entities
    
    async def _create_edges(
        self,
        entities: List[Entity],
        ade_output: Dict[str, Any],
        graph_id: str,
        skip_llm_detection: bool = False,
        existing_narrative_edges: List[Edge] = None
    ) -> List[Edge]:
        """Create edges (relationships) between entities using LLM + heuristics"""
        
        if not entities:
            return []
        
        logger.info(f"Creating relationships for {len(entities)} entities...")
        
        # Strategy 1: LLM-based relationship detection (intelligent, adaptive)
        # Skip for narrative documents (already have context-based relationships)
        llm_edges = []
        if skip_llm_detection:
            logger.info("⏩ Skipping LLM relationship detection (narrative entities already have context-based relationships)")
        else:
            # Use Claude to analyze entities and discover semantic relationships
            try:
                llm_edges = await self.relationship_detector.detect_relationships_chunked(
                    entities=entities,
                    graph_id=graph_id,
                    chunk_size=20  # Process 20 entities at a time
                )
                logger.info(f"LLM detected {len(llm_edges)} relationships")
            except Exception as e:
                logger.warning(f"LLM relationship detection failed: {e}, using fallback")
                llm_edges = []
        
        # Strategy 2: Enhance with heuristics (supplement obvious patterns)
        # Add rule-based edges that don't need LLM reasoning
        if existing_narrative_edges is None:
            existing_narrative_edges = []
        
        all_edges = await self.relationship_detector.enhance_with_heuristics(
            llm_edges=llm_edges,
            entities=entities,
            graph_id=graph_id,
            existing_narrative_edges=existing_narrative_edges  # Pass separately to avoid duplicates
        )
        
        logger.info(f"Total relationships: {len(all_edges)}")
        return all_edges
    
    async def _create_property_based_edges(
        self,
        entities: List[Entity],
        entity_lookup: Dict[str, Entity],
        graph_id: str
    ) -> List[Edge]:
        """Create edges based on entity properties (most accurate)"""
        edges = []
        
        for entity in entities:
            # Loan entities: Link lender to loan, and main company to loan
            if entity.type == EntityType.LOAN:
                lender_name = entity.properties.get("lender")
                
                # Create lender --[ISSUED_BY]--> loan edge
                if lender_name and lender_name in entity_lookup:
                    lender = entity_lookup[lender_name]
                    edge = Edge(
                        id=f"edge_{uuid.uuid4().hex[:12]}",
                        source=lender.id,
                        target=entity.id,
                        type=EdgeType.ISSUED_BY,
                        graph_id=graph_id,
                        properties={}
                    )
                    edges.append(edge)
                
                # Find main company (first company that's not a lender)
                main_company = None
                for other in entity_lookup.values():
                    if other.type == EntityType.COMPANY and other.name != lender_name:
                        main_company = other
                        break
                
                # Create main company --[HAS_LOAN]--> loan edge
                if main_company:
                    edge = Edge(
                        id=f"edge_{uuid.uuid4().hex[:12]}",
                        source=main_company.id,
                        target=entity.id,
                        type=EdgeType.HAS_LOAN,
                        graph_id=graph_id,
                        properties=entity.properties
                    )
                    edges.append(edge)
        
        return edges
    
    async def _create_heuristic_edges(
        self,
        entities: List[Entity],
        entity_lookup: Dict[str, Entity],
        graph_id: str
    ) -> List[Edge]:
        """Create edges using heuristics (fallback for relationships without explicit properties)"""
        edges = []
        
        # Find main company (first company entity, excluding lenders)
        companies = [e for e in entities if e.type == EntityType.COMPANY]
        main_company = companies[0] if companies else None
        
        if not main_company:
            return edges
        
        # Link all subsidiaries to main company
        for entity in entities:
            if entity.type == EntityType.SUBSIDIARY and entity.id != main_company.id:
                edge = Edge(
                    id=f"edge_{uuid.uuid4().hex[:12]}",
                    source=main_company.id,
                    target=entity.id,
                    type=EdgeType.OWNS,
                    graph_id=graph_id,
                    properties={}
                )
                edges.append(edge)
        
        # Link all metrics to main company
        for entity in entities:
            if entity.type == EntityType.METRIC:
                edge = Edge(
                    id=f"edge_{uuid.uuid4().hex[:12]}",
                    source=main_company.id,
                    target=entity.id,
                    type=EdgeType.HAS_METRIC,
                    graph_id=graph_id,
                    properties=entity.properties
                )
                edges.append(edge)

        # Link summary to metrics if present
        for entity in entities:
            if entity.type == EntityType.CLAUSE and entity.name == "Document Summary":
                for other in entities:
                    if other.type == EntityType.METRIC:
                        edge = Edge(
                            id=f"edge_{uuid.uuid4().hex[:12]}",
                            source=entity.id,
                            target=other.id,
                            type=EdgeType.HAS_METRIC,
                            graph_id=graph_id,
                            properties={}
                        )
                        edges.append(edge)
        
        return edges
    
    def _deduplicate_edges(self, edges: List[Edge]) -> List[Edge]:
        """Remove duplicate edges (same source, target, type)"""
        seen = set()
        unique_edges = []
        
        for edge in edges:
            key = (edge.source, edge.target, edge.type)
            if key not in seen:
                seen.add(key)
                unique_edges.append(edge)
        
        return unique_edges
    
    def _map_entity_type(self, ade_type: str) -> EntityType:
        """Map ADE entity type to internal EntityType"""
        return self.entity_type_mapping.get(ade_type.upper())

    def _extract_metrics_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract simple metrics from free text: percentages and currency amounts."""
        import re
        metrics: List[Dict[str, Any]] = []
        # Percentages (e.g., 8%, 9.2%)
        for match in re.finditer(r"(\d{1,3}(?:\.\d{1,2})?)%", text):
            value = float(match.group(1))
            metrics.append({"name": f"percentage_{match.group(1)}%", "value": value, "unit": "%"})
        # Currency amounts (very simple matcher: $50M, $12M, $8.3M, 50M)
        for match in re.finditer(r"\$?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)(\s*[MBKmbk])?", text):
            raw = match.group(1)
            unit = (match.group(2) or '').strip().upper()
            try:
                num = float(raw.replace(',', ''))
            except Exception:
                continue
            # Normalize units
            multiplier = 1.0
            if unit == 'K':
                multiplier = 1e3
            elif unit == 'M':
                multiplier = 1e6
            elif unit == 'B':
                multiplier = 1e9
            value = num * multiplier
            metrics.append({"name": f"amount_{raw}{unit}", "value": value, "unit": "USD"})
        return metrics
    
    async def _extract_entities_from_key_values(
        self,
        ade_output: Dict[str, Any],
        document_id: str,
        graph_id: str
    ) -> Tuple[List[Entity], Dict[str, Entity]]:
        """
        Extract entities from schema-based key_values extraction.
        
        Parses nested structures from financial_basic or similar schemas:
        - company_info: Company entity
        - loans: Array of Loan entities
        - metrics: Metric entities
        - risks: Risk/Clause entities
        
        Also handles adaptive schemas that put data in 'extraction' field:
        - cities: Array of Location entities (municipal financials)
        - jurisdictions: Array of Location entities
        - Any array of objects with inferrable entity types
        """
        entities = []
        entity_map = {}
        
        # Process key_values array (standard ADE format)
        for kv in ade_output.get("key_values", []):
            key = kv.get("key")
            value = kv.get("value")
            
            if not isinstance(value, (dict, list)):
                continue
            
            # Process known structures (backward compatibility)
            processed = await self._process_known_structure(key, value, document_id, graph_id, entity_map)
            if processed:
                entities.extend(processed)
                continue
            
            # Generic array processing for adaptive schemas
            if isinstance(value, list):
                generic_entities = await self._process_generic_array(key, value, document_id, graph_id, entity_map)
                if generic_entities:
                    entities.extend(generic_entities)
                    continue
        
        # Process 'extraction' field directly (adaptive schema format)
        extraction_data = ade_output.get("extraction", {})
        if extraction_data and isinstance(extraction_data, dict):
            for key, value in extraction_data.items():
                if not isinstance(value, (dict, list)):
                    continue
                
                # Skip if already processed from key_values
                if any(kv.get("key") == key for kv in ade_output.get("key_values", [])):
                    continue
                
                # Process known structures
                processed = await self._process_known_structure(key, value, document_id, graph_id, entity_map)
                if processed:
                    entities.extend(processed)
                    continue
                
                # Generic array processing
                if isinstance(value, list):
                    generic_entities = await self._process_generic_array(key, value, document_id, graph_id, entity_map)
                    if generic_entities:
                        entities.extend(generic_entities)
        
        return entities, entity_map
    
    async def _process_known_structure(
        self,
        key: str,
        value: Any,
        document_id: str,
        graph_id: str,
        entity_map: Dict[str, Entity]
    ) -> List[Entity]:
        """Process known structures (company_info, loans, metrics, risks)"""
        entities = []
        
        if key == "company_info" and isinstance(value, dict):
            company_name = value.get("company_name")
            if company_name:
                company = Entity(
                    id=f"ent_{uuid.uuid4().hex[:12]}",
                    type=EntityType.COMPANY,
                    name=company_name,
                    properties={
                        "ticker": value.get("ticker"),
                        "report_type": value.get("report_type"),
                        "fiscal_year": value.get("fiscal_year")
                    },
                    citations=[],
                    document_id=document_id,
                    graph_id=graph_id
                )
                entities.append(company)
                entity_map[company_name] = company
        
        # Parse loans array
        elif key == "loans" and isinstance(value, list):
            for loan_data in value:
                if not isinstance(loan_data, dict):
                    continue
                
                instrument = loan_data.get("instrument")
                lender_name = loan_data.get("lender")
                
                # Create lender entity if it doesn't exist
                if lender_name and lender_name not in entity_map:
                    lender = Entity(
                        id=f"ent_{uuid.uuid4().hex[:12]}",
                        type=EntityType.COMPANY,  # Banks/Lenders are companies
                        name=lender_name,
                        properties={},
                        citations=[],
                        document_id=document_id,
                        graph_id=graph_id
                    )
                    entities.append(lender)
                    entity_map[lender_name] = lender
                
                # Create loan entity
                if instrument:
                    loan = Entity(
                        id=f"ent_{uuid.uuid4().hex[:12]}",
                        type=EntityType.LOAN,
                        name=instrument,
                        properties={
                            "lender": lender_name,
                            "principal": loan_data.get("principal"),
                            "rate": loan_data.get("rate"),
                            "maturity": loan_data.get("maturity"),
                            "covenants": loan_data.get("covenants")
                        },
                        citations=[],
                        document_id=document_id,
                        graph_id=graph_id
                    )
                    entities.append(loan)
                    entity_map[instrument] = loan
        
        # Parse metrics object
        elif key == "metrics" and isinstance(value, dict):
            for metric_name, metric_value in value.items():
                if metric_value:  # Skip None/empty values
                    metric = Entity(
                        id=f"ent_{uuid.uuid4().hex[:12]}",
                        type=EntityType.METRIC,
                        name=metric_name,
                        properties={"value": metric_value},
                        citations=[],
                        document_id=document_id,
                        graph_id=graph_id
                    )
                    entities.append(metric)
                    entity_map[metric_name] = metric
        
        # Parse risks array
        elif key == "risks" and isinstance(value, list):
            for risk_data in value:
                if not isinstance(risk_data, dict):
                    continue
                
                risk_title = risk_data.get("risk_title")
                if risk_title:
                    risk = Entity(
                        id=f"ent_{uuid.uuid4().hex[:12]}",
                        type=EntityType.CLAUSE,
                        name=risk_title,
                        properties={"description": risk_data.get("description", "")},
                        citations=[],
                        document_id=document_id,
                        graph_id=graph_id
                    )
                    entities.append(risk)
                    entity_map[risk_title] = risk
        
        return entities
    
    async def _process_generic_array(
        self,
        key: str,
        value: List[Any],
        document_id: str,
        graph_id: str,
        entity_map: Dict[str, Entity]
    ) -> List[Entity]:
        """
        Process generic arrays using LLM to infer entity types and structure.
        Handles adaptive schema structures like cities, jurisdictions, etc.
        """
        import boto3
        from config import settings
        
        if not value or not isinstance(value, list):
            return []
        
        # Check if array contains objects
        if not any(isinstance(item, dict) for item in value):
            return []
        
        # TEMP: the LLM normalization is unstable for large tables. Use deterministic fallback.
        logger.info(f"🤖 Skipping LLM normalization for array '{key}' ({len(value)} items); using deterministic fallback.")
        return self._fallback_array_processing(key, value, document_id, graph_id, entity_map)
        
        logger.info(f"🤖 Using LLM to normalize array: {key} ({len(value)} items)")
        
        try:
            # Initialize Bedrock client
            bedrock = boto3.client(
                service_name="bedrock-runtime",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            
            # Prepare sample data for LLM (first 3 items)
            sample_items = value[:3]
            
            # System prompt for normalization
            system_prompt = """You are a data normalization expert. Analyze extracted data and determine:
1. What entity type best represents this data (Company, Location, Person, Loan, Metric, etc.)
2. Which field should be used as the entity name
3. What relationships exist between entities

Available entity types:
- COMPANY: Organizations, corporations, lenders, banks
- LOCATION: Cities, countries, jurisdictions, addresses
- PERSON: Individuals, officers, directors
- LOAN: Debt instruments, loans, bonds
- METRIC: Financial metrics, KPIs, measurements
- SUBSIDIARY: Child companies, divisions
- INVOICE: Bills, invoices
- CLAUSE: Contracts, terms, risks
- VENDOR: Suppliers, vendors

Respond with JSON:
{
  "entity_type": "LOCATION",
  "name_field": "city_name",
  "description": "Municipal financial entities",
  "relationships": [
    {"field": "county", "creates_edge": true, "edge_type": "LOCATED_IN"}
  ]
}"""
            
            user_prompt = f"""Analyze this data array and determine the best entity structure:

Array name: "{key}"
Number of items: {len(value)}

Sample items:
{json.dumps(sample_items, indent=2)}

Provide the normalization strategy in JSON format."""
            
            # Use Claude via InvokeModel API
            model_id = settings.BEDROCK_MODEL_ID
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "temperature": 0.3,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            
            llm_response = None
            for block in content:
                if block.get('type') == 'text':
                    llm_response = block.get('text', '')
                    break
            
            if not llm_response:
                logger.warning(f"No LLM response for {key}, using fallback")
                return self._fallback_array_processing(key, value, document_id, graph_id, entity_map)
            
            # Parse LLM response
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', llm_response, re.DOTALL)
            if json_match:
                strategy = json.loads(json_match.group(1))
            else:
                strategy = json.loads(llm_response.strip())
            
            logger.info(f"LLM normalization strategy: {strategy.get('entity_type')} using {strategy.get('name_field')}")
            
            # Apply the strategy
            return await self._apply_normalization_strategy(
                strategy, value, document_id, graph_id, entity_map
            )
            
        except Exception as e:
            logger.warning(f"LLM normalization failed for {key}: {e}, using fallback")
            return self._fallback_array_processing(key, value, document_id, graph_id, entity_map)
    
    async def _apply_normalization_strategy(
        self,
        strategy: Dict[str, Any],
        data: List[Dict],
        document_id: str,
        graph_id: str,
        entity_map: Dict[str, Entity]
    ) -> List[Entity]:
        """Apply LLM-determined normalization strategy to create entities"""
        entities = []
        
        entity_type_str = strategy.get("entity_type", "METRIC")
        name_field = strategy.get("name_field")
        
        # Map string to EntityType
        entity_type = self.entity_type_mapping.get(entity_type_str.upper(), EntityType.METRIC)
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            # Get entity name from specified field
            entity_name = item.get(name_field) if name_field else item.get("name", f"Item_{uuid.uuid4().hex[:6]}")
            
            if not entity_name:
                continue
            
            # Extract citations if available
            citations = []
            if "citations" in item:
                citations = [
                    Citation(**citation_data) if isinstance(citation_data, dict) else citation_data
                    for citation_data in item.get("citations", [])
                ]
            elif "page" in item:
                # Create citation from page number in properties
                citations = [Citation(page=item["page"])]
            
            # Create entity with all properties
            entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=entity_type,
                name=str(entity_name),
                properties=item,  # Store all fields as properties
                citations=citations,
                document_id=document_id,
                graph_id=graph_id
            )
            
            entities.append(entity)
            entity_map[str(entity_name)] = entity
        
        logger.info(f"Created {len(entities)} {entity_type} entities")
        return entities
    
    def _fallback_array_processing(
        self,
        key: str,
        value: List[Any],
        document_id: str,
        graph_id: str,
        entity_map: Dict[str, Entity]
    ) -> List[Entity]:
        """Fallback: Simple heuristic-based array processing"""
        entities = []
        
        # Infer entity type from key name
        key_lower = key.lower()
        if "city" in key_lower or "cities" in key_lower or "jurisdiction" in key_lower:
            entity_type = EntityType.LOCATION
            name_field = "city_name"
        elif "company" in key_lower or "companies" in key_lower:
            entity_type = EntityType.COMPANY
            name_field = "company_name"
        elif "loan" in key_lower or "loans" in key_lower:
            entity_type = EntityType.LOAN
            name_field = "instrument"
        elif "person" in key_lower or "people" in key_lower:
            entity_type = EntityType.PERSON
            name_field = "name"
        else:
            entity_type = EntityType.METRIC
            name_field = "name"
        
        for item in value:
            if not isinstance(item, dict):
                continue
            
            # Try to find a name field
            entity_name = (
                item.get(name_field) or
                item.get("name") or
                item.get("title") or
                item.get("id") or
                f"{key}_{uuid.uuid4().hex[:6]}"
            )
            
            # Extract citations if available
            citations = []
            if "citations" in item:
                citations = [
                    Citation(**citation_data) if isinstance(citation_data, dict) else citation_data
                    for citation_data in item.get("citations", [])
                ]
            elif "page" in item:
                # Create citation from page number in properties
                citations = [Citation(page=item["page"])]
            
            entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=entity_type,
                name=str(entity_name),
                properties=item,
                citations=citations,
                document_id=document_id,
                graph_id=graph_id
            )
            
            entities.append(entity)
            entity_map[str(entity_name)] = entity
        
        logger.info(f"Fallback: Created {len(entities)} {entity_type} entities from {key}")
        return entities
    
    async def _extract_entities_from_table(
        self,
        table: Dict[str, Any],
        document_id: str,
        graph_id: str
    ) -> List[Entity]:
        """Extract entities from table data"""
        entities = []
        
        # Example: Extract loan entities from debt schedule tables
        if "debt" in table.get("caption", "").lower():
            for row in table.get("rows", []):
                # Create loan entity from row
                entity = Entity(
                    id=f"ent_{uuid.uuid4().hex[:12]}",
                    type=EntityType.LOAN,
                    name=row.get("description", "Unknown Loan"),
                    properties={
                        "principal": row.get("principal"),
                        "rate": row.get("interest_rate"),
                        "maturity": row.get("maturity_date")
                    },
                    citations=[Citation(
                        page=table.get("page"),
                        table_id=table.get("id")
                    )],
                    document_id=document_id,
                    graph_id=graph_id
                )
                entities.append(entity)
        
        return entities
    
    def _should_extract_more(self, ade_output: Dict[str, Any], document_id: str) -> bool:
        """
        Determine if we should use deterministic fallback even though we have some entities.
        Returns True if the document appears to have substantial content that wasn't fully extracted.
        """
        try:
            from main import documents_store
            document = documents_store.get(document_id)
            
            if not document or not document.metadata:
                return False
            
            markdown = document.metadata.get("markdown", "")
            
            # Check if markdown has tables (indicator of structured data)
            has_tables = "<table" in markdown or "|" in markdown
            
            # Check if markdown is substantial (>10k chars suggests complex document)
            is_substantial = len(markdown) > 10000
            
            # If we have tables or substantial content, worth trying LLM extraction
            return has_tables or is_substantial
            
        except Exception:
            return False
    
    async def _extract_entities_from_tables(
        self,
        ade_output: Dict[str, Any],
        document_id: str,
        graph_id: str
    ) -> List[Entity]:
        """
        Extract entities from markdown tables using deterministic parsing (no LLM needed!)
        This is a fallback for complex tables that ADE struggles with
        """
        entities = []
        
        try:
            # Get markdown from document metadata
            from main import documents_store
            document = documents_store.get(document_id)
            
            if not document or not document.metadata:
                logger.warning("No document metadata available for table parsing")
                return entities
            
            markdown = document.metadata.get("markdown", "")
            if not markdown:
                logger.warning("No markdown available for table parsing")
                return entities
            
            # Get the original schema that was attempted (if any)
            extraction_schema = document.metadata.get("adaptive_schema")
            
            # Use deterministic markdown table parser (no LLM!)
            parsed_result = self.markdown_parser.extract_entities_from_markdown(
                markdown=markdown,
                extraction_schema=extraction_schema,
                max_entities=500  # Can handle more since it's fast
            )
            
            # Convert parsed entities to our Entity model
            for parsed_entity in parsed_result.get("entities", []):
                entity_type_str = parsed_entity.get("type", "other").upper()
                entity_type = self.entity_type_mapping.get(entity_type_str, EntityType.CLAUSE)
                
                # Create entity
                entity = Entity(
                    id=f"ent_{uuid.uuid4().hex[:12]}",
                    type=entity_type,
                    name=parsed_entity.get("name", "Unknown"),
                    properties=parsed_entity.get("properties", {}),
                    citations=[Citation(
                        page=1,  # Default page for table parsing
                        section=parsed_entity.get("source_reference", "Table parsing")
                    )],
                    document_id=document_id,
                    graph_id=graph_id
                )
                entities.append(entity)
            
            logger.info(f"Table parser extracted {len(entities)} entities from markdown")
            
        except Exception as e:
            logger.error(f"Table parsing failed: {e}", exc_info=True)
        
        return entities


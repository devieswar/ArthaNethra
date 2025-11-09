"""
Deterministic contract parser
Extracts parties, clauses, obligations, and dates from contracts
"""
import re
import uuid
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from loguru import logger

from models.entity import Entity, EntityType
from models.citation import Citation


class ContractParser:
    """Parse contracts deterministically"""
    
    def __init__(self):
        # Common contract section patterns
        self.section_patterns = [
            r'^(\d+\.?\s+[A-Z][A-Za-z\s]+)',  # "1. Definitions"
            r'^([A-Z\s]+)$',  # "TERMS AND CONDITIONS"
            r'^(ARTICLE\s+[IVX\d]+)',  # "ARTICLE I"
            r'^(Section\s+\d+\.?\d*)',  # "Section 1.1"
        ]
    
    def extract_entities_from_contract(
        self,
        markdown: str,
        document_id: str,
        graph_id: str
    ) -> List[Entity]:
        """
        Extract entities from contract markdown
        
        Returns:
            List of entities including:
            - Contract (main document)
            - Party entities (companies/people)
            - Clause entities (terms, obligations)
        """
        logger.info("Parsing contract deterministically")
        
        soup = BeautifulSoup(markdown, 'html.parser')
        text = soup.get_text()
        
        entities = []
        
        # Extract contract metadata
        contract_data = self._extract_contract_metadata(text)
        
        # Create Contract entity
        contract_entity = Entity(
            id=f"ent_{uuid.uuid4().hex[:12]}",
            type=EntityType.CLAUSE,  # Using CLAUSE for contract documents
            name=contract_data.get("title", "Contract Agreement"),
            properties={
                "contract_type": contract_data.get("contract_type"),
                "effective_date": contract_data.get("effective_date"),
                "expiration_date": contract_data.get("expiration_date"),
                "term_length": contract_data.get("term_length"),
                "governing_law": contract_data.get("governing_law"),
                "jurisdiction": contract_data.get("jurisdiction")
            },
            citations=[Citation(page=1, section="Contract Header")],
            document_id=document_id,
            graph_id=graph_id
        )
        entities.append(contract_entity)
        
        # Extract parties
        parties = self._extract_parties(text)
        for idx, party in enumerate(parties):
            party_type = EntityType.COMPANY if any(word in party.get("name", "").upper() for word in ["INC", "LLC", "CORP", "LTD", "COMPANY"]) else EntityType.PERSON
            
            party_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=party_type,
                name=party.get("name", f"Party {idx+1}"),
                properties={
                    "role": party.get("role"),  # "seller", "buyer", "lender", "borrower"
                    "address": party.get("address"),
                    "representative": party.get("representative")
                },
                citations=[Citation(page=1, section="Parties")],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(party_entity)
        
        # Extract sections and clauses
        sections = self._extract_sections(soup, text)
        for section in sections:
            clause_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=EntityType.CLAUSE,
                name=section.get("title", "Clause"),
                properties={
                    "section_number": section.get("section_number"),
                    "content": section.get("content"),
                    "clause_type": section.get("clause_type"),
                    "obligations": section.get("obligations", [])
                },
                citations=[Citation(page=1, section=section.get("title", "Clause"))],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(clause_entity)
        
        # Extract obligations
        obligations = self._extract_obligations(text)
        for idx, obligation in enumerate(obligations):
            obligation_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=EntityType.CLAUSE,
                name=f"Obligation: {obligation.get('summary', 'Obligation')}",
                properties={
                    "description": obligation.get("description"),
                    "party": obligation.get("party"),
                    "due_date": obligation.get("due_date"),
                    "type": "obligation"
                },
                citations=[Citation(page=1, section="Obligations")],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(obligation_entity)
        
        logger.info(f"Extracted {len(entities)} entities from contract")
        return entities
    
    def _extract_contract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract contract metadata"""
        data = {}
        
        # Contract type
        types = ["agreement", "contract", "license", "lease", "loan", "service"]
        for contract_type in types:
            if contract_type in text.lower()[:500]:  # Check first 500 chars
                data["contract_type"] = contract_type
                break
        
        # Extract title (usually first heading or capitalized text)
        title_match = re.search(r'^([A-Z\s]+(?:AGREEMENT|CONTRACT|LICENSE))', text, re.MULTILINE)
        if title_match:
            data["title"] = title_match.group(1).strip()
        
        # Effective date
        effective_patterns = [
            r'effective\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'dated\s+as\s+of:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'entered\s+into\s+on:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        for pattern in effective_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["effective_date"] = match.group(1)
                break
        
        # Expiration/termination date
        expiration_patterns = [
            r'expiration\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'termination\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'expires?\s+on:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        for pattern in expiration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["expiration_date"] = match.group(1)
                break
        
        # Term length
        term_match = re.search(r'term\s+of\s+(\d+)\s+(year|month|day)s?', text, re.IGNORECASE)
        if term_match:
            data["term_length"] = f"{term_match.group(1)} {term_match.group(2)}s"
        
        # Governing law
        law_match = re.search(r'governed\s+by\s+(?:the\s+)?laws?\s+of\s+([A-Za-z\s]+)(?:\.|,)', text, re.IGNORECASE)
        if law_match:
            data["governing_law"] = law_match.group(1).strip()
        
        return data
    
    def _extract_parties(self, text: str) -> List[Dict[str, Any]]:
        """Extract contracting parties"""
        parties = []
        
        # Pattern 1: "between ... and ..."
        between_match = re.search(
            r'between\s+([^,]+?(?:Inc|LLC|Ltd|Corp|Company|[A-Z][a-z]+\s+[A-Z][a-z]+))[,\s]+(?:and|&)\s+([^,]+?(?:Inc|LLC|Ltd|Corp|Company|[A-Z][a-z]+\s+[A-Z][a-z]+))',
            text,
            re.IGNORECASE
        )
        if between_match:
            parties.append({
                "name": between_match.group(1).strip(),
                "role": "party_1"
            })
            parties.append({
                "name": between_match.group(2).strip(),
                "role": "party_2"
            })
        
        # Pattern 2: Look for "Lender:", "Borrower:", "Seller:", "Buyer:", etc.
        role_patterns = [
            (r'lender:?\s*([^\n]+)', "lender"),
            (r'borrower:?\s*([^\n]+)', "borrower"),
            (r'seller:?\s*([^\n]+)', "seller"),
            (r'buyer:?\s*([^\n]+)', "buyer"),
            (r'licensor:?\s*([^\n]+)', "licensor"),
            (r'licensee:?\s*([^\n]+)', "licensee"),
            (r'lessor:?\s*([^\n]+)', "lessor"),
            (r'lessee:?\s*([^\n]+)', "lessee")
        ]
        
        for pattern, role in role_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                party_name = match.group(1).strip()
                # Remove trailing punctuation and extra text
                party_name = re.sub(r'[,\.].*$', '', party_name).strip()
                if party_name and not any(p["name"] == party_name for p in parties):
                    parties.append({
                        "name": party_name,
                        "role": role
                    })
        
        return parties
    
    def _extract_sections(self, soup: BeautifulSoup, text: str) -> List[Dict[str, Any]]:
        """Extract contract sections and clauses"""
        sections = []
        
        # Look for headings
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
        for heading in headings:
            section_title = heading.get_text(strip=True)
            
            # Get section number if present
            section_number = None
            num_match = re.match(r'^(\d+\.?\d*)', section_title)
            if num_match:
                section_number = num_match.group(1)
            
            # Get content until next heading
            content_parts = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ['h1', 'h2', 'h3', 'h4']:
                    break
                content_parts.append(sibling.get_text(strip=True))
            
            content = " ".join(content_parts)
            
            # Determine clause type
            clause_type = self._classify_clause_type(section_title, content)
            
            sections.append({
                "title": section_title,
                "section_number": section_number,
                "content": content[:500],  # Limit content length
                "clause_type": clause_type
            })
        
        # If no headings found, try to extract numbered sections from text
        if not sections:
            lines = text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a section header
                for pattern in self.section_patterns:
                    match = re.match(pattern, line)
                    if match:
                        # Save previous section
                        if current_section:
                            sections.append(current_section)
                        
                        # Start new section
                        current_section = {
                            "title": match.group(1).strip(),
                            "section_number": None,
                            "content": "",
                            "clause_type": "general"
                        }
                        break
                
                # Add content to current section
                if current_section and not any(re.match(p, line) for p in self.section_patterns):
                    current_section["content"] += line + " "
            
            # Add last section
            if current_section:
                sections.append(current_section)
        
        return sections[:20]  # Limit to first 20 sections
    
    def _classify_clause_type(self, title: str, content: str) -> str:
        """Classify clause type based on title and content"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        if any(word in title_lower for word in ["payment", "price", "fee", "compensation"]):
            return "payment"
        elif any(word in title_lower for word in ["term", "duration"]):
            return "term"
        elif any(word in title_lower for word in ["termination", "cancellation"]):
            return "termination"
        elif any(word in title_lower for word in ["warranty", "guarantee"]):
            return "warranty"
        elif any(word in title_lower for word in ["liability", "indemnity"]):
            return "liability"
        elif any(word in title_lower for word in ["confidential", "nda", "non-disclosure"]):
            return "confidentiality"
        elif any(word in title_lower for word in ["delivery", "performance"]):
            return "performance"
        elif "shall" in content_lower or "must" in content_lower:
            return "obligation"
        else:
            return "general"
    
    def _extract_obligations(self, text: str) -> List[Dict[str, Any]]:
        """Extract specific obligations from contract"""
        obligations = []
        
        # Look for "shall" or "must" statements
        shall_pattern = r'([A-Za-z\s]+)\s+(?:shall|must)\s+([^\.]+)\.'
        for match in re.finditer(shall_pattern, text, re.IGNORECASE):
            party = match.group(1).strip()
            action = match.group(2).strip()
            
            obligations.append({
                "party": party,
                "description": action,
                "summary": action[:50] + "..." if len(action) > 50 else action
            })
            
            if len(obligations) >= 10:  # Limit to 10 obligations
                break
        
        return obligations


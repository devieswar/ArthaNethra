"""
Document type detection and adaptive parsing strategies
"""
import re
from typing import Dict, Any, Optional, List
from loguru import logger
from bs4 import BeautifulSoup


class DocumentTypeDetector:
    """Detects document type from markdown content"""
    
    def __init__(self):
        # Document type patterns with confidence scoring
        self.patterns = {
            "financial_statement": {
                "keywords": ["balance sheet", "income statement", "cash flow", "assets", "liabilities", "equity"],
                "indicators": ["total assets", "net income", "revenue", "expenses"],
                "structure": ["table"],
                "confidence_threshold": 0.6
            },
            "invoice": {
                "keywords": ["invoice", "bill to", "ship to", "invoice number", "due date", "amount due"],
                "indicators": ["subtotal", "tax", "total", "quantity", "price"],
                "structure": ["key_value", "line_items"],
                "confidence_threshold": 0.7
            },
            "contract": {
                "keywords": ["whereas", "parties", "agreement", "contract", "hereby", "witnesseth"],
                "indicators": ["term", "conditions", "obligations", "effective date"],
                "structure": ["sections", "clauses"],
                "confidence_threshold": 0.6
            },
            "receipt": {
                "keywords": ["receipt", "transaction", "purchased", "paid", "store"],
                "indicators": ["date", "time", "items", "total", "payment method"],
                "structure": ["line_items"],
                "confidence_threshold": 0.7
            },
            "email": {
                "keywords": ["from:", "to:", "subject:", "date:", "cc:", "bcc:"],
                "indicators": ["sent", "received", "reply", "forward"],
                "structure": ["headers", "body"],
                "confidence_threshold": 0.8
            },
            "form": {
                "keywords": ["application", "form", "applicant", "please fill"],
                "indicators": ["name:", "address:", "phone:", "signature:"],
                "structure": ["key_value"],
                "confidence_threshold": 0.6
            },
            "loan_document": {
                "keywords": ["loan", "borrower", "lender", "principal", "interest rate", "maturity"],
                "indicators": ["loan amount", "apr", "monthly payment", "term"],
                "structure": ["key_value", "clauses"],
                "confidence_threshold": 0.7
            }
        }
    
    def detect_document_type(self, markdown: str) -> Dict[str, Any]:
        """
        Detect document type from markdown content
        
        Returns:
            {
                "type": str,
                "confidence": float,
                "structure": List[str],
                "parsing_strategy": str
            }
        """
        markdown_lower = markdown.lower()
        
        # Calculate confidence scores for each type
        scores = {}
        for doc_type, pattern in self.patterns.items():
            score = 0.0
            
            # Check keywords (weight: 40%)
            keyword_matches = sum(1 for kw in pattern["keywords"] if kw in markdown_lower)
            keyword_score = (keyword_matches / len(pattern["keywords"])) * 0.4
            
            # Check indicators (weight: 40%)
            indicator_matches = sum(1 for ind in pattern["indicators"] if ind in markdown_lower)
            indicator_score = (indicator_matches / len(pattern["indicators"])) * 0.4
            
            # Check structure (weight: 20%)
            structure_score = 0.0
            for struct in pattern["structure"]:
                if struct == "table" and "<table" in markdown:
                    structure_score += 0.2
                elif struct == "key_value" and re.search(r'\w+:\s*\w+', markdown):
                    structure_score += 0.2
                elif struct == "sections" and re.search(r'^#+\s+', markdown, re.MULTILINE):
                    structure_score += 0.2
            
            total_score = keyword_score + indicator_score + structure_score
            scores[doc_type] = total_score
        
        # Get best match
        if not scores:
            return self._default_detection(markdown)
        
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]
        
        # If confidence too low, return generic
        if confidence < self.patterns[best_type]["confidence_threshold"]:
            logger.info(f"Low confidence ({confidence:.2f}) for {best_type}, using generic")
            return self._default_detection(markdown)
        
        logger.info(f"✅ Detected document type: {best_type} (confidence: {confidence:.2f})")
        
        return {
            "type": best_type,
            "confidence": confidence,
            "structure": self.patterns[best_type]["structure"],
            "parsing_strategy": self._determine_parsing_strategy(best_type, markdown)
        }
    
    def _determine_parsing_strategy(self, doc_type: str, markdown: str) -> str:
        """Determine best parsing strategy for document type"""
        has_tables = "<table" in markdown or "|" in markdown
        
        strategies = {
            "financial_statement": "deterministic_table" if has_tables else "ade_with_template",
            "invoice": "template_extraction",  # Key-value pairs
            "contract": "clause_extraction",  # Nested sections
            "receipt": "line_item_extraction",  # Line items
            "email": "header_body_split",  # Headers + body
            "form": "template_extraction",  # Key-value pairs
            "loan_document": "hybrid"  # Mix of KV and clauses
        }
        
        return strategies.get(doc_type, "ade_generic")
    
    def _default_detection(self, markdown: str) -> Dict[str, Any]:
        """Default detection for unknown documents"""
        has_tables = "<table" in markdown or "|" in markdown
        
        return {
            "type": "generic",
            "confidence": 0.0,
            "structure": ["table"] if has_tables else ["text"],
            "parsing_strategy": "deterministic_table" if has_tables else "ade_generic"
        }


class DocumentTypeParser:
    """Parser strategies for different document types"""
    
    def __init__(self):
        self.detector = DocumentTypeDetector()
    
    def can_parse_deterministically(self, doc_type: str) -> bool:
        """Check if document type can be parsed without LLM"""
        deterministic_types = [
            "financial_statement",  # ✅ Tables → Already implemented
            "invoice",              # ✅ EASY: Key-value pairs + line items
            "receipt",              # ✅ EASY: Simple line items
            "email",                # ✅ EASY: Headers + body
            "form"                  # ✅ MEDIUM: Key-value pairs
        ]
        return doc_type in deterministic_types
    
    def get_parsing_difficulty(self, doc_type: str) -> str:
        """Rate parsing difficulty"""
        difficulties = {
            # Already implemented
            "financial_statement": "IMPLEMENTED ✅",
            
            # Easy (regex + BeautifulSoup)
            "invoice": "EASY 🟢",
            "receipt": "EASY 🟢", 
            "email": "EASY 🟢",
            "form": "EASY 🟢",
            
            # Medium (needs some logic)
            "contract": "MEDIUM 🟡",
            "loan_document": "MEDIUM 🟡",
            
            # Hard (better with LLM)
            "generic": "HARD 🔴 (use ADE)"
        }
        return difficulties.get(doc_type, "UNKNOWN")


# Example parsing functions for each type

def parse_invoice_deterministically(markdown: str) -> Dict[str, Any]:
    """Parse invoice using regex and BeautifulSoup"""
    soup = BeautifulSoup(markdown, 'html.parser')
    text = soup.get_text()
    
    # Extract key fields using regex
    invoice_number = re.search(r'invoice\s*#?:?\s*(\S+)', text, re.IGNORECASE)
    date = re.search(r'date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
    total = re.search(r'total:?\s*\$?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    
    # Extract line items from table or list
    line_items = []
    tables = soup.find_all('table')
    if tables:
        for table in tables:
            rows = table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    line_items.append({
                        "description": cells[0].get_text(strip=True),
                        "quantity": cells[1].get_text(strip=True),
                        "amount": cells[2].get_text(strip=True)
                    })
    
    return {
        "invoice_number": invoice_number.group(1) if invoice_number else None,
        "date": date.group(1) if date else None,
        "total": total.group(1) if total else None,
        "line_items": line_items
    }


def parse_contract_deterministically(markdown: str) -> Dict[str, Any]:
    """Parse contract sections and clauses"""
    soup = BeautifulSoup(markdown, 'html.parser')
    
    # Extract parties
    parties_match = re.search(r'between\s+(.+?)\s+and\s+(.+?)(?:\.|,)', markdown, re.IGNORECASE)
    parties = []
    if parties_match:
        parties = [parties_match.group(1).strip(), parties_match.group(2).strip()]
    
    # Extract sections (headings)
    sections = []
    headings = soup.find_all(['h1', 'h2', 'h3'])
    for heading in headings:
        section_title = heading.get_text(strip=True)
        # Get content until next heading
        section_content = []
        for sibling in heading.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3']:
                break
            section_content.append(sibling.get_text(strip=True))
        
        sections.append({
            "title": section_title,
            "content": " ".join(section_content)
        })
    
    # Extract key dates
    effective_date = re.search(r'effective date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', markdown, re.IGNORECASE)
    
    return {
        "parties": parties,
        "effective_date": effective_date.group(1) if effective_date else None,
        "sections": sections
    }


def parse_email_deterministically(markdown: str) -> Dict[str, Any]:
    """Parse email headers and body"""
    lines = markdown.split('\n')
    
    headers = {}
    body_start = 0
    
    # Parse headers
    for i, line in enumerate(lines):
        if re.match(r'^(From|To|Subject|Date|Cc|Bcc):', line, re.IGNORECASE):
            parts = line.split(':', 1)
            if len(parts) == 2:
                headers[parts[0].strip().lower()] = parts[1].strip()
        elif line.strip() == '' and headers:
            body_start = i + 1
            break
    
    # Get body
    body = '\n'.join(lines[body_start:]).strip()
    
    return {
        "from": headers.get('from'),
        "to": headers.get('to'),
        "subject": headers.get('subject'),
        "date": headers.get('date'),
        "cc": headers.get('cc'),
        "body": body
    }


def parse_receipt_deterministically(markdown: str) -> Dict[str, Any]:
    """Parse receipt items and total"""
    soup = BeautifulSoup(markdown, 'html.parser')
    text = soup.get_text()
    
    # Extract store name (usually first line)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    store = lines[0] if lines else None
    
    # Extract date/time
    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    time_match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)', text, re.IGNORECASE)
    
    # Extract items (pattern: item name followed by price)
    items = []
    item_pattern = r'(.+?)\s+\$?([\d,]+\.?\d{2})'
    for match in re.finditer(item_pattern, text):
        items.append({
            "item": match.group(1).strip(),
            "price": match.group(2)
        })
    
    # Extract total
    total_match = re.search(r'total:?\s*\$?\s*([\d,]+\.?\d{2})', text, re.IGNORECASE)
    
    return {
        "store": store,
        "date": date_match.group(1) if date_match else None,
        "time": time_match.group(1) if time_match else None,
        "items": items,
        "total": total_match.group(1) if total_match else None
    }


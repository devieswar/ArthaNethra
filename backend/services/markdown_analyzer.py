"""
Markdown Structure Analyzer
Analyzes markdown to automatically generate optimal extraction schemas
No LLM needed - pure deterministic analysis!
"""
import re
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger
from bs4 import BeautifulSoup


class MarkdownSchemaAnalyzer:
    """Analyzes markdown structure to generate optimal extraction schemas"""
    
    def __init__(self):
        pass
    
    def analyze_and_generate_schema(self, markdown: str) -> Dict[str, Any]:
        """
        Analyze markdown content and generate an optimal extraction schema
        
        Args:
            markdown: Markdown content to analyze
            
        Returns:
            JSON schema optimized for the content
        """
        logger.info(f"Analyzing markdown structure ({len(markdown)} chars)")
        
        # Detect document type and structure
        has_html_tables = "<table" in markdown
        has_pipe_tables = self._detect_pipe_tables(markdown)
        
        # Extract table structure if present
        if has_html_tables:
            logger.info("Detected HTML tables in markdown")
            schema = self._generate_schema_from_html_tables(markdown)
        elif has_pipe_tables:
            logger.info("Detected pipe-delimited tables in markdown")
            schema = self._generate_schema_from_pipe_tables(markdown)
        else:
            logger.info("ℹ️ No tables detected, using generic schema")
            schema = self._generate_generic_schema(markdown)
        
        logger.info(f"Generated schema with {len(schema.get('properties', {}))} top-level properties")
        return schema
    
    def _detect_pipe_tables(self, markdown: str) -> bool:
        """Detect if markdown contains pipe-delimited tables"""
        # Look for table pattern: | col1 | col2 | col3 |
        lines = markdown.split('\n')
        for i, line in enumerate(lines[:100]):  # Check first 100 lines
            if '|' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                # Check for separator line: |---|---|---|
                if re.match(r'^\s*\|[\s\-:]+\|', next_line):
                    return True
        return False
    
    def _generate_schema_from_html_tables(self, markdown: str) -> Dict[str, Any]:
        """Generate schema by analyzing HTML tables"""
        try:
            soup = BeautifulSoup(markdown, 'html.parser')
            tables = soup.find_all('table')
            
            if not tables:
                return self._generate_generic_schema(markdown)
            
            # Extract headers from ALL tables (they might be continuations of the same table)
            all_headers = []
            seen_headers = set()
            
            for table in tables:
                headers = self._extract_table_headers(table)
                for header in headers:
                    # Avoid duplicates
                    if header not in seen_headers:
                        all_headers.append(header)
                        seen_headers.add(header)
            
            if not all_headers:
                logger.warning("Could not extract table headers, using generic schema")
                return self._generate_generic_schema(markdown)
            
            logger.info(f"Detected {len(all_headers)} columns across {len(tables)} tables: {all_headers[:5]}...")
            
            # Generate schema based on all headers
            schema = self._build_schema_from_headers(all_headers)
            return schema
            
        except Exception as e:
            logger.error(f"Error analyzing HTML tables: {e}", exc_info=True)
            return self._generate_generic_schema(markdown)
    
    def _extract_table_headers(self, table) -> List[str]:
        """Extract column headers from HTML table"""
        headers = []
        
        # Try to find header row (first <tr>)
        rows = table.find_all('tr')
        if not rows:
            return headers
        
        # Try first few rows to find the best header row
        # (sometimes first row is a category label, actual headers are in row 2)
        best_headers = []
        max_valid_headers = 0
        
        for row_idx in range(min(3, len(rows))):  # Check first 3 rows
            row = rows[row_idx]
            cells = row.find_all(['th', 'td'])
            current_headers = []
            
            for cell in cells:
                header_text = cell.get_text(strip=True)
                if header_text and len(header_text) < 100:  # Reasonable header length
                    # Convert to snake_case
                    header_snake = self._to_snake_case(header_text)
                    if header_snake and header_snake != 'field':  # Valid header
                        current_headers.append(header_snake)
            
            # Keep the row with the most valid headers
            if len(current_headers) > max_valid_headers:
                max_valid_headers = len(current_headers)
                best_headers = current_headers
        
        return best_headers
    
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case"""
        # Remove special characters
        text = re.sub(r'[^\w\s]', '', text)
        # Replace spaces with underscores
        text = re.sub(r'\s+', '_', text)
        # Convert to lowercase
        text = text.lower()
        # Remove multiple underscores
        text = re.sub(r'_+', '_', text)
        # Remove leading/trailing underscores
        text = text.strip('_')
        return text or 'field'
    
    def _build_schema_from_headers(self, headers: List[str]) -> Dict[str, Any]:
        """Build a flat JSON schema from table headers"""
        
        # Determine primary identifier (usually first column)
        identifier_field = headers[0] if headers else "id"
        
        # Build properties
        properties = {}
        for header in headers:
            # Infer type from header name
            field_type = self._infer_field_type(header)
            properties[header] = {"type": field_type}
        
        # Create schema with array of objects (one per row)
        array_name = self._generate_array_name(headers)
        
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Auto-generated Schema from Table Structure",
            "type": "object",
            "properties": {
                array_name: {
                    "type": "array",
                    "description": "Extracted table data",
                    "items": {
                        "type": "object",
                        "required": [identifier_field],
                        "properties": properties
                    }
                }
            }
        }
        
        return schema
    
    def _generate_array_name(self, headers: List[str]) -> str:
        """Generate a meaningful array name from headers"""
        # Common patterns
        if any('city' in h.lower() for h in headers):
            return "cities"
        elif any('company' in h.lower() or 'organization' in h.lower() for h in headers):
            return "companies"
        elif any('person' in h.lower() or 'employee' in h.lower() for h in headers):
            return "people"
        elif any('product' in h.lower() or 'item' in h.lower() for h in headers):
            return "items"
        elif any('transaction' in h.lower() or 'payment' in h.lower() for h in headers):
            return "transactions"
        else:
            return "records"
    
    def _infer_field_type(self, field_name: str) -> str:
        """Infer JSON schema type from field name"""
        field_lower = field_name.lower()
        
        # Numeric indicators
        numeric_keywords = [
            'amount', 'total', 'balance', 'price', 'cost', 'value', 
            'count', 'quantity', 'number', 'rate', 'percent', 'tax',
            'receivable', 'payable', 'asset', 'liability', 'equity',
            'revenue', 'expense', 'income', 'cash', 'investment'
        ]
        
        if any(keyword in field_lower for keyword in numeric_keywords):
            return "number"
        
        # Date indicators
        date_keywords = ['date', 'time', 'year', 'month', 'day']
        if any(keyword in field_lower for keyword in date_keywords):
            return "string"  # Keep as string for flexibility
        
        # Default to string
        return "string"
    
    def _generate_schema_from_pipe_tables(self, markdown: str) -> Dict[str, Any]:
        """Generate schema from pipe-delimited markdown tables"""
        try:
            lines = markdown.split('\n')
            
            # Find first table
            for i, line in enumerate(lines):
                if '|' in line and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if re.match(r'^\s*\|[\s\-:]+\|', next_line):
                        # Found table header
                        headers = [h.strip() for h in line.split('|') if h.strip()]
                        headers_snake = [self._to_snake_case(h) for h in headers]
                        
                        logger.info(f"Detected pipe table with {len(headers_snake)} columns")
                        return self._build_schema_from_headers(headers_snake)
            
            return self._generate_generic_schema(markdown)
            
        except Exception as e:
            logger.error(f"Error analyzing pipe tables: {e}")
            return self._generate_generic_schema(markdown)
    
    def _generate_generic_schema(self, markdown: str) -> Dict[str, Any]:
        """Generate a generic schema for unstructured content"""
        logger.info("Generating generic schema for unstructured content")
        
        # Check for common document types
        markdown_lower = markdown.lower()
        
        if any(word in markdown_lower for word in ['invoice', 'bill', 'receipt']):
            return self._invoice_schema()
        elif any(word in markdown_lower for word in ['contract', 'agreement']):
            return self._contract_schema()
        elif any(word in markdown_lower for word in ['financial', 'balance sheet', 'income statement']):
            return self._financial_schema()
        else:
            return self._default_schema()
    
    def _invoice_schema(self) -> Dict[str, Any]:
        """Schema for invoice documents"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Invoice",
            "type": "object",
            "properties": {
                "invoice_number": {"type": "string"},
                "date": {"type": "string"},
                "vendor": {"type": "string"},
                "customer": {"type": "string"},
                "total_amount": {"type": "number"},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number"},
                            "amount": {"type": "number"}
                        }
                    }
                }
            }
        }
    
    def _contract_schema(self) -> Dict[str, Any]:
        """Schema for contract documents"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Contract",
            "type": "object",
            "properties": {
                "contract_title": {"type": "string"},
                "effective_date": {"type": "string"},
                "parties": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "terms": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "signatures": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "party": {"type": "string"},
                            "date": {"type": "string"}
                        }
                    }
                }
            }
        }
    
    def _financial_schema(self) -> Dict[str, Any]:
        """Schema for financial statements"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Financial Statement",
            "type": "object",
            "properties": {
                "report_title": {"type": "string"},
                "period": {"type": "string"},
                "entity": {"type": "string"},
                "financial_metrics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "metric_name": {"type": "string"},
                            "value": {"type": "number"},
                            "category": {"type": "string"}
                        }
                    }
                }
            }
        }
    
    def _default_schema(self) -> Dict[str, Any]:
        """Default schema for generic documents"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Document Data",
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "key_entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "value": {"type": "string"}
                        }
                    }
                }
            }
        }


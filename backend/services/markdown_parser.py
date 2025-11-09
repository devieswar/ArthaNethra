"""
Deterministic markdown table parser for extracting structured data
No LLM needed - pure Python parsing of markdown tables
"""
import re
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger
from bs4 import BeautifulSoup


class MarkdownTableParser:
    """Parse markdown tables into structured entities without using LLM"""
    
    def __init__(self):
        pass
    
    def extract_entities_from_markdown(
        self,
        markdown: str,
        extraction_schema: Optional[Dict[str, Any]] = None,
        max_entities: int = 500
    ) -> Dict[str, Any]:
        """
        Extract entities from markdown tables using deterministic parsing
        
        Args:
            markdown: Markdown content with tables
            extraction_schema: Schema that was attempted (used for hints)
            max_entities: Maximum number of entities to extract
            
        Returns:
            Dict with extracted entities in structured format
        """
        logger.info(f"Parsing markdown tables deterministically ({len(markdown)} chars)")
        
        entities = []
        
        # Parse HTML tables (ADE outputs HTML table tags in markdown)
        html_entities = self._parse_html_tables(markdown, max_entities)
        entities.extend(html_entities)
        
        # Parse markdown pipe tables (| col1 | col2 | format)
        if len(entities) < max_entities:
            pipe_entities = self._parse_pipe_tables(markdown, max_entities - len(entities))
            entities.extend(pipe_entities)
        
        logger.info(f"Parsed {len(entities)} entities from markdown tables")
        
        # Save debug output
        import time
        import json
        debug_path = f"/tmp/markdown_table_extraction_{int(time.time())}.json"
        try:
            with open(debug_path, 'w') as f:
                json.dump({
                    "entities": entities,
                    "extraction_metadata": {
                        "total_entities": len(entities),
                        "tables_found": "multiple"
                    }
                }, f, indent=2)
            logger.info(f"Table extraction result saved to: {debug_path}")
        except Exception as e:
            logger.warning(f"Could not save debug output: {e}")
        
        return {
            "entities": entities,
            "extraction_metadata": {
                "total_entities": len(entities),
                "parser_type": "deterministic"
            }
        }
    
    def _parse_html_tables(self, markdown: str, max_entities: int) -> List[Dict[str, Any]]:
        """Parse HTML tables from markdown using BeautifulSoup"""
        entities = []
        
        try:
            # Find all HTML tables
            soup = BeautifulSoup(markdown, 'html.parser')
            tables = soup.find_all('table')
            
            logger.info(f"Found {len(tables)} HTML tables in markdown")
            
            for table_idx, table in enumerate(tables):
                if len(entities) >= max_entities:
                    break
                
                # Extract table data
                table_entities = self._parse_single_html_table(table, table_idx)
                entities.extend(table_entities[:max_entities - len(entities)])
            
        except Exception as e:
            logger.error(f"Error parsing HTML tables: {e}")
        
        return entities
    
    def _parse_single_html_table(self, table, table_idx: int) -> List[Dict[str, Any]]:
        """Parse a single HTML table into entities"""
        entities = []
        
        try:
            # Extract headers (handle multi-row headers)
            headers = []
            all_rows = table.find_all('tr')
            
            # Try first 3 rows to find the best header row
            best_headers = []
            best_row_idx = 0
            
            for row_idx in range(min(3, len(all_rows))):
                row = all_rows[row_idx]
                row_headers = []
                
                for cell in row.find_all(['th', 'td']):
                    header_text = cell.get_text(strip=True)
                    cleaned = self._clean_header(header_text)
                    row_headers.append(cleaned)
                
                # Count non-empty headers
                non_empty = sum(1 for h in row_headers if h and h != 'column')
                
                logger.debug(f"  Row {row_idx}: {len(row_headers)} cells, {non_empty} non-empty headers")
                
                # Use the row with most non-empty headers
                if len(row_headers) > len(best_headers) or non_empty > sum(1 for h in best_headers if h and h != 'column'):
                    best_headers = row_headers
                    best_row_idx = row_idx
            
            headers = best_headers
            
            # Log the chosen header row
            for i, h in enumerate(headers[:15]):
                logger.debug(f"  Header[{i}]: '{h}'")
            
            if not headers:
                logger.warning(f"No headers found in table {table_idx}")
                return entities
            
            logger.info(f"Table {table_idx}: Found {len(headers)} columns (from row {best_row_idx})")
            logger.info(f"   Headers: {headers[:10]}{'...' if len(headers) > 10 else ''}")
            
            # Extract rows (skip header rows - start after the best header row)
            rows = table.find_all('tr')[best_row_idx + 1:]  # Skip all header rows
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all('td')
                if len(cells) < 2:  # Skip empty or malformed rows
                    continue
                
                # Skip rows that look like headers (all text, no numbers)
                cell_values = [cell.get_text(strip=True) for cell in cells]
                has_number = any(any(c.isdigit() for c in val) for val in cell_values)
                if not has_number and row_idx == 0:  # First data row should have numbers
                    logger.debug(f"Skipping header-like row: {cell_values[:3]}")
                    continue
                
                # Create entity from row
                entity = self._create_entity_from_row(
                    headers=headers,
                    cells=cells,
                    table_idx=table_idx,
                    row_idx=row_idx
                )
                
                if entity:
                    entities.append(entity)
        
        except Exception as e:
            logger.error(f"Error parsing HTML table {table_idx}: {e}")
        
        return entities
    
    def _create_entity_from_row(
        self,
        headers: List[str],
        cells: List[Any],
        table_idx: int,
        row_idx: int
    ) -> Optional[Dict[str, Any]]:
        """Create an entity dict from a table row"""
        
        try:
            # Extract cell values
            values = []
            for cell in cells:
                value = cell.get_text(strip=True)
                values.append(value)
            
            if not values or len(values) < 2:
                return None
            
            # Determine entity type and name from first few columns
            entity_type = "location"  # Default type
            entity_name = values[0] if values else f"Entity_{row_idx}"
            
            # Check if this looks like a location (city/county pattern)
            if len(values) >= 2:
                first_col = values[0].lower()
                if any(keyword in first_col for keyword in ["city", "town", "village", "municipality"]):
                    entity_type = "location"
                    entity_name = values[0]
                elif any(keyword in first_col for keyword in ["company", "corp", "inc", "llc"]):
                    entity_type = "company"
                    entity_name = values[0]
            
            # Build properties dict from all columns
            properties = {}
            
            # DEBUG: Log array lengths
            logger.debug(f"Row {row_idx}: {len(headers)} headers, {len(values)} values")
            
            # Handle length mismatch
            if len(headers) != len(values):
                logger.warning(f"Header/value mismatch: {len(headers)} headers vs {len(values)} values")
                # Pad shorter array with empty strings
                max_len = max(len(headers), len(values))
                headers = headers + [''] * (max_len - len(headers))
                values = values + [''] * (max_len - len(values))
            
            for i, (header, value) in enumerate(zip(headers, values)):
                if i == 0:  # First column is usually the name
                    # Still add city to properties for consistency
                    if header and value:
                        properties[header] = value
                    continue
                
                # Skip empty headers
                if not header or header.strip() == '':
                    logger.debug(f"  Skipping column {i}: empty header")
                    continue
                
                # Process ALL values, including strings like county names
                if value and value not in ["", "-", "N/A", "n/a"]:
                    # Try to convert to number if possible
                    clean_value = value.replace(',', '').replace('$', '').strip()
                    try:
                        # Try integer first
                        if '.' not in clean_value and any(c.isdigit() for c in clean_value):
                            properties[header] = int(clean_value)
                            logger.debug(f"{header}: {properties[header]} (int)")
                        elif '.' in clean_value:
                            properties[header] = float(clean_value)
                            logger.debug(f"{header}: {properties[header]} (float)")
                        else:
                            # Not a number, keep as string (e.g., county names)
                            properties[header] = value
                            logger.debug(f"{header}: {value} (string)")
                    except (ValueError, AttributeError):
                        # Keep as string
                        properties[header] = value
                        logger.debug(f"{header}: {value} (string)")
                else:
                    # Store empty/null values as None for non-numeric fields, 0 for numeric
                    properties[header] = None if header.lower() in ['county', 'state', 'country'] else 0
                    logger.debug(f"{header}: {properties[header]} (empty)")
            
            # Only create entity if it has meaningful properties
            if not properties:
                return None
            
            # Summary log at INFO level
            logger.info(f"Entity '{entity_name[:30]}': {len(properties)} properties extracted from {len(headers)} columns")
            
            return {
                "type": entity_type,
                "name": entity_name,
                "properties": properties,
                "source_reference": f"Table {table_idx + 1}, Row {row_idx + 1}"
            }
        
        except Exception as e:
            logger.debug(f"Could not create entity from row {row_idx}: {e}")
            return None
    
    def _clean_header(self, header: str) -> str:
        """Clean and normalize header text"""
        # Remove special characters, convert to snake_case
        cleaned = header.strip().lower()
        cleaned = re.sub(r'[^\w\s]', '', cleaned)
        cleaned = re.sub(r'\s+', '_', cleaned)
        return cleaned or "column"
    
    def _parse_pipe_tables(self, markdown: str, max_entities: int) -> List[Dict[str, Any]]:
        """Parse markdown pipe tables (| col1 | col2 | format)"""
        entities = []
        
        try:
            # Find pipe tables using regex
            # Pattern: lines starting with | and containing multiple |
            lines = markdown.split('\n')
            
            i = 0
            table_count = 0
            while i < len(lines) and len(entities) < max_entities:
                line = lines[i].strip()
                
                # Check if this is a table row
                if line.startswith('|') and line.count('|') >= 3:
                    # Extract table starting from this line
                    table_lines = []
                    while i < len(lines):
                        curr_line = lines[i].strip()
                        if curr_line.startswith('|'):
                            table_lines.append(curr_line)
                            i += 1
                        else:
                            break
                    
                    if len(table_lines) >= 2:  # At least header + 1 row
                        table_entities = self._parse_pipe_table_lines(table_lines, table_count)
                        entities.extend(table_entities[:max_entities - len(entities)])
                        table_count += 1
                else:
                    i += 1
        
        except Exception as e:
            logger.error(f"Error parsing pipe tables: {e}")
        
        return entities
    
    def _parse_pipe_table_lines(self, lines: List[str], table_idx: int) -> List[Dict[str, Any]]:
        """Parse a markdown pipe table"""
        entities = []
        
        try:
            # Extract headers from first line
            header_line = lines[0]
            headers = [self._clean_header(cell.strip()) for cell in header_line.split('|')[1:-1]]
            
            # Skip separator line if present (line with dashes)
            start_row = 1
            if len(lines) > 1 and '-' in lines[1]:
                start_row = 2
            
            # Extract data rows
            for row_idx, line in enumerate(lines[start_row:]):
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                
                if len(cells) != len(headers):
                    continue
                
                # Create entity
                entity = {
                    "type": "metric",  # Default for pipe tables
                    "name": cells[0] if cells else f"Item_{row_idx}",
                    "properties": {},
                    "source_reference": f"Pipe Table {table_idx + 1}, Row {row_idx + 1}"
                }
                
                for header, value in zip(headers[1:], cells[1:]):
                    if value and value not in ["", "-"]:
                        entity["properties"][header] = value
                
                if entity["properties"]:
                    entities.append(entity)
        
        except Exception as e:
            logger.error(f"Error parsing pipe table {table_idx}: {e}")
        
        return entities


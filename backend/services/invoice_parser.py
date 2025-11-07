"""
Deterministic invoice parser
Extracts structured data from invoice documents
"""
import re
import uuid
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from loguru import logger

from models.entity import Entity, EntityType
from models.citation import Citation


class InvoiceParser:
    """Parse invoices deterministically without LLM"""
    
    def __init__(self):
        pass
    
    def extract_entities_from_invoice(
        self,
        markdown: str,
        document_id: str,
        graph_id: str
    ) -> List[Entity]:
        """
        Extract entities from invoice markdown
        
        Returns:
            List of entities including:
            - Invoice (main document)
            - Vendor (company issuing invoice)
            - Customer (company receiving invoice)
            - LineItem entities (individual items)
        """
        logger.info("📋 Parsing invoice deterministically")
        
        soup = BeautifulSoup(markdown, 'html.parser')
        text = soup.get_text()
        
        entities = []
        
        # Extract invoice metadata
        invoice_data = self._extract_invoice_metadata(text, markdown)
        
        # Create Invoice entity
        invoice_entity = Entity(
            id=f"ent_{uuid.uuid4().hex[:12]}",
            type=EntityType.INVOICE,
            name=f"Invoice {invoice_data.get('invoice_number', 'Unknown')}",
            properties={
                "invoice_number": invoice_data.get("invoice_number"),
                "invoice_date": invoice_data.get("invoice_date"),
                "due_date": invoice_data.get("due_date"),
                "subtotal": invoice_data.get("subtotal"),
                "tax": invoice_data.get("tax"),
                "total": invoice_data.get("total"),
                "currency": invoice_data.get("currency", "USD"),
                "status": invoice_data.get("status", "pending")
            },
            citations=[Citation(page=1, section="Invoice Header")],
            document_id=document_id,
            graph_id=graph_id
        )
        entities.append(invoice_entity)
        
        # Extract vendor (bill from)
        vendor_data = self._extract_vendor(text)
        if vendor_data:
            vendor_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=EntityType.VENDOR,
                name=vendor_data.get("name", "Unknown Vendor"),
                properties={
                    "address": vendor_data.get("address"),
                    "phone": vendor_data.get("phone"),
                    "email": vendor_data.get("email"),
                    "tax_id": vendor_data.get("tax_id")
                },
                citations=[Citation(page=1, section="Vendor Information")],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(vendor_entity)
        
        # Extract customer (bill to)
        customer_data = self._extract_customer(text)
        if customer_data:
            customer_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=EntityType.COMPANY,
                name=customer_data.get("name", "Unknown Customer"),
                properties={
                    "address": customer_data.get("address"),
                    "phone": customer_data.get("phone"),
                    "email": customer_data.get("email")
                },
                citations=[Citation(page=1, section="Customer Information")],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(customer_entity)
        
        # Extract line items
        line_items = self._extract_line_items(soup, text)
        for idx, item in enumerate(line_items):
            item_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=EntityType.METRIC,  # Line items as metrics
                name=item.get("description", f"Line Item {idx+1}"),
                properties={
                    "description": item.get("description"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "amount": item.get("amount"),
                    "item_code": item.get("item_code"),
                    "category": "invoice_line_item"
                },
                citations=[Citation(page=1, section=f"Line Item {idx+1}")],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(item_entity)
        
        logger.info(f"✅ Extracted {len(entities)} entities from invoice")
        return entities
    
    def _extract_invoice_metadata(self, text: str, markdown: str) -> Dict[str, Any]:
        """Extract invoice number, dates, amounts"""
        data = {}
        
        # Invoice number
        patterns = [
            r'invoice\s*#?:?\s*([A-Z0-9\-]+)',
            r'inv\s*#?:?\s*([A-Z0-9\-]+)',
            r'invoice\s+number:?\s*([A-Z0-9\-]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["invoice_number"] = match.group(1)
                break
        
        # Invoice date
        date_patterns = [
            r'invoice\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'dated?:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["invoice_date"] = match.group(1)
                break
        
        # Due date
        due_patterns = [
            r'due\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'payment\s+due:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        for pattern in due_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["due_date"] = match.group(1)
                break
        
        # Amounts
        # Subtotal
        subtotal_match = re.search(r'sub\s*total:?\s*\$?\s*([\d,]+\.?\d{0,2})', text, re.IGNORECASE)
        if subtotal_match:
            data["subtotal"] = float(subtotal_match.group(1).replace(',', ''))
        
        # Tax
        tax_match = re.search(r'tax:?\s*\$?\s*([\d,]+\.?\d{0,2})', text, re.IGNORECASE)
        if tax_match:
            data["tax"] = float(tax_match.group(1).replace(',', ''))
        
        # Total
        total_patterns = [
            r'total\s+(?:amount\s+)?due:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'(?:grand\s+)?total:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'amount\s+due:?\s*\$?\s*([\d,]+\.?\d{0,2})'
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["total"] = float(match.group(1).replace(',', ''))
                break
        
        return data
    
    def _extract_vendor(self, text: str) -> Dict[str, Any]:
        """Extract vendor/seller information"""
        vendor = {}
        
        # Look for "From:", "Vendor:", "Seller:", etc.
        patterns = [
            r'(?:from|vendor|seller|billed?\s+from):?\s*([^\n]+)',
            r'([A-Z][A-Za-z\s&,\.]+(?:Inc|LLC|Ltd|Corp|Company))'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                vendor["name"] = match.group(1).strip()
                break
        
        # Extract contact info near vendor name
        if vendor.get("name"):
            # Look for address
            address_match = re.search(r'(\d+\s+[A-Za-z\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)[^\n]*)', text, re.IGNORECASE)
            if address_match:
                vendor["address"] = address_match.group(1).strip()
            
            # Phone
            phone_match = re.search(r'(?:phone|tel|phone):?\s*([\d\-\(\)\s]+)', text, re.IGNORECASE)
            if phone_match:
                vendor["phone"] = phone_match.group(1).strip()
            
            # Email
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
            if email_match:
                vendor["email"] = email_match.group(1)
        
        return vendor if vendor else None
    
    def _extract_customer(self, text: str) -> Dict[str, Any]:
        """Extract customer/buyer information"""
        customer = {}
        
        # Look for "Bill To:", "Customer:", "Buyer:", etc.
        patterns = [
            r'(?:bill\s+to|customer|buyer|sold\s+to):?\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                customer["name"] = match.group(1).strip()
                break
        
        return customer if customer else None
    
    def _extract_line_items(self, soup: BeautifulSoup, text: str) -> List[Dict[str, Any]]:
        """Extract line items from table or text"""
        line_items = []
        
        # Try to find line items in table
        tables = soup.find_all('table')
        for table in tables:
            # Look for table with columns: description, quantity, price, amount
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Check if this looks like a line items table
            header_row = rows[0]
            headers = [cell.get_text(strip=True).lower() for cell in header_row.find_all(['th', 'td'])]
            
            # Check for line item indicators
            if any(h in headers for h in ['description', 'item', 'qty', 'quantity', 'price', 'amount']):
                # This is a line items table
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        item = {}
                        
                        # Map cells to fields based on position
                        for idx, cell in enumerate(cells):
                            cell_text = cell.get_text(strip=True)
                            if idx < len(headers):
                                header = headers[idx]
                                if 'desc' in header or 'item' in header:
                                    item['description'] = cell_text
                                elif 'qty' in header or 'quantity' in header:
                                    try:
                                        item['quantity'] = int(re.sub(r'[^\d]', '', cell_text))
                                    except:
                                        item['quantity'] = cell_text
                                elif 'price' in header or 'rate' in header:
                                    try:
                                        item['unit_price'] = float(re.sub(r'[^\d\.]', '', cell_text))
                                    except:
                                        item['unit_price'] = cell_text
                                elif 'amount' in header or 'total' in header:
                                    try:
                                        item['amount'] = float(re.sub(r'[^\d\.]', '', cell_text))
                                    except:
                                        item['amount'] = cell_text
                        
                        if item.get('description'):
                            line_items.append(item)
        
        # If no table found, try to extract from text
        if not line_items:
            # Look for pattern: item name ... quantity ... price
            pattern = r'([A-Za-z\s\-]+)\s+(\d+)\s+\$?([\d,]+\.?\d{0,2})\s+\$?([\d,]+\.?\d{0,2})'
            for match in re.finditer(pattern, text):
                line_items.append({
                    'description': match.group(1).strip(),
                    'quantity': int(match.group(2)),
                    'unit_price': float(match.group(3).replace(',', '')),
                    'amount': float(match.group(4).replace(',', ''))
                })
        
        return line_items


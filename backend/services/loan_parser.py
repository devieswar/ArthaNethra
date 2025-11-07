"""
Deterministic loan agreement parser
Extracts loan terms, parties, rates, covenants, and maturity dates
"""
import re
import uuid
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from loguru import logger

from models.entity import Entity, EntityType
from models.citation import Citation


class LoanParser:
    """Parse loan agreements deterministically"""
    
    def __init__(self):
        pass
    
    def extract_entities_from_loan(
        self,
        markdown: str,
        document_id: str,
        graph_id: str
    ) -> List[Entity]:
        """
        Extract entities from loan agreement markdown
        
        Returns:
            List of entities including:
            - Loan (main instrument)
            - Lender (financial institution)
            - Borrower (company/person)
            - Covenant entities (loan conditions)
        """
        logger.info("💰 Parsing loan agreement deterministically")
        
        soup = BeautifulSoup(markdown, 'html.parser')
        text = soup.get_text()
        
        entities = []
        
        # Extract loan metadata
        loan_data = self._extract_loan_metadata(text)
        
        # Create Loan entity
        loan_entity = Entity(
            id=f"ent_{uuid.uuid4().hex[:12]}",
            type=EntityType.LOAN,
            name=f"Loan {loan_data.get('loan_number', loan_data.get('borrower', 'Agreement'))}",
            properties={
                "loan_number": loan_data.get("loan_number"),
                "loan_type": loan_data.get("loan_type"),
                "principal_amount": loan_data.get("principal_amount"),
                "currency": loan_data.get("currency", "USD"),
                "interest_rate": loan_data.get("interest_rate"),
                "rate_type": loan_data.get("rate_type"),  # "fixed" or "variable"
                "term_months": loan_data.get("term_months"),
                "origination_date": loan_data.get("origination_date"),
                "maturity_date": loan_data.get("maturity_date"),
                "payment_frequency": loan_data.get("payment_frequency"),
                "collateral": loan_data.get("collateral"),
                "purpose": loan_data.get("purpose")
            },
            citations=[Citation(page=1, section="Loan Terms")],
            document_id=document_id,
            graph_id=graph_id
        )
        entities.append(loan_entity)
        
        # Extract lender
        lender_data = self._extract_lender(text)
        if lender_data:
            lender_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=EntityType.COMPANY,
                name=lender_data.get("name", "Lender"),
                properties={
                    "role": "lender",
                    "address": lender_data.get("address"),
                    "contact": lender_data.get("contact")
                },
                citations=[Citation(page=1, section="Lender Information")],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(lender_entity)
        
        # Extract borrower
        borrower_data = self._extract_borrower(text)
        if borrower_data:
            borrower_type = EntityType.COMPANY if any(word in borrower_data.get("name", "").upper() for word in ["INC", "LLC", "CORP", "LTD"]) else EntityType.PERSON
            
            borrower_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=borrower_type,
                name=borrower_data.get("name", "Borrower"),
                properties={
                    "role": "borrower",
                    "address": borrower_data.get("address"),
                    "credit_score": borrower_data.get("credit_score")
                },
                citations=[Citation(page=1, section="Borrower Information")],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(borrower_entity)
        
        # Extract covenants (loan conditions)
        covenants = self._extract_covenants(text)
        for idx, covenant in enumerate(covenants):
            covenant_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=EntityType.CLAUSE,
                name=covenant.get("title", f"Covenant {idx+1}"),
                properties={
                    "covenant_type": covenant.get("covenant_type"),
                    "description": covenant.get("description"),
                    "threshold": covenant.get("threshold"),
                    "measurement_frequency": covenant.get("frequency")
                },
                citations=[Citation(page=1, section="Covenants")],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(covenant_entity)
        
        # Extract fees
        fees = self._extract_fees(text)
        for fee in fees:
            fee_entity = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                type=EntityType.METRIC,
                name=fee.get("name", "Fee"),
                properties={
                    "fee_type": fee.get("fee_type"),
                    "amount": fee.get("amount"),
                    "percentage": fee.get("percentage"),
                    "when_due": fee.get("when_due")
                },
                citations=[Citation(page=1, section="Fees")],
                document_id=document_id,
                graph_id=graph_id
            )
            entities.append(fee_entity)
        
        logger.info(f"✅ Extracted {len(entities)} entities from loan agreement")
        return entities
    
    def _extract_loan_metadata(self, text: str) -> Dict[str, Any]:
        """Extract core loan terms"""
        data = {}
        
        # Loan number/ID
        loan_num_patterns = [
            r'loan\s*#?:?\s*([A-Z0-9\-]+)',
            r'loan\s+number:?\s*([A-Z0-9\-]+)',
            r'facility\s+number:?\s*([A-Z0-9\-]+)'
        ]
        for pattern in loan_num_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["loan_number"] = match.group(1)
                break
        
        # Loan type
        types = ["term loan", "revolving credit", "line of credit", "mortgage", "bridge loan"]
        for loan_type in types:
            if loan_type in text.lower():
                data["loan_type"] = loan_type
                break
        
        # Principal amount
        principal_patterns = [
            r'principal\s+amount:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'loan\s+amount:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'(?:sum|amount)\s+of\s+\$?\s*([\d,]+\.?\d{0,2})'
        ]
        for pattern in principal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                data["principal_amount"] = float(amount_str)
                break
        
        # Interest rate
        rate_patterns = [
            r'interest\s+rate:?\s*([\d\.]+)\s*%',
            r'at\s+(?:a\s+rate\s+of\s+)?([\d\.]+)\s*%',
            r'apr:?\s*([\d\.]+)\s*%'
        ]
        for pattern in rate_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["interest_rate"] = float(match.group(1))
                break
        
        # Rate type (fixed or variable)
        if "fixed rate" in text.lower() or "fixed interest" in text.lower():
            data["rate_type"] = "fixed"
        elif "variable rate" in text.lower() or "adjustable" in text.lower() or "floating" in text.lower():
            data["rate_type"] = "variable"
        
        # Term
        term_patterns = [
            r'term\s+of\s+(\d+)\s+(year|month)s?',
            r'(?:for|over)\s+a\s+period\s+of\s+(\d+)\s+(year|month)s?',
            r'(\d+)[- ](?:year|month)\s+(?:term|loan)'
        ]
        for pattern in term_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = int(match.group(1))
                unit = match.group(2).lower()
                data["term_months"] = amount * 12 if unit == "year" else amount
                break
        
        # Origination date
        orig_patterns = [
            r'dated\s+(?:as\s+of\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'origination\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'effective\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        for pattern in orig_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["origination_date"] = match.group(1)
                break
        
        # Maturity date
        maturity_patterns = [
            r'maturity\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'due\s+(?:on|date):?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'final\s+payment\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        for pattern in maturity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["maturity_date"] = match.group(1)
                break
        
        # Payment frequency
        if "monthly" in text.lower():
            data["payment_frequency"] = "monthly"
        elif "quarterly" in text.lower():
            data["payment_frequency"] = "quarterly"
        elif "annually" in text.lower():
            data["payment_frequency"] = "annually"
        
        # Collateral
        collateral_match = re.search(r'(?:secured\s+by|collateral|security):?\s*([^\.\n]+)', text, re.IGNORECASE)
        if collateral_match:
            data["collateral"] = collateral_match.group(1).strip()
        
        # Purpose
        purpose_match = re.search(r'purpose:?\s*([^\.\n]+)', text, re.IGNORECASE)
        if purpose_match:
            data["purpose"] = purpose_match.group(1).strip()
        
        return data
    
    def _extract_lender(self, text: str) -> Dict[str, Any]:
        """Extract lender information"""
        lender = {}
        
        # Look for "Lender:"
        lender_match = re.search(r'lender:?\s*([^\n]+)', text, re.IGNORECASE)
        if lender_match:
            lender["name"] = lender_match.group(1).strip()
        
        return lender if lender else None
    
    def _extract_borrower(self, text: str) -> Dict[str, Any]:
        """Extract borrower information"""
        borrower = {}
        
        # Look for "Borrower:"
        borrower_match = re.search(r'borrower:?\s*([^\n]+)', text, re.IGNORECASE)
        if borrower_match:
            borrower["name"] = borrower_match.group(1).strip()
        
        return borrower if borrower else None
    
    def _extract_covenants(self, text: str) -> List[Dict[str, Any]]:
        """Extract loan covenants"""
        covenants = []
        
        # Common covenant types
        covenant_patterns = [
            (r'debt[- ]to[- ]equity\s+ratio[^\d]*([\d\.]+)', "debt_to_equity_ratio"),
            (r'minimum\s+(?:net\s+)?(?:working\s+)?capital[^\d]*\$?\s*([\d,]+)', "minimum_capital"),
            (r'debt\s+service\s+coverage\s+ratio[^\d]*([\d\.]+)', "debt_service_coverage"),
            (r'leverage\s+ratio[^\d]*([\d\.]+)', "leverage_ratio"),
            (r'interest\s+coverage\s+ratio[^\d]*([\d\.]+)', "interest_coverage")
        ]
        
        for pattern, covenant_type in covenant_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                threshold = match.group(1).replace(',', '')
                covenants.append({
                    "title": covenant_type.replace('_', ' ').title(),
                    "covenant_type": covenant_type,
                    "threshold": float(threshold) if '.' in threshold else int(threshold),
                    "description": f"Must maintain {covenant_type.replace('_', ' ')} of {threshold}"
                })
        
        # Look for "shall maintain" or "shall not exceed" clauses
        maintain_pattern = r'(?:borrower|company)\s+shall\s+(?:maintain|not\s+exceed)\s+([^\.]+)\.'
        for match in re.finditer(maintain_pattern, text, re.IGNORECASE):
            covenant_text = match.group(1).strip()
            covenants.append({
                "title": "Financial Covenant",
                "covenant_type": "general",
                "description": covenant_text
            })
            
            if len(covenants) >= 10:
                break
        
        return covenants
    
    def _extract_fees(self, text: str) -> List[Dict[str, Any]]:
        """Extract loan fees"""
        fees = []
        
        # Fee patterns
        fee_patterns = [
            (r'origination\s+fee:?\s*\$?\s*([\d,]+\.?\d{0,2})', "origination_fee"),
            (r'processing\s+fee:?\s*\$?\s*([\d,]+\.?\d{0,2})', "processing_fee"),
            (r'late\s+(?:payment\s+)?fee:?\s*\$?\s*([\d,]+\.?\d{0,2})', "late_fee"),
            (r'prepayment\s+penalty:?\s*\$?\s*([\d,]+\.?\d{0,2})', "prepayment_penalty"),
            (r'commitment\s+fee:?\s*([\d\.]+)\s*%', "commitment_fee")
        ]
        
        for pattern, fee_type in fee_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                if '%' in pattern:
                    fees.append({
                        "name": fee_type.replace('_', ' ').title(),
                        "fee_type": fee_type,
                        "percentage": float(amount_str)
                    })
                else:
                    fees.append({
                        "name": fee_type.replace('_', ' ').title(),
                        "fee_type": fee_type,
                        "amount": float(amount_str)
                    })
        
        return fees


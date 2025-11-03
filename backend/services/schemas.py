"""
Financial domain schema presets for ADE Extract.
These are JSON Schemas designed to capture rich financial data from markdown
produced by ADE Parse.
"""

financial_basic = {
    "type": "object",
    "title": "Financial Report Extraction",
    "properties": {
        "company_info": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Official company name"},
                "ticker": {"type": "string", "description": "Ticker symbol if present"},
                "report_type": {"type": "string", "description": "10-K, 10-Q, annual report, etc."},
                "fiscal_year": {"type": "string", "description": "Fiscal year or period"}
            },
            "required": ["company_name"],
            "description": "High-level identity of the issuer"
        },
        "report_info": {
            "type": "object",
            "properties": {
                "filing_date": {"type": "string"},
                "period_end": {"type": "string"},
                "auditor": {"type": "string"}
            }
        },
        "loans": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "lender": {"type": "string"},
                    "instrument": {"type": "string", "description": "Term loan, revolver, notes, etc."},
                    "principal": {"type": "string"},
                    "rate": {"type": "string"},
                    "maturity": {"type": "string"},
                    "covenants": {"type": "string", "description": "Key financial covenants if present"}
                }
            },
            "description": "Debt instruments and key terms"
        },
        "metrics": {
            "type": "object",
            "properties": {
                "revenue": {"type": "string"},
                "ebitda": {"type": "string"},
                "net_income": {"type": "string"},
                "debt_ratio": {"type": "string"},
                "cash_flow": {"type": "string"}
            },
            "description": "Key financial metrics if explicitly present"
        },
        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "risk_title": {"type": "string"},
                    "description": {"type": "string"}
                }
            },
            "description": "Risk factors summarized from the document"
        },
        "summary": {"type": "string", "description": "Executive summary"}
    },
    "required": ["company_info"],
}

invoice_basic = {
    "type": "object",
    "title": "Invoice Extraction",
    "properties": {
        "seller": {"type": "string"},
        "buyer": {"type": "string"},
        "invoice_number": {"type": "string"},
        "invoice_date": {"type": "string"},
        "due_date": {"type": "string"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "string"},
                    "unit_price": {"type": "string"},
                    "amount": {"type": "string"}
                }
            }
        },
        "total": {"type": "string"}
    },
    "required": ["seller", "buyer", "invoice_number"],
}

presets = {
    "financial_basic": financial_basic,
    "invoice_basic": invoice_basic,
}



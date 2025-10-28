# 🔌 ArthaNethra — API Documentation

## Base URL
```
Local Development: http://localhost:8000
Production: https://api.arthanethra.com
```

---

## Authentication
*(Optional for MVP, will be added in future)*

```http
Authorization: Bearer <jwt_token>
```

---

## Endpoints

### 1. Document Ingestion

#### Upload Document
```http
POST /api/v1/ingest
Content-Type: multipart/form-data
```

**Request:**
```python
files = {"file": open("10K_2025.pdf", "rb")}
```

**Response:**
```json
{
  "document_id": "doc_abc123",
  "filename": "10K_2025.pdf",
  "size": 2048576,
  "status": "pending",
  "uploaded_at": "2025-01-15T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request` — Invalid file format
- `413 Payload Too Large` — File exceeds 100MB limit
- `500 Internal Server Error` — Server error

---

### 2. Document Extraction

#### Extract with ADE
```http
POST /api/v1/extract
Content-Type: application/json
```

**Request:**
```json
{
  "document_id": "doc_abc123",
  "schema": "financial_entities"
}
```

**Response:**
```json
{
  "extraction_id": "ext_xyz789",
  "document_id": "doc_abc123",
  "status": "completed",
  "entities_count": 156,
  "extracted_at": "2025-01-15T10:32:00Z",
  "ade_output": {
    "entities": [
      {
        "type": "Company",
        "name": "ACME Corporation",
        "page": 47,
        "attributes": {
          "industry": "Technology",
          "fiscal_year": 2025
        },
        "citations": [
          {"page": 47, "section": "Business Overview", "cell": null}
        ]
      },
      {
        "type": "Loan",
        "name": "Variable Rate Credit Facility",
        "page": 89,
        "attributes": {
          "bank": "Bank of America",
          "principal": 50000000,
          "rate": 0.0875,
          "maturity": "2030-01-15"
        },
        "citations": [
          {"page": 89, "section": "Note 8: Debt", "table_id": "T3.2.1", "cell": "B5"}
        ]
      }
    ],
    "metadata": {
      "total_pages": 247,
      "confidence_score": 0.94
    }
  }
}
```

**Error Responses:**
- `404 Not Found` — Document ID not found
- `500 Internal Server Error` — ADE API error

---

### 3. Graph Normalization

#### Convert ADE Output to Graph
```http
POST /api/v1/normalize
Content-Type: application/json
```

**Request:**
```json
{
  "extraction_id": "ext_xyz789",
  "mapping_config": {
    "entity_types": ["Company", "Subsidiary", "Loan", "Invoice", "Metric"],
    "relationship_types": ["HAS_LOAN", "OWNS", "PARTY_TO", "HAS_METRIC"]
  }
}
```

**Response:**
```json
{
  "graph_id": "graph_123",
  "entities": [
    {
      "id": "ent_1",
      "type": "Company",
      "name": "ACME Corporation",
      "properties": {
        "industry": "Technology",
        "fiscal_year": 2025
      },
      "citations": [
        {"page": 47, "section": "Business Overview"}
      ],
      "embedding": [...]
    },
    {
      "id": "ent_2",
      "type": "Loan",
      "name": "Variable Rate Credit Facility",
      "properties": {
        "bank": "Bank of America",
        "principal": 50000000,
        "rate": 0.0875
      },
      "citations": [
        {"page": 89, "section": "Note 8: Debt", "table_id": "T3.2.1"}
      ],
      "embedding": [...]
    }
  ],
  "edges": [
    {
      "id": "edge_1",
      "source": "ent_1",
      "target": "ent_2",
      "type": "HAS_LOAN",
      "properties": {
        "created_at": "2025-01-15T10:35:00Z"
      }
    }
  ]
}
```

---

### 4. Graph Indexing

#### Index Entities in Weaviate/Neo4j
```http
POST /api/v1/index
Content-Type: application/json
```

**Request:**
```json
{
  "graph_id": "graph_123",
  "index_weaviate": true,
  "index_neo4j": true
}
```

**Response:**
```json
{
  "indexed_at": "2025-01-15T10:36:00Z",
  "weaviate": {
    "entities_count": 156,
    "collection_name": "financial_entities_2025_01_15"
  },
  "neo4j": {
    "nodes_count": 156,
    "relationships_count": 234,
    "transaction_id": "tx_abc123"
  }
}
```

---

### 5. Risk Detection

#### Run Risk Analysis
```http
POST /api/v1/risk
Content-Type: application/json
```

**Request:**
```json
{
  "graph_id": "graph_123",
  "rules": [
    {
      "name": "high_variable_rate",
      "condition": "loan.rate > 0.08",
      "severity": "high"
    },
    {
      "name": "missing_covenant",
      "condition": "NOT EXISTS covenant_clause",
      "severity": "medium"
    }
  ]
}
```

**Response:**
```json
{
  "risk_report": {
    "total_risks": 5,
    "high_severity": 2,
    "medium_severity": 3,
    "low_severity": 0,
    "risks": [
      {
        "id": "risk_1",
        "type": "Interest Rate Risk",
        "severity": "high",
        "description": "Variable-rate debt exceeds 8% threshold",
        "affected_entities": [
          {"id": "ent_2", "name": "Variable Rate Credit Facility"}
        ],
        "evidence": [
          {"entity_id": "ent_2", "citation": {"page": 89, "section": "Note 8: Debt"}}
        ]
      }
    ]
  },
  "generated_at": "2025-01-15T10:37:00Z"
}
```

---

### 6. Chatbot Query

#### Ask the AI Bot
```http
POST /api/v1/ask
Content-Type: application/json
```

**Request:**
```json
{
  "message": "Show me all subsidiaries with variable-rate debt above 8%",
  "context": {
    "graph_id": "graph_123",
    "include_evidence": true
  }
}
```

**Response (Streaming):**
```json
{
  "response": "Found 3 subsidiaries with high variable-rate exposure:\n1. ACME Europe Ltd. → $25M at 8.75% (Risk: HIGH)\n2. TechCorp Inc. → $12M at 9.2% (Risk: HIGH)\n3. GlobalTech Asia → $8M at 8.3% (Risk: MEDIUM)",
  "citations": [
    {
      "type": "entity",
      "id": "ent_5",
      "name": "ACME Europe Ltd.",
      "citation": {"page": 134, "section": "Subsidiaries"}
    },
    {
      "type": "entity",
      "id": "ent_6",
      "name": "TechCorp Inc.",
      "citation": {"page": 189, "section": "Subsidiaries"}
    }
  ],
  "subgraph": {
    "nodes": [
      {"id": "ent_5", "name": "ACME Europe Ltd."},
      {"id": "ent_6", "name": "TechCorp Inc."},
      {"id": "ent_7", "name": "GlobalTech Asia"}
    ],
    "edges": [
      {"source": "ent_5", "target": "loan_1", "type": "HAS_LOAN"},
      {"source": "ent_6", "target": "loan_2", "type": "HAS_LOAN"}
    ]
  },
  "query_timestamp": "2025-01-15T10:40:00Z"
}
```

**Streaming Response Format:**
```
data: {"chunk": "Found", "timestamp": "..."}
data: {"chunk": " 3 subsidiaries", "timestamp": "..."}
data: {"chunk": " with high", "timestamp": "..."}
...
data: {"done": true}
```

---

### 7. Evidence Viewer

#### Serve PDF with Highlights
```http
GET /api/v1/evidence/{document_id}?page={page}&highlight={entity_id}
```

**Request:**
```
GET /api/v1/evidence/doc_abc123?page=89&highlight=ent_2
```

**Response:**
- Returns PDF byte stream with highlights
- Content-Type: `application/pdf`
- Highlights specified entity on the requested page

**Error Responses:**
- `404 Not Found` — Document or page not found
- `400 Bad Request` — Invalid page number

---

### 8. Graph Query

#### Query the Knowledge Graph
```http
POST /api/v1/graph/query
Content-Type: application/json
```

**Request:**
```json
{
  "graph_id": "graph_123",
  "query": {
    "type": "semantic",
    "search_text": "variable rate debt",
    "filters": {
      "entity_types": ["Loan"],
      "rate_threshold": 0.08
    },
    "limit": 10
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "entity_id": "ent_2",
      "name": "Variable Rate Credit Facility",
      "similarity_score": 0.94,
      "citations": [
        {"page": 89, "section": "Note 8: Debt"}
      ]
    }
  ],
  "total_results": 10
}
```

---

## Data Models

### Entity
```typescript
interface Entity {
  id: string;
  type: "Company" | "Subsidiary" | "Loan" | "Invoice" | "Metric" | "Clause";
  name: string;
  properties: Record<string, any>;
  citations: Citation[];
  embedding: number[];
  created_at: string;
  updated_at: string;
}
```

### Edge
```typescript
interface Edge {
  id: string;
  source: string;
  target: string;
  type: "HAS_LOAN" | "OWNS" | "PARTY_TO" | "HAS_METRIC" | "CONTAINS";
  properties: Record<string, any>;
  created_at: string;
}
```

### Citation
```typescript
interface Citation {
  page: number;
  section?: string;
  table_id?: string;
  cell?: string;
  clause?: string;
}
```

### Risk
```typescript
interface Risk {
  id: string;
  type: string;
  severity: "low" | "medium" | "high";
  description: string;
  affected_entities: Entity[];
  evidence: Citation[];
}
```

---

## Error Handling

All endpoints follow REST conventions:
- `200 OK` — Success
- `201 Created` — Resource created
- `400 Bad Request` — Invalid input
- `401 Unauthorized` — Missing/invalid auth
- `404 Not Found` — Resource not found
- `500 Internal Server Error` — Server error

**Error Response Format:**
```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Document with ID doc_abc123 not found",
    "timestamp": "2025-01-15T10:45:00Z"
  }
}
```

---

## Rate Limiting

*(To be implemented in production)*

- `/api/v1/ask`: 60 requests/minute
- `/api/v1/extract`: 10 requests/minute
- All other endpoints: 120 requests/minute

**Rate Limit Response:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

---

## SDK Examples

### Python
```python
import requests

BASE_URL = "http://localhost:8000"

# Upload document
with open("10K_2025.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/api/v1/ingest",
        files={"file": f}
    )
    doc_id = response.json()["document_id"]

# Extract with ADE
response = requests.post(
    f"{BASE_URL}/api/v1/extract",
    json={"document_id": doc_id}
)
extraction = response.json()["ade_output"]

# Chat
response = requests.post(
    f"{BASE_URL}/api/v1/ask",
    json={
        "message": "What are the risks?",
        "context": {"graph_id": "graph_123"}
    }
)
print(response.json()["response"])
```

### JavaScript
```javascript
const BASE_URL = "http://localhost:8000";

// Upload document
const formData = new FormData();
formData.append("file", fileInput.files[0]);

const uploadResponse = await fetch(`${BASE_URL}/api/v1/ingest`, {
  method: "POST",
  body: formData
});
const { document_id } = await uploadResponse.json();

// Chat (streaming)
const response = await fetch(`${BASE_URL}/api/v1/ask`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: "Show me all high-risk entities",
    context: { graph_id: "graph_123" }
  })
});

// Handle streaming response
const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = new TextDecoder().decode(value);
  console.log(chunk);
}
```

---

## WebSocket (Future)

Real-time graph updates via WebSocket:

```http
ws://localhost:8000/ws/graph/{graph_id}
```

**Message Format:**
```json
{
  "type": "graph_update",
  "event": "node_added",
  "data": {
    "entity_id": "ent_3",
    "name": "New Loan",
    "properties": {...}
  }
}
```

---

## Migration Guide

### v1 → v2 (Future)
- Add auth headers to all endpoints
- `/api/v1/` prefix becomes `/api/v2/`
- Enhanced citation format with coordinates

---

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/arthanethra/issues)
- **Email:** support@arthanethra.com
- **Docs:** https://docs.arthanethra.com


# 🔄 ArthaNethra — Complete Workflow Documentation

## Overview

This document details the complete workflow from file upload to knowledge graph visualization and AI-powered risk detection.

---

## 📊 High-Level Pipeline

```
Upload → Extract → Normalize → Index → Risk Detection → Chat Analysis
  ↓        ↓          ↓          ↓           ↓              ↓
Ingest   ADE      Graph      Vector      Rules+AI    Interactive
         Parse    Entities   Search      Detection   Q&A
```

---

## 🔍 Detailed Workflow

### 1️⃣ **Document Ingestion** (`POST /api/v1/ingest`)

**Service:** `IngestionService`

#### Steps:
1. **File Validation**
   - Check MIME type against allowed types
   - Validate file size (max 100MB)
   - Generate unique document ID: `doc_abc123...`

2. **Storage**
   - Save file to `backend/uploads/doc_{id}.{ext}`
   - Create `Document` object with metadata
   - Status: `UPLOADED`

#### Supported File Types:
- **Documents:** PDF, DOC, DOCX, PPT, PPTX, ODT, ODP
- **Images:** JPEG, PNG
- **Archives:** ZIP (processed recursively)
- **Spreadsheets:** XLS, XLSX, CSV

#### Response:
```json
{
  "id": "doc_abc123",
  "filename": "10K_2025.pdf",
  "file_path": "./uploads/doc_abc123.pdf",
  "file_size": 5242880,
  "mime_type": "application/pdf",
  "status": "uploaded",
  "uploaded_at": "2025-01-15T10:30:00Z"
}
```

---

### 2️⃣ **Document Extraction** (`POST /api/v1/extract`)

**Service:** `ExtractionService`  
**External API:** LandingAI ADE

#### Routing Logic:
```
Is ZIP? → Yes → Extract files → Process each in parallel
           ↓
          No → Check file size
                       ↓
                  > 15MB → Async Jobs API
                       ↓
                  ≤ 15MB → Synchronous Parse+Extract
```

#### ADE Parse Flow (Synchronous - ≤ 15MB):

**Endpoint:** `POST https://api.va.landing.ai/v1/ade/parse`

1. **Parse Request**
   - Upload binary file to LandingAI
   - **Retry:** 2 attempts with exponential backoff
   - Receive markdown + metadata

2. **Extract Request**
   - Use markdown from Parse step
   - Apply schema (financial_basic, invoice_basic, or custom)
   - **Retry:** 2 attempts with exponential backoff
   - Receive structured extraction

3. **Fallback**
   - If Extract fails → return Parse-only output
   - Preserve markdown for downstream processing

#### ADE Jobs Flow (Asynchronous - > 15MB or ZIP):

**Endpoints:**
- Submit: `POST /v1/ade/parse/jobs`
- Status: `GET /v1/ade/jobs/{job_id}`

1. **Submit Job**
   - Upload file with `split=page` option
   - Receive `job_id`
   - **Retry:** 2 attempts

2. **Poll Status**
   - Initial delay: 1.0s
   - Exponential backoff: 1.5x per poll (max 8.0s)
   - Max attempts: 60 (~1-2 minutes)
   - Check status: `completed`, `succeeded`, `success`

3. **Extract**
   - Run Extract on completed Parse markdown
   - Merge results

#### ZIP Handling:

For ZIP archives:
- Extract all supported files
- Process each file in parallel via `asyncio.gather()`
- Track progress per file
- Aggregate all results into single response

#### Retry/Backoff Strategy:

**Retryable Errors:**
- Connection errors
- 408 Request Timeout
- 409 Conflict
- 429 Rate Limit
- ≥500 Server errors

**Non-Retryable (fail immediately):**
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 422 Unprocessable Entity

**Backoff Schedule:**
- Attempt 1: 0.5s
- Attempt 2: 1.0s
- Attempt 3: 2.0s (max)
- Capped at 8.0s

#### Output:
```json
{
  "extraction_id": "ext_xyz789",
  "document_id": "doc_abc123",
  "status": "completed",
  "entities_count": 42,
  "ade_output": {
    "entities": [...],
    "tables": [...],
    "key_values": [...],
    "metadata": {
      "total_pages": 47,
      "confidence_score": 0.95,
      "extraction_id": "ext_xyz789"
    }
  }
}
```

#### Document Update:
- `status` → `EXTRACTED`
- `ade_output` → stored
- `extraction_id` → stored
- `total_pages` → stored
- `confidence_score` → stored

---

### 3️⃣ **Normalization** (`POST /api/v1/normalize`)

**Service:** `NormalizationService`

#### Process:
1. **Input:** ADE output (entities, tables, key_values)
2. **Extract Entities**
   - Parse `key_values` from Extract schema
   - Identify: Company, Loan, Metric, Risk, etc.
3. **Create Graph**
   - Generate entity nodes (Company, Subsidiary, Instrument, etc.)
   - Create edges (HAS_LOAN, OWNS, PARTY_TO, etc.)
   - Assign `graph_id`
4. **Store**
   - Add to `graphs_store`
   - Update `Document`: status → `NORMALIZED`

#### Output:
```json
{
  "graph_id": "graph_def456",
  "entities": [
    {
      "id": "entity_1",
      "type": "Company",
      "name": "ACME Corp",
      "properties": {...},
      "citations": [{"page": 47, "section": "Part I"}]
    }
  ],
  "edges": [
    {
      "id": "edge_1",
      "source": "entity_1",
      "target": "entity_2",
      "relation": "HAS_LOAN",
      "properties": {...}
    }
  ]
}
```

---

### 4️⃣ **Indexing** (`POST /api/v1/index`)

**Service:** `IndexingService`

#### Vector DB (Weaviate):
- Embed entities with text embeddings
- Store for semantic search
- Cross-reference capabilities

#### Graph DB (Neo4j):
- Store node/edge structure
- Enable complex Cypher queries
- Relationship traversal

#### Update:
- Document status → `INDEXED`
- Entity/edge counts stored

---

### 5️⃣ **Risk Detection** (`POST /api/v1/risk`)

**Service:** `RiskDetectionService`

#### Methods:
1. **Rule-Based**
   - High debt ratio detection
   - Missing covenant checks
   - Metric thresholds

2. **AI-Enhanced** (TODO)
   - LLM-based anomaly detection
   - Contextual risk assessment

#### Output:
```json
{
  "risk_report": {
    "total_risks": 3,
    "high_severity": 1,
    "medium_severity": 2,
    "risks": [
      {
        "type": "HIGH_DEBT_RATIO",
        "severity": "high",
        "description": "Debt-to-equity ratio exceeds 2.0",
        "entities": ["entity_1"],
        "evidence": [...]
      }
    ]
  }
}
```

---

### 6️⃣ **Interactive Analysis** (`POST /api/v1/ask`)

**Service:** `ChatbotService`  
**LLM:** AWS Bedrock (Claude 3 Sonnet)

#### Workflow:
1. **User Query** → "Show me all loans for ACME Corp"
2. **Tool Selection**
   - `graph_query`: Semantic search over entities
   - `doc_lookup`: Evidence retrieval
   - `metric_compute`: Calculate metrics
3. **LLM Reasoning**
   - Synthesize tool results
   - Generate explanation
   - Cite sources
4. **Stream Response**
   - Server-Sent Events (SSE)
   - Incremental text delivery

#### Example:
```
User: "What are the risks for ACME Corp?"
Bot: [streaming response]
"Based on the financial reports analyzed, ACME Corp shows the following risks:
1. High debt-to-equity ratio of 2.3...
[Evidence: Page 47, Financial Statements]
2. Missing liquidity covenants...
[Evidence: Loan Agreement, Section 7.2]
..."
```

---

## 📈 Data Flow States

```
UPLOADED → EXTRACTED → NORMALIZED → INDEXED → (COMPLETED)
    ↓
UPLOADING
    ↓
EXTRACTING (with progress tracking)
    ↓
NORMALIZING
    ↓
INDEXING
```

---

## 🔧 Configuration

### File Size Thresholds:
- `MAX_UPLOAD_SIZE`: 100MB (upload limit)
- `ADE_SYNC_MAX_BYTES`: 15MB (sync vs async boundary)

### Timeouts:
- ADE API: 480s (8 minutes total, 10s connect)
- Retry attempts: 2
- Polling max: 60 attempts (~1-2 minutes)

### Connection Pooling:
- Max connections: 20
- Client reuse across requests

---

## 🚨 Error Handling

### LandingAI API:
- **Transient errors** (429, 500+): Automatic retry with backoff
- **Client errors** (400, 401, 403): Fail fast, return error
- **Parse failure**: Return parse-only output
- **Extract failure**: Fallback to parse-only

### Pipeline Failures:
- Each stage validates previous stage output
- 404 if prerequisite stage incomplete
- Errors logged with context
- Graceful degradation where possible

---

## 📝 Job Progress Tracking

### ZIP Processing:
```json
{
  "status": "processing",
  "total": 5,      // Total files in ZIP
  "completed": 3,  // Files processed
  "failed": 0
}
```

### Streaming Updates:
- Endpoint: `GET /api/v1/extract/stream?document_id=doc_123`
- Format: Server-Sent Events (SSE)
- Updates every 0.5s
- Terminates on completion/failure

---

## 🔗 API Endpoint Summary

| Endpoint | Method | Purpose | Input | Output |
|----------|--------|---------|-------|--------|
| `/ingest` | POST | Upload document | File | Document metadata |
| `/extract` | POST | Run ADE extraction | document_id | ADE results |
| `/normalize` | POST | Build knowledge graph | document_id | Graph entities/edges |
| `/index` | POST | Index in DBs | graph_id | Index stats |
| `/risk` | POST | Detect risks | graph_id | Risk report |
| `/ask` | POST | AI chatbot query | message | Streaming response |
| `/documents` | GET | List documents | - | Document list |
| `/documents/{id}` | GET | Get document | document_id | Document details |
| `/graph/{id}` | GET | Get graph | graph_id | Graph data |

---

## 📚 References

- [LandingAI ADE Docs](https://docs.landing.ai/api-reference/tools/)
- [AWS Bedrock Claude](https://docs.aws.amazon.com/bedrock/)
- [Weaviate Documentation](https://weaviate.io/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)

---

## 🎯 Summary

The ArthaNethra pipeline transforms unstructured financial documents into:
1. **Structured data** (via LandingAI ADE)
2. **Knowledge graph** (via normalization)
3. **Searchable entities** (via vector + graph DBs)
4. **Risk insights** (via rules + AI)
5. **Interactive analysis** (via chatbot with tool calling)

Each stage is designed for reliability, scalability, and traceability—every insight links back to its source document and page.


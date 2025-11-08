# 🏗️ ArthaNethra — Technical Architecture

## Overview

ArthaNethra is a **hybrid AI financial investigation platform** that combines:
- **LandingAI's Agentic Document Extraction (ADE)** for structured data extraction
- **AWS Bedrock (Claude 3)** for reasoning and explanations
- **Vector databases (Weaviate)** for semantic search
- **Graph analytics** for relationship traversal
- **Angular frontend** for interactive visualization

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Angular Frontend (Port 4200)                     │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              Unified Chat + Explorer Component                    │  │
│  │  • Document Upload (Drag & Drop)                                  │  │
│  │  • Interactive Graph Viewer (Sigma.js + 4 layouts)                │  │
│  │  • Multi-document Chat Sessions (Streaming SSE)                   │  │
│  │  • PDF Evidence Viewer (ngx-extended-pdf-viewer)                  │  │
│  │  • Clickable Citations (Auto-attach + Jump to page)               │  │
│  │  • AI Response Graphs (Fullscreen modal)                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTP/REST + SSE
┌───────────────────────────────▼─────────────────────────────────────────┐
│                      FastAPI Backend (Port 8000)                         │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                   API Gateway (main.py - 1576 lines)                │ │
│  │                                                                      │ │
│  │  POST /upload          → IngestionService                           │ │
│  │     ↓ Save PDF to disk, create Document record                      │ │
│  │                                                                      │ │
│  │  POST /extract         → ExtractionService (325+ ADE refs)          │ │
│  │     ↓ Step 1: _ade_parse() → LandingAI Parse API                   │ │
│  │     ↓   PDF/DOCX → Markdown + Tables + Metadata                    │ │
│  │     ↓ Step 2: _ade_extract() → LandingAI Extract API (optional)    │ │
│  │     ↓   Markdown + Schema → Structured Entities                     │ │
│  │     ↓ Step 3: Detect document type (invoice/contract/loan/other)   │ │
│  │     ↓ Result: ade_output (markdown, tables, entities, citations)   │ │
│  │                                                                      │ │
│  │  POST /normalize       → NormalizationService                       │ │
│  │     ↓ Step 1: Check ADE entities (if >= 20, use them)              │ │
│  │     ↓ Step 2: If ADE < 20, fallback to specialized parsers:        │ │
│  │     ↓   • InvoiceParser (extract line items, totals)               │ │
│  │     ↓   • ContractParser (extract clauses, parties)                │ │
│  │     ↓   • LoanParser (extract terms, covenants)                    │ │
│  │     ↓   • Table Parser (extract financial metrics)                 │ │
│  │     ↓ Step 3: If < 5 entities & doc > 10k chars:                   │ │
│  │     ↓   → NarrativeParser (LLM chunks → entities + relationships)  │ │
│  │     ↓ Step 4: Create relationships:                                 │ │
│  │     ↓   • LLM-based (chunk analysis with Haiku)                    │ │
│  │     ↓   • Heuristic (shared properties)                            │ │
│  │     ↓ Result: entities[] + edges[]                                 │ │
│  │                                                                      │ │
│  │  POST /index           → IndexingService                            │ │
│  │     ↓ Batch insert entities → Weaviate (vectors)                   │ │
│  │     ↓ Batch insert entities + edges → Neo4j (graph)                │ │
│  │     ↓ Result: searchable + queryable knowledge graph               │ │
│  │                                                                      │ │
│  │  POST /chat/sessions/{id}/messages → ChatbotService                │ │
│  │     ↓ Step 1: MANDATORY document_search (Weaviate)                 │ │
│  │     ↓   Filter by attached document_ids                             │ │
│  │     ↓ Step 2: Optional graph_query (Neo4j)                         │ │
│  │     ↓ Step 3: Optional metric_compute                              │ │
│  │     ↓ Step 4: Claude 3.5 Sonnet reasoning                          │ │
│  │     ↓ Step 5: Generate graph data (entities + relationships)       │ │
│  │     ↓ Result: SSE stream (text + citations + graphData)            │ │
│  │                                                                      │ │
│  │  POST /risks/detect    → RiskDetectionService                      │ │
│  │     ↓ Numeric rule validation + LLM anomaly detection              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    17 Backend Services                              │ │
│  │  • IngestionService        (upload, validation)                     │ │
│  │  • ExtractionService       (ADE Parse + Extract, 325+ refs)         │ │
│  │  • InvoiceParser           (line items, totals)                     │ │
│  │  • ContractParser          (clauses, parties)                       │ │
│  │  • LoanParser              (terms, rates, covenants)                │ │
│  │  • NarrativeParser         (LLM chunked extraction - Haiku)         │ │
│  │  • MarkdownParser          (table extraction)                       │ │
│  │  • DocumentTypeDetector    (auto-routing logic)                     │ │
│  │  • NormalizationService    (ADE → entities + edges)                 │ │
│  │  • RelationshipDetector    (LLM + heuristic)                        │ │
│  │  • IndexingService         (Weaviate + Neo4j batching)              │ │
│  │  • RiskDetectionService    (rules + LLM)                            │ │
│  │  • ChatbotService          (multi-tool, streaming)                  │ │
│  │  • AnalyticsService        (metric calculations)                    │ │
│  │  • PersistenceService      (sessions, messages)                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────┬────────────┬────────────┬────────────┬────────────┬──────────────┘
      │            │            │            │            │
      ▼            ▼            ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│LandingAI │  │ Weaviate │  │  Neo4j   │  │   AWS    │  │  Local   │
│   ADE    │  │ (Docker) │  │ (Docker) │  │ Bedrock  │  │   Disk   │
│   API    │  │  Port    │  │  Ports   │  │ (Cloud)  │  │  (PDFs,  │
│          │  │  8080    │  │7474,7687 │  │          │  │  Cache)  │
│          │  │          │  │          │  │          │  │          │
│ • Parse  │  │ • Vector │  │ • Cypher │  │ • Sonnet │  │ • uploads│
│   (PDF→  │  │   Search │  │   Queries│  │   (Chat) │  │ • ade_   │
│   MD)    │  │ • Embed- │  │ • Graph  │  │ • Haiku  │  │   cache  │
│ • Extract│  │   dings  │  │   Algos  │  │   (Bulk) │  │ • session│
│   (MD+   │  │ • Chunks │  │ • 38 Edge│  │ • Tool   │  │   data   │
│   Schema)│  │          │  │   Types  │  │   Calling│  │          │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘

═══════════════════════════════════════════════════════════════════════

                        DOCUMENT PROCESSING FLOW

User uploads PDF → /upload
    ↓
IngestionService: Save to disk, validate
    ↓
/extract → ExtractionService
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: LandingAI ADE Parse API                                     │
│   • POST https://api.landing.ai/v1/tools/ade/parse                  │
│   • Input: PDF bytes + filename                                     │
│   • Output: { markdown, tables[], metadata }                        │
│   • Timeout: 8 minutes                                              │
└─────────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: LandingAI ADE Extract API (Optional)                        │
│   • POST https://api.landing.ai/v1/tools/ade/extract                │
│   • Input: { markdown, schema }                                     │
│   • Output: { entities[], key_values[], confidence }                │
│   • Fallback: Skip if schema extraction fails                       │
└─────────────────────────────────────────────────────────────────────┘
    ↓
Document.ade_output = { markdown, tables, entities, metadata }
    ↓
/normalize → NormalizationService
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ IF ADE entities >= 20: Use ADE entities (good quality)              │
│ ELSE:                                                                │
│   ├─ Detect document type (invoice/contract/loan/narrative)         │
│   └─ Route to specialized parser:                                   │
│       • InvoiceParser → line items, vendor, totals                  │
│       • ContractParser → parties, clauses, terms                    │
│       • LoanParser → borrower, lender, rate, covenants              │
│       • Table Parser → financial metrics from tables                │
│                                                                      │
│ IF entities < 5 AND markdown > 10,000 chars:                        │
│   └─ NarrativeParser:                                               │
│       1. Chunk markdown by paragraphs (5000 char chunks)            │
│       2. For each chunk: LLM (Haiku) → entities + relationships     │
│       3. Deduplicate entities across chunks                         │
└─────────────────────────────────────────────────────────────────────┘
    ↓
entities[] (12 types: Company, Loan, Person, Location, etc.)
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Create Relationships (edges[])                                       │
│   • LLM-based: Chunk entities → Haiku → relationships               │
│   • Heuristic: Shared properties → inferred relationships           │
│   • 38 edge types: HAS_LOAN, OWNS, INVESTED_IN, etc.                │
└─────────────────────────────────────────────────────────────────────┘
    ↓
/index → IndexingService
    ↓
┌───────────────────────┐  ┌───────────────────────┐
│ Weaviate (Vectors)    │  │ Neo4j (Graph)         │
│ • Batch insert 100/tx │  │ • Batch insert 100/tx │
│ • Generate embeddings │  │ • Create nodes + rels │
│ • Enable semantic     │  │ • Enable Cypher       │
│   search              │  │   queries             │
└───────────────────────┘  └───────────────────────┘
    ↓
Document status: COMPLETED
Knowledge graph ready for chat!
```

---

## Component Details

### 1. Frontend (Angular 19)

#### Components:
- **DocumentUploadComponent**
  - Drag-and-drop file upload
  - Multi-file ZIP support
  - Progress tracking

- **GraphViewerComponent** (Sigma.js + Graphology)
  - Interactive node-edge visualization
  - Zoom, pan, highlight
  - Real-time filter controls
  - Supports extended relationship vocabulary (ACQUIRED, INVESTED_IN, PARTNERS_WITH, etc.)

- **ChatbotComponent** (Angular Material)
  - Streaming responses from Claude
  - Message history
  - Citation buttons ("Open Graph", "Open Source")
  - Citation pills auto-attach the referenced document to the active chat and open it in the explorer

- **EvidenceViewerComponent** (ngx-extended-pdf-viewer)
  - PDF rendering with highlights
  - Page jump via citations
  - Zoom, search, download

- **DashboardComponent** (ECharts + AG Grid)
  - KPI charts (line, bar, pie)
  - Sortable/filterable data grids
  - Export functionality

#### Services:
- `DocumentService` → upload, status, download
- `GraphService` → query nodes, edges, subgraphs
- `ChatbotService` → send messages, stream responses
- `AuthService` → (optional) user management

---

### 2. Backend (FastAPI + Python)

#### Endpoints:

##### `/ingest` (POST)
```python
async def ingest_document(file: UploadFile) -> dict:
    """
    Upload and validate document
    Returns: { "document_id": "...", "status": "pending" }
    """
```

##### `/extract` (POST)
```python
async def extract_with_ade(document_id: str) -> dict:
    """
    Call LandingAI ADE API
    Returns: ADE JSON with citations
    """
```

##### `/normalize` (POST)
```python
async def normalize_to_graph(ade_output: dict) -> dict:
    """
    Convert ADE JSON to graph entities
    Returns: { "entities": [...], "edges": [...] }
    """
```

##### `/index` (POST)
```python
async def index_entities(entities: list) -> dict:
    """
    Index entities in Weaviate + Neo4j
    Returns: { "indexed": count }
    """
```

##### `/risk` (POST)
```python
async def detect_risks(entities: list) -> dict:
    """
    Run rule-based risk detection
    Returns: { "risks": [...], "severity": "high" }
    """
```

##### `/ask` (POST)
```python
async def chat_bot(message: str, context: dict) -> StreamingResponse:
    """
    Tool-augmented chatbot with Bedrock
    Returns: Streaming text + citations
    """
```

- Enforces a mandatory `document_search` tool call at the start of every interaction to gather evidence.
- Filters search results to documents attached to the active chat session.
- Automatically attaches a cited document to the chat session when the user clicks a citation pill so the explorer can open it instantly.

##### `/evidence` (GET)
```python
async def serve_pdf(document_id: str, page: int) -> FileResponse:
    """
    Serve PDF with highlights
    Returns: PDF byte stream
    """
```

---

### 3. ADE Integration (LandingAI)

#### Workflow:
```python
# 1. Upload PDF
document_id = upload_pdf("10K_2025.pdf")

# 2. Call ADE
ade_response = landingai_client.extract(
    document_id=document_id,
    schema="financial_entities"
)

# 3. Parse response
entities = parse_ade_output(ade_response)
# Returns: [{ "type": "Company", "name": "ACME", "page": 47 }]
```

#### Schema Definition:
```json
{
  "entities": ["Company", "Subsidiary", "Loan", "Invoice", "Metric"],
  "relationships": ["HAS_LOAN", "OWNS", "PARTY_TO", "HAS_METRIC"],
  "metadata": ["page", "clause", "table_id", "cell_coord"]
}
```

---

### 4. Weaviate Integration (Vector DB)

#### Purpose:
- Semantic search over entities
- Embedding-based relationship discovery
- Fast retrieval for chatbot context

#### Schema:
```python
class Entity(Base):
    name: str
    type: str  # Company, Loan, Metric, etc.
    properties: dict  # ADE extracted attributes
    embeddings: list  # Vector representation
    citations: list   # [{"page": 47, "section": "..."}]
```

#### Queries:
```python
# Semantic search
results = client.query.get(
    "Entity",
    ["name", "type", "citations"]
).with_near_text({
    "concepts": ["variable rate debt"]
}).with_limit(10).do()
```

---

### 5. Neo4j Integration (Optional)

#### Purpose:
- Complex graph queries (Cypher)
- Path analysis
- Network analytics

#### Cypher Examples:
```cypher
// Find all companies with debt > threshold
MATCH (c:Company)-[:HAS_LOAN]->(l:Loan)
WHERE l.variable_rate > 0.08
RETURN c, l

// Find exposure paths
MATCH path = (c:Company)-[*1..3]-(related:Entity)
WHERE c.name = "ACME"
RETURN path
```

---

### 6. AWS Bedrock Integration (Claude 3 Sonnet)

#### Chatbot Architecture:
```python
class ChatbotService:
    def __init__(self):
        self.bedrock = boto3.client("bedrock-runtime")
        self.tools = [
            GraphQueryTool(),
            DocLookupTool(),
            MetricComputeTool()
        ]
    
    async def chat(self, message: str, context: dict):
        # 1. Format message with context
        prompt = self.format_prompt(message, context)
        
        # 2. Call Claude with tools
        response = self.bedrock.invoke_with_response_stream(
            ModelId="anthropic.claude-3-sonnet-20240229-v1:0",
            Body={
                "messages": [{"role": "user", "content": prompt}],
                "tools": self.tools
            }
        )
        
        # 3. Stream response
        for chunk in response:
            yield chunk["chunk"]["bytes"]
```

#### Tool Definitions:
```python
tools = [
    {
        "name": "graph_query",
        "description": "Query the knowledge graph for entities and relationships",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string"},
                "filters": {"type": "object"}
            }
        }
    },
    {
        "name": "doc_lookup",
        "description": "Retrieve source document evidence",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "page": {"type": "integer"}
            }
        }
    }
]
```

---

## Data Flow

### 1. Document Ingestion Flow
```
User uploads PDF
  → Backend validates + stores locally
  → Returns document_id
  → Frontend shows "Processing..."
```

### 2. Extraction Flow
```
Backend calls LandingAI ADE
  → Receives structured JSON
  → Extracts entities + citations
  → Stores ADE output
  → Returns to frontend
```

### 3. Graph Construction Flow
```
Backend parses ADE output
  → Normalizes to entities (Company, Loan, etc.)
  → Creates edges (HAS_LOAN, OWNS, etc.)
  → Indexes in Weaviate
  → (Optional) Indexes in Neo4j
  → Returns graph summary
```

### 4. Risk Detection Flow
```
Backend runs rule engine
  → Checks numeric thresholds
  → Flags anomalies
  → LLM reviews for contextual insights
  → Returns risk report
```

### 5. Chatbot Query Flow
```
User: "Show high-risk debt"
  → Frontend sends to /ask endpoint
  → Backend formats context (graph + risks)
  → Calls Bedrock with tools
  → Bedrock invokes graph_query tool
  → Returns subgraph + citations
  → Streams response to frontend
```

---

## Deployment Architecture

### Local Development (Docker Compose)
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - LANDINGAI_API_KEY=${LANDINGAI_API_KEY}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
  
  frontend:
    build: ./frontend
    ports: ["4200:4200"]
    depends_on: [backend]
  
  weaviate:
    image: semitechnologies/weaviate:latest
    ports: ["8080:8080"]
  
  neo4j:
    image: neo4j:latest
    ports: ["7474:7474", "7687:7687"]
```

### Production (AWS ECS)
```
┌──────────────────────────────────────────┐
│         AWS Cloud Architecture           │
│                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │  ALB    │  │  ECS    │  │  S3     │ │
│  │(Public) │─→│(Tasks)  │─→│(Docs)   │ │
│  └─────────┘  └─────────┘  └─────────┘ │
│        │            │             │     │
│        └────────────┼─────────────┘     │
│                     │                    │
│  ┌──────────────────▼────────────────┐  │
│  │         Bedrock                   │  │
│  │      (Claude 3)                   │  │
│  └──────────────────┬────────────────┘  │
│                     │                    │
│  ┌──────────────────▼────────────────┐  │
│  │         LandingAI ADE             │  │
│  │         (External API)            │  │
│  └──────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

---

## Security & Privacy

### Data Handling:
- Documents stored locally (dev) or encrypted in S3 (production)
- ADE JSON cached for demo replay
- No PII stored in Weaviate/Neo4j (only entity names + metrics)
- API keys via environment variables

### Authentication:
- (Optional) JWT tokens for multi-user
- Session management via FastAPI SessionMiddleware
- Rate limiting on `/ask` endpoint

---

## Performance Optimization

### Caching:
- ADE results cached by document hash
- Graph query results cached (TTL 5 minutes)
- LLM responses cached for common queries

### Batching:
- Document uploads batch-processed (max 10 files)
- Graph indexing batched (100 entities/batch)

### Async:
- All I/O operations async (FastAPI + asyncio)
- Streaming responses for chatbot
- WebSocket for real-time graph updates

---

## Monitoring & Logging

### Metrics:
- Document processing time
- ADE API latency
- Chatbot response time
- Graph query performance

### Logging:
- Structured JSON logs (Python logging)
- Request/response trace IDs
- Error tracking (optional: Sentry)

---

## Future Enhancements

1. **Multi-tenant support** with per-user graph isolation
2. **Real-time collaboration** via WebSocket
3. **Advanced graph algorithms** (PageRank, community detection)
4. **ML-based risk scoring** (supervised learning)
5. **Document versioning** for temporal analysis

---

## References

- [LandingAI ADE Docs](https://landing.ai/document-automation/)
- [AWS Bedrock Claude](https://docs.aws.amazon.com/bedrock/latest/userguide/models-claude.html)
- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)


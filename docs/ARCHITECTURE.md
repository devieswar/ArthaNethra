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
┌─────────────────────────────────────────────────────────────────┐
│                         Angular Frontend                         │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Document       │  │  Knowledge      │  │  Evidence       │ │
│  │  Upload UI      │  │  Graph Viewer   │  │  Viewer         │ │
│  │  (Dropzone)     │  │  (Sigma.js)     │  │  (ngx-pdf)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  AI Chatbot     │  │  KPI Dashboard  │  │  Risk           │ │
│  │  (Claude)       │  │  (ECharts)      │  │  Alert Panel    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP/REST API
┌────────────────────▼────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   API Gateway (main.py)                     │ │
│  │  - /ingest   → Document upload & validation                 │ │
│  │  - /extract  → LandingAI ADE extraction                     │ │
│  │  - /normalize → Entity mapping & graph construction         │ │
│  │  - /index    → Weaviate/Neo4j indexing                     │ │
│  │  - /risk     → Rule-based risk detection                    │ │
│  │  - /ask      → AI chatbot endpoint                         │ │
│  │  - /evidence → PDF serving with highlights                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────┬────────────────┬────────────────┬────────────────┬────────┘
      │                │                │                │
┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
│LandingAI  │   │ Weaviate  │   │  Neo4j    │   │ AWS       │
│   ADE     │   │  (Local)  │   │ (Optional)│   │ Bedrock   │
│  API      │   │ Docker    │   │  Docker   │   │ (Cloud)   │
└───────────┘   └───────────┘   └───────────┘   └───────────┘
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

- **ChatbotComponent** (Angular Material)
  - Streaming responses from Claude
  - Message history
  - Citation buttons ("Open Graph", "Open Source")

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


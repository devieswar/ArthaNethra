# 🧠 ArthaNethra — AI Financial Risk Investigator

> *"Turning complex financial documents into connected, explainable insights."*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Angular](https://img.shields.io/badge/Angular-19-red.svg)](https://angular.io/)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange.svg)](https://aws.amazon.com/bedrock/)
[![LandingAI ADE](https://img.shields.io/badge/LandingAI-ADE-green.svg)](https://landing.ai/)

## 🌟 Overview

**ArthaNethra** (from Sanskrit: "Artha" = wealth, "Nethra" = eye/vision) is an AI-powered financial investigation platform that transforms complex financial documents into connected, explainable insights.

Financial analysts spend countless hours reviewing thousands of pages of documents to understand risks, relationships, and compliance gaps. ArthaNethra automates this process using:
* **LandingAI's Agentic Document Extraction (ADE)** for intelligent document parsing
* **AWS Bedrock (Claude 3)** for reasoning and explanations
* **Knowledge graphs** for relationship mapping
* **Vector search** for semantic discovery

---

## 🎯 Project Goal

Create an **AI-powered financial investigation agent** that can:

1. **Ingest & Understand** complex financial documents (10-Ks, loan agreements, invoices, contracts)
2. **Connect Key Entities** — companies, subsidiaries, instruments, vendors, metrics — into a **knowledge graph**
3. **Detect Risks, Anomalies, and Compliance Gaps** using LLM reasoning + numeric rules
4. **Explain Findings with Citations** — every insight links back to its source page or clause
5. **Enable Human-AI Collaboration** through a chatbot that "talks finance" and "proves its claims"

---

## 🧩 Core Features

### 🗂️ 1. Intelligent Document Processing
* **Hybrid Extraction Pipeline**: LandingAI ADE for structured data (tables, invoices) + LLM-based narrative parsing for unstructured text
* **Multi-Format Support**: 10-Ks, loan agreements, contracts, invoices, balance sheets
* **Adaptive Processing**: Automatic document type detection routes to specialized parsers
* **Rich Citations**: Every extracted entity preserves page, section, table, and cell-level provenance

### 🧱 2. Dynamic Knowledge Graph Construction
* **Deep Entity Normalization**: 12+ entity types (Company, Subsidiary, Loan, Invoice, Clause, Metric, Location, Person, etc.)
* **38+ Relationship Types**: Complex financial relationships (HAS_LOAN, OWNS, SUBSIDIARY_OF, INVESTED_IN, REGULATED_BY, etc.)
* **Dual-Mode Relationship Detection**:
  - **LLM-Based**: Entities & relationships extracted directly from narrative text chunks (faster, cheaper with Claude Haiku)
  - **Heuristic**: Property-based relationship inference (e.g., shared addresses, ownership patterns)
* **Multi-Database Architecture**: Weaviate (semantic vectors) + Neo4j (graph traversal) + In-memory (fast queries)

### 🌐 3. Advanced Graph Visualization
* **Interactive Exploration**: Sigma.js with real-time zoom, pan, hover, and drag
* **Multiple Layout Algorithms**: Force-directed, circular, grid, random (switchable on-the-fly)
* **Response Graphs**: AI-generated subgraphs visualized in fullscreen modals
* **Entity Filtering**: Dynamic filters by type, property thresholds, and risk level

### 💬 4. Context-Aware AI Chatbot
* **Multi-Document Sessions**: Chat with multiple documents simultaneously
* **Mandatory Document Search**: Every query triggers Weaviate semantic search for grounded responses
* **Tool-Augmented Reasoning**: 
  - `document_search()`: Semantic chunk retrieval (automatically filtered by attached docs)
  - `graph_query()`: Entity/relationship graph traversal
  - `metric_compute()`: Financial calculations and aggregations
* **Clickable Citations**: Source pills auto-attach and open documents in explorer
* **Graph Visualization Buttons**: "View Graph" pills show AI-mentioned entities in interactive modal
* **Streaming Responses**: Real-time SSE streaming with Claude 3.5 Sonnet

### 📊 5. Financial Analytics Dashboard
* **Unified Chat + Explorer Interface**: Single-page app combining chat, document list, graph viewer, and PDF evidence
* **Document Management**: Search, filter, attach/detach documents to chat sessions
* **Session Persistence**: Named chat sessions with full message history and document context
* **Inline Editing**: Rename sessions, delete with confirmation, manage multiple conversations

### 📑 6. Evidence Viewer with Auto-Navigation
* **ngx-extended-pdf-viewer**: Full-featured PDF viewer with zoom, search, download
* **Citation-Driven Navigation**: Click source pills → document auto-opens in explorer at exact page
* **Auto-Attachment**: Clicking citations for unattached documents automatically adds them to session

### ⚙️ 7. Production-Ready Architecture
* **Dockerized Stack**: One-command deployment (frontend + backend + Weaviate + Neo4j)
* **Async Everything**: FastAPI with full async/await for I/O-bound operations
* **Caching**: ADE results cached by document hash, reducing API costs
* **Error Resilience**: Exponential backoff, fallback models, graceful degradation

### 🧾 8. Multi-Strategy Risk Detection
* **Hybrid Risk Engine**: 
  - Numeric rule validation (thresholds, ratios)
  - LLM-based anomaly detection
  - Cross-document pattern matching
* **Risk Severity Classification**: HIGH/MEDIUM/LOW with actionable recommendations
* **Citation-Backed Findings**: Every risk links to source evidence

### 🔍 9. Explainability & Provenance
* **Full Traceability**: Document → ADE JSON → Entities → Graph → Chatbot response
* **Chain-of-Thought**: AI explains reasoning steps before answering
* **Evidence-First**: Only answers from attached documents; refuses general knowledge queries

### 🧩 10. Modular Service Architecture
* **17 Backend Services**: Ingestion, extraction (ADE + narrative), normalization, indexing, risk detection, chatbot, analytics, persistence
* **Specialized Parsers**: Invoice, contract, loan, narrative (each optimized for document type)
* **Clean Separation**: Models, services, endpoints cleanly separated with Pydantic validation

---

## 💡 Innovation Highlights

| Area                          | Innovation                                  | Description                                                                          |
| ----------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Hybrid Extraction**         | ADE + LLM narrative parsing                 | Structured data via ADE, unstructured narrative via chunked LLM analysis             |
| **Dual-Model Strategy**       | Sonnet (reasoning) + Haiku (extraction)     | Cost-optimized: expensive model for chat, cheap model for bulk entity extraction     |
| **Automatic Document Routing** | Type detection → specialized parser        | Invoices, contracts, loans, narratives each get domain-optimized processing          |
| **Grounded AI**               | Mandatory document search                   | AI **must** search Weaviate before responding; refuses non-cited answers             |
| **Interactive Citations**     | Click → auto-attach → open PDF             | Source pills automatically attach documents and jump to exact evidence page          |
| **Live Graph Generation**     | AI-generated subgraphs                      | Chat responses include structured graph data visualized in draggable modal           |
| **Multi-Layout Graphs**       | Switchable algorithms                       | Force-directed, circular, grid layouts toggled in real-time without re-render        |
| **Session-Based Context**     | Multi-document chat sessions                | Attach/detach docs, maintain conversation history, named sessions with persistence   |
| **Provenance Preservation**   | End-to-end citation tracking                | Document → ADE → Entity → Graph → Chat response → Evidence viewer (full traceability) |

---

## 🏗️ Tech Stack

| Layer                  | Tech                                      | Purpose                                     |
| ---------------------- | ----------------------------------------- | ------------------------------------------- |
| **Frontend**           | Angular 19 + Tailwind CSS                 | Modern responsive single-page app           |
| **Graph Visualization**| Sigma.js v3 + Graphology + Layout Algos   | Interactive, draggable graphs with layouts  |
| **Markdown Rendering** | MarkdownIt                                | Rich text formatting in chat                |
| **PDF Viewer**         | ngx-extended-pdf-viewer                   | Full-featured PDF with citations            |
| **Backend**            | FastAPI + Uvicorn + Python 3.11           | High-performance async API                  |
| **AI Models**          | AWS Bedrock (Claude 3.5 Sonnet + Haiku)   | Reasoning (Sonnet) + bulk extraction (Haiku)|
| **Document Extraction**| LandingAI ADE                             | Structured data extraction (tables, KV)     |
| **Narrative Parsing**  | Custom LLM chunking (Haiku)               | Entity + relationship extraction from prose |
| **Vector DB**          | Weaviate (Docker)                         | Semantic search, embeddings                 |
| **Graph DB**           | Neo4j (Docker)                            | Complex graph queries, Cypher               |
| **Storage**            | Local filesystem                          | Documents, ADE cache, session data          |
| **Logging**            | Loguru                                    | Structured logs with rotation               |
| **DevOps**             | Docker Compose + Makefile                 | One-command deployment and management       |

---

## 🗺️ Architecture Diagram

![ArthaNethra System Architecture](docs/ArthaNethra%20Arc%20Diagram.jpg)

---

## 🧭 Elevator Pitch (30 seconds)

> "ArthaNethra is an AI financial risk investigator that reads thousands of filings, connects relationships, and detects hidden risks — all with traceable, explainable insights.
> It uses LandingAI's ADE for extraction, AWS Bedrock for reasoning, and a live knowledge graph for real-time exploration — delivering the clarity financial analysts wish they had."

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** 
- **Node.js 20+**
- **Docker & Docker Compose**
- **UV** (recommended) or pip — [Install UV](https://docs.astral.sh/uv/)
- **AWS credentials** for Bedrock
- **LandingAI API key**

### Installation

```bash
# Clone the repository
git clone https://github.com/devieswar/ArthaNethra.git
cd ArthaNethra

# Set up environment variables
cp env.example .env
# Edit .env with your API keys

# Start all services with Docker
docker-compose up -d

# Access the application
# Frontend: http://localhost:4200
# Backend API: http://localhost:8000/api/v1/docs
# Neo4j: http://localhost:7474
```

**📖 For detailed setup instructions, see [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)**

### Code Quality

```bash
# Check code quality
make lint

# Auto-fix issues
make format
```

**📋 For linting details, see [LINT_QUICKSTART.md](LINT_QUICKSTART.md)**

---

## 📁 Project Structure

```
ArthaNethra/
├── backend/                      # FastAPI backend
│   ├── services/                 # 17 Business logic services
│   │   ├── ingestion.py          # Document upload & validation
│   │   ├── extraction.py         # LandingAI ADE API integration
│   │   ├── invoice_parser.py     # Specialized invoice extraction
│   │   ├── contract_parser.py    # Contract clause extraction
│   │   ├── loan_parser.py        # Loan agreement parsing
│   │   ├── narrative_parser.py   # LLM-based narrative extraction (NEW)
│   │   ├── markdown_parser.py    # Markdown table parsing
│   │   ├── markdown_analyzer.py  # Schema detection from markdown
│   │   ├── document_type_detector.py # Auto-routing logic
│   │   ├── normalization.py      # ADE → Entity normalization
│   │   ├── relationship_detector.py # LLM + heuristic relationship finder
│   │   ├── indexing.py           # Weaviate + Neo4j indexing
│   │   ├── risk_detection.py     # Hybrid risk engine
│   │   ├── chatbot.py            # Multi-tool chatbot with SSE streaming
│   │   ├── analytics.py          # Metric calculations
│   │   └── persistence.py        # Session & document management
│   ├── models/                   # Pydantic data models
│   │   ├── document.py           # Document metadata
│   │   ├── entity.py             # 12 entity types
│   │   ├── edge.py               # 38 relationship types
│   │   ├── risk.py               # Risk findings
│   │   ├── citation.py           # Source provenance
│   │   └── chat_session.py       # Chat session model
│   ├── config.py                 # Environment config
│   ├── main.py                   # FastAPI app (1576 lines)
│   ├── requirements.txt          # 30+ dependencies
│   └── Dockerfile
├── frontend/                     # Angular 19 frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/
│   │   │   │   └── chat-unified/  # Unified chat + explorer UI
│   │   │   │       ├── chat-unified.component.ts    (1529 lines)
│   │   │   │       ├── chat-unified.component.html  (1080 lines)
│   │   │   │       └── chat-unified.component.css
│   │   │   ├── services/
│   │   │   │   └── api.service.ts  # HTTP client for backend
│   │   │   ├── models/             # TypeScript interfaces
│   │   │   └── app.component.ts
│   │   ├── types/
│   │   │   └── markdown-it.d.ts    # Custom type definitions
│   │   └── styles.scss
│   ├── package.json               # 20+ npm packages
│   ├── tailwind.config.js
│   └── Dockerfile
├── docs/                          # Comprehensive documentation
│   ├── ARCHITECTURE.md            # System architecture (480 lines)
│   ├── HACKATHON_CHECKLIST.md     # Submission checklist
│   ├── JUDGE_EVALUATION.md        # Self-evaluation (NEW)
│   └── SAMPLE_QUESTIONS.md        # 98 test queries (NEW)
├── docker-compose.yml             # Full stack orchestration
├── Makefile                       # Dev shortcuts
├── LICENSE
└── README.md
```

---

## 🎯 Key Use Cases

| Use Case                 | Problem                                 | ArthaNethra Solution                      |
| ------------------------ | --------------------------------------- | ----------------------------------------- |
| **Loan Risk Assessment** | Manual review of loan agreements (weeks) | Automated extraction + risk scoring (hours) |
| **Compliance Audit**     | Missing covenants detected too late      | Real-time compliance gap detection        |
| **Financial Analysis**   | Fragmented view across documents          | Unified knowledge graph of relationships  |
| **Invoice Reconciliation** | Time-consuming GL matching              | Automated mismatch detection               |

---

## 🚀 Current Status & Metrics

### ✅ Implemented Features
- ✅ Full document processing pipeline (ADE + narrative extraction)
- ✅ 38 relationship types, 12 entity types
- ✅ Multi-document chat sessions with persistence
- ✅ Clickable citations with auto-attach
- ✅ AI-generated response graphs
- ✅ Multiple graph layout algorithms
- ✅ Mandatory document search for grounded responses
- ✅ Dual-model strategy (Sonnet + Haiku) for cost optimization
- ✅ Hybrid relationship detection (LLM + heuristics)
- ✅ Docker Compose deployment

### 📊 Code Metrics
- **Backend**: 1,576 lines (main.py) + 17 services
- **Frontend**: 1,529 lines (chat component) + 1,080 lines (template)
- **Documentation**: 4 comprehensive docs (2,000+ lines)
- **Test Coverage**: 98 sample questions for demos

### 🔧 Known Limitations
- No multi-tenant support yet (single-user deployment)
- ADE requires API key (not bundled)
- No mobile-optimized UI
- Session data stored locally (not cloud-synced)

## 🧩 Future Extensions

### Near-term (30 days)
- [ ] Add export functionality (PDF reports, CSV data)
- [ ] Mobile-responsive UI
- [ ] Performance metrics dashboard (processing time, accuracy)
- [ ] Bulk document operations

### Mid-term (90 days)
- [ ] Multi-tenant architecture with RBAC
- [ ] Deploy to AWS ECS with S3 storage
- [ ] User authentication & audit trail
- [ ] Custom ADE schema training
- [ ] Integration with Slack, Excel, Bloomberg Terminal

### Long-term (6+ months)
- [ ] ML-based risk scoring (supervised learning)
- [ ] Advanced graph algorithms (PageRank, community detection)
- [ ] Document versioning for temporal analysis
- [ ] Real-time collaboration via WebSocket
- [ ] Fine-tuned domain-specific models

---

## 📄 License

MIT License - see LICENSE file for details

---

## 👥 Contributors

Built for the Financial AI Hackathon Championship 2025

---

## 📞 Contact

For questions or support, please open an issue in the repository.


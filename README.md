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

### 🗂️ 1. Smart Document Ingestion (ADE Integration)
* Upload financial PDFs or ZIPs (SEC filings, invoices, contracts)
* LandingAI **ADE API** extracts: key-value pairs, tables, sections, clauses, and metadata
* Outputs **structured JSON** with **citations** (page, cell, clause)

### 🧱 2. Entity Graph Construction
* ADE output normalized into entities: `Company`, `Subsidiary`, `Instrument`, `Invoice`, `Clause`, `Metric`
* Stored in **Weaviate (local)** with embeddings + cross-refs
* Optional **Neo4j integration** for advanced Cypher analytics

### 🌐 3. Financial Graph Visualization (Sigma.js)
* Interactive network of relationships: "ACME → HAS_LOAN → Bank of America"
* Dynamic filters for entity types, thresholds, and risk factors
* Real-time highlighting from chatbot commands

### 💬 4. Tool-Augmented Chatbot (Claude 3 on Bedrock)
* Natural-language interface for analysts
* Example queries: "Show subsidiaries with >8% variable-rate debt"
* Backend tools: `graph_query()`, `doc_lookup()`, `metric_compute()`
* Returns findings, subgraphs, and citations with "Open Graph" and "Open Source" buttons

### 📊 5. KPI & Trend Dashboards (ECharts + AG Grid)
* Displays: profit/loss trends, debt ratios, exposure distribution
* Built-in filters for period, entity type, or metric name

### 📑 6. Evidence Viewer (ngx-extended-pdf-viewer)
* View ADE-sourced PDFs with highlights
* Click any citation → jump to exact page/section
* Powered by pre-signed local URLs for offline demo

### ⚙️ 7. Local-first Architecture
* All components run locally for speed and stability
* Angular (frontend) + FastAPI (backend) + Weaviate (vectors)
* Minimal reliance on cloud beyond ADE and Bedrock APIs

### 🧾 8. Risk Detection Engine (Rules + Reasoning)
* Hybrid approach: LLM identifies anomalies + Python rule engine checks thresholds
* Example rules: Variable-rate > 8% → flag "Interest Rate Risk"

### 🔍 9. Explainability & Traceability
* Every result has clickable evidence
* Chatbot provides reasoning chain and numeric breakdown

### 🧩 10. Modular Microservice Design
* FastAPI microservices: `/ingest`, `/extract`, `/normalize`, `/index`, `/risk`, `/ask`, `/evidence`

---

## 💡 Innovation Highlights

| Area                       | Innovation                    | Description                                                |
| -------------------------- | ----------------------------- | ---------------------------------------------------------- |
| **ADE Integration**        | Deep ADE JSON post-processing | Converts raw extraction into graph entities and citations  |
| **Financial Graph AI**     | Hybrid LLM + vector + graph   | Combines semantic understanding + relational reasoning     |
| **Explainable AI**         | Traceable evidence            | Every LLM claim backed by ADE-sourced page/cell            |
| **Local-first Design**     | Fully runnable demo           | Works offline, fast iterations, reproducible               |
| **Tool-Augmented Chatbot** | Actionable dialogue           | Chatbot triggers graph, evidence, metrics programmatically |
| **Cross-Domain Utility**   | Real finance workflows        | Loan risk, audit trail, compliance check, variance reports |

---

## 🏗️ Tech Stack

| Layer              | Tech                          | Purpose                               |
| ------------------ | ----------------------------- | ------------------------------------- |
| **Frontend**       | Angular 19 + Tailwind         | Modern responsive UI                  |
| **Graph**          | Sigma.js + Graphology         | Real-time visualization               |
| **Charts**         | ECharts + AG Grid             | KPIs, trends, analytics               |
| **PDFs**           | ngx-extended-pdf-viewer       | Source evidence                       |
| **Backend**        | FastAPI + Python              | Microservice orchestrator             |
| **AI / LLM**       | AWS Bedrock (Claude 3 Sonnet) | Reasoning + explanations              |
| **Extraction**     | LandingAI ADE                 | Document parsing (mandatory)          |
| **Vector DB**      | Weaviate (Docker local)       | Semantic retrieval & graph cross-refs |
| **Graph DB (opt)** | Neo4j (local)                 | Complex relations, Cypher queries     |
| **Storage**        | Local filesystem              | PDFs, ADE JSON                        |
| **DevOps**         | Docker Compose                | Self-contained demo environment       |

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
├── backend/              # FastAPI backend
│   ├── services/         # Business logic services
│   │   ├── ingestion.py        # Document upload
│   │   ├── extraction.py       # LandingAI ADE integration
│   │   ├── normalization.py    # Graph construction
│   │   ├── indexing.py         # Weaviate/Neo4j indexing
│   │   ├── risk_detection.py   # Risk analysis
│   │   └── chatbot.py          # AWS Bedrock chatbot
│   ├── models/           # Data models
│   │   ├── document.py
│   │   ├── entity.py
│   │   ├── edge.py
│   │   ├── risk.py
│   │   └── citation.py
│   ├── config.py         # Configuration
│   ├── main.py           # FastAPI application
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile
├── frontend/             # Angular frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/     # UI components
│   │   │   │   ├── dashboard/
│   │   │   │   ├── upload/
│   │   │   │   ├── graph/
│   │   │   │   ├── chat/
│   │   │   │   └── risks/
│   │   │   ├── services/       # API services
│   │   │   ├── models/         # TypeScript models
│   │   │   └── app.component.ts
│   │   ├── environments/
│   │   └── styles.scss
│   ├── package.json      # Node dependencies
│   ├── angular.json
│   ├── tailwind.config.js
│   └── Dockerfile
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md   # Technical architecture
│   ├── API.md            # API documentation
│   └── PROJECT_OVERVIEW.md
├── docker-compose.yml    # Docker orchestration
├── env.example           # Environment template
├── docs/GETTING_STARTED.md    # Setup guide
├── docs/HACKATHON_CHECKLIST.md
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

## 🧩 Future Extensions

* Deploy to AWS ECS with real S3 + Bedrock integration
* Add **document QA fine-tuning** for ADE schemas
* Integrate **neo4j-graph-algo** for exposure concentration
* Add **multi-user dashboards + audit trail**

---

## 📄 License

MIT License - see LICENSE file for details

---

## 👥 Contributors

Built for the Financial AI Hackathon Championship 2025

---

## 📞 Contact

For questions or support, please open an issue in the repository.


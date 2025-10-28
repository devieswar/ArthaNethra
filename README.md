# 🧠 ArthaNethra — AI Financial Risk Investigator

> *"Turning complex financial documents into connected, explainable insights."*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Angular](https://img.shields.io/badge/Angular-19-red.svg)](https://angular.io/)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange.svg)](https://aws.amazon.com/bedrock/)
[![LandingAI ADE](https://img.shields.io/badge/LandingAI-ADE-green.svg)](https://landing.ai/)

## 🚀 Hackathon Focus

**Event:** Financial AI Hackathon Championship 2025  
**Hosts:** LandingAI × AWS × DeepLearning.AI  
**Core Challenge:** Build an intelligent financial agent that:
* Integrates **LandingAI's Agentic Document Extraction (ADE)** API ✅ (mandatory)
* Leverages **AWS Bedrock** for reasoning
* Demonstrates real-world financial document analysis & insights
* Runs as a usable prototype with explainability and real-time reasoning

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
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- AWS credentials for Bedrock
- LandingAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ArthaNethra.git
cd ArthaNethra

# Start infrastructure
docker-compose up -d

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install

# Run backend
cd ../backend
uvicorn main:app --reload

# Run frontend (new terminal)
cd frontend
ng serve
```

---

## 📁 Project Structure

```
ArthaNethra/
├── backend/              # FastAPI microservices
│   ├── services/
│   │   ├── ingestion.py
│   │   ├── extraction.py
│   │   ├── normalization.py
│   │   ├── indexing.py
│   │   ├── risk_detection.py
│   │   └── chatbot.py
│   ├── models/
│   ├── utils/
│   └── main.py
├── frontend/             # Angular application
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/
│   │   │   ├── services/
│   │   │   └── models/
│   │   └── assets/
│   └── angular.json
├── docs/                 # Documentation
│   ├── PITCH_DECK.md
│   ├── ARCHITECTURE.md
│   └── API.md
├── docker-compose.yml
└── README.md
```

---

## 🏆 Hackathon Goals

| Goal                                      | Description                                            | Metric                            |
| ----------------------------------------- | ------------------------------------------------------ | --------------------------------- |
| **1. Problem Clarity & Domain Relevance** | Solve real-world financial compliance / audit use case | Clear risk detection examples     |
| **2. Deep ADE Integration**               | Mandatory API use; visible ADE-to-Graph mapping        | Live ADE extraction + JSON proof  |
| **3. Technical Depth**                    | LLM + Graph + Vector + UI synergy                      | Demonstrated architecture diagram |
| **4. Accuracy & Reliability**             | Verified results, evidence-backed insights             | Citations + numeric checks        |
| **5. Usability & Workflow Design**        | Interactive and intuitive                              | Clean UI, fast graph, simple chat |
| **6. Feasibility**                        | Runnable MVP with path to pilot                        | Local demo + deploy-ready code    |
| **7. Presentation Quality**               | Polished, visual, confident story                      | <4 min crisp demo & Q&A ready     |

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


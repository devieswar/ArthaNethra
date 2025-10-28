# 📖 ArthaNethra — Project Overview

## What is ArthaNethra?

**ArthaNethra** (from Sanskrit: "Artha" = wealth, "Nethra" = eye/vision) is an AI-powered financial investigation platform that transforms complex financial documents into connected, explainable insights.

### The Core Value Proposition
> "Financial analysts spend weeks reviewing thousands of pages to understand risks. ArthaNethra does it in minutes, with every insight backed by traceable evidence."

---

## Why This Project?

### The Problem
Financial institutions face a critical challenge:

1. **Information Overload**
   - A single 10-K filing can contain 200+ pages
   - Multiple documents across subsidiaries, contracts, invoices
   - Manual review is slow, expensive, and error-prone

2. **Hidden Relationships**
   - Subsidiary structures are complex
   - Debt obligations span multiple contracts
   - Risks are fragmented across documents

3. **Compliance Gaps**
   - Missed covenants can lead to penalties
   - Reconciliation errors go undetected
   - Regulatory filings require cross-checking

4. **Time-Consuming Analysis**
   - Analysts need days to complete risk assessments
   - Evidence gathering requires page-by-page review
   - No unified view of financial health

### Our Solution
ArthaNethra automates the analysis pipeline:
- ✅ Extract structured data from any financial document
- ✅ Build a knowledge graph of relationships
- ✅ Detect risks using AI reasoning + numeric rules
- ✅ Explain findings with clickable evidence
- ✅ Enable natural-language queries

---

## How It Works

### 1. Document Ingestion
**Input:** PDFs, ZIP files (SEC filings, contracts, invoices)

**Process:**
- User uploads documents via web UI
- Files validated and staged for processing

**Output:** Document ID + metadata

### 2. Document Extraction (ADE)
**Input:** Document ID

**Process:**
- LandingAI ADE API extracts:
  - Key-value pairs
  - Tables and matrices
  - Sections and clauses
  - Page-level citations

**Output:** Structured JSON with citations

**Example:**
```json
{
  "entities": [
    {
      "type": "Company",
      "name": "ACME Corporation",
      "page": 47,
      "attributes": {
        "industry": "Technology",
        "fiscal_year": 2025
      }
    },
    {
      "type": "Loan",
      "name": "Variable Rate Credit Facility",
      "page": 89,
      "attributes": {
        "bank": "Bank of America",
        "principal": 50000000,
        "rate": 0.0875
      }
    }
  ]
}
```

### 3. Knowledge Graph Construction
**Input:** ADE JSON

**Process:**
- Normalize entities (Company, Subsidiary, Loan, Invoice, Metric)
- Create relationships (HAS_LOAN, OWNS, PARTY_TO, HAS_METRIC)
- Store in Weaviate (vectors) + Neo4j (graph)

**Output:** Graph of interconnected entities

**Example:**
```
Company:ACME Corp
  ├─ HAS_LOAN → Loan:Variable Rate ($50M, 8.75%)
  ├─ OWNS → Subsidiary:ACME Europe
  └─ HAS_METRIC → Metric:Debt Ratio (0.35)
```

### 4. Risk Detection
**Input:** Graph entities + business rules

**Process:**
- **Rule-based checks:**
  - Variable-rate debt > 8% → "Interest Rate Risk"
  - Missing covenant clause → "Compliance Gap"
  - Invoice mismatch → "Reconciliation Error"
  
- **LLM-based analysis:**
  - Detect anomalies in language
  - Contextual risk assessment

**Output:** Risk report with severity + citations

### 5. Interactive Visualization
**Input:** Graph + user filters

**Process:**
- Sigma.js renders interactive network
- Filters by entity type, risk level, threshold
- Real-time highlighting from chat queries

**Output:** Visual graph explorer

### 6. AI-Powered Chatbot
**Input:** Natural language query

**Process:**
- Claude 3 (Bedrock) receives query + context
- Invokes tools: `graph_query()`, `doc_lookup()`, `metric_compute()`
- Returns findings + citations

**Output:** Streaming response with "Open Graph" and "Open Source" buttons

**Example Dialog:**
```
User: "Show me all subsidiaries with variable-rate debt above 8%"

ArthaNethra: "Found 3 subsidiaries with high variable-rate exposure:
  1. ACME Europe Ltd. → $25M at 8.75% (Risk: HIGH)
     [Open Graph] [Open Source - page 89]
  2. TechCorp Inc. → $12M at 9.2% (Risk: HIGH)
     [Open Graph] [Open Source - page 142]
  3. GlobalTech Asia → $8M at 8.3% (Risk: MEDIUM)
     [Open Graph] [Open Source - page 201]

These represent 72% of total variable-rate exposure. Consider hedging strategies."
```

### 7. Evidence Viewer
**Input:** Document ID + page number

**Process:**
- ngx-extended-pdf-viewer loads PDF
- Highlights specific cells/paragraphs
- Enables zoom, search, download

**Output:** Interactive PDF viewer

### 8. KPI Dashboards
**Input:** Graph metrics

**Process:**
- ECharts renders trends (profit/loss, debt ratios)
- AG Grid displays tabular data
- Filters by period, entity type, metric name

**Output:** Analytics dashboard

---

## Technology Stack

### Frontend
- **Angular 19** — Modern reactive framework
- **Tailwind CSS** — Utility-first styling
- **Sigma.js** — Graph visualization
- **ECharts** — Data visualization
- **AG Grid** — Data tables
- **ngx-extended-pdf-viewer** — PDF rendering

### Backend
- **FastAPI** — High-performance async API
- **Python 3.11+** — Core language
- **Pydantic** — Data validation
- **aiohttp** — Async HTTP client

### AI/ML
- **LandingAI ADE** — Document extraction (mandatory)
- **AWS Bedrock (Claude 3 Sonnet)** — LLM reasoning
- **boto3** — AWS SDK

### Data Storage
- **Weaviate (local)** — Vector embeddings + graph cross-refs
- **Neo4j (optional)** — Advanced graph analytics
- **Local filesystem** — PDFs, ADE JSON cache

### DevOps
- **Docker Compose** — Local development
- **Git** — Version control

---

## Hackathon Alignment

### Required Integration (LandingAI ADE)
✅ **Mandatory:** Use ADE API for extraction  
✅ **Deep Integration:** ADE output → graph entities with citations  
✅ **Visible:** Live demo shows ADE JSON → graph mapping

### Required Integration (AWS Bedrock)
✅ **Mandatory:** Use Bedrock for AI reasoning  
✅ **Tool-Augmented:** Chatbot invokes graph tools  
✅ **Streaming:** Real-time responses to user queries

### Hackathon Goals
| Goal                                      | How We Address It                              |
| ----------------------------------------- | ---------------------------------------------- |
| **1. Problem Clarity**                    | Real analyst pain: risk detection, compliance  |
| **2. ADE Integration**                    | Visible extraction → graph pipeline             |
| **3. Technical Depth**                    | LLM + Vector + Graph + UI synergy              |
| **4. Accuracy & Reliability**              | Citations + numeric rule validation            |
| **5. Usability**                          | Clean UI, fast graph, simple chat               |
| **6. Feasibility**                        | Runnable local demo + deploy-ready code         |
| **7. Presentation Quality**               | <4 min polished demo + Q&A ready                |

---

## Innovation Highlights

### 1. Hybrid AI Reasoning
**Traditional:** Either LLM-based OR rule-based  
**ArthaNethra:** Both, combined
- LLM identifies contextual anomalies
- Rules validate numeric thresholds
- Result: More accurate, explainable insights

### 2. Explainable Citations
**Traditional:** AI makes claims without evidence  
**ArthaNethra:** Every claim linked to source
- "This subsidiary has 8.75% variable-rate debt" → [Page 89, Table 3.2.1]
- Users can verify → AI gains trust

### 3. Tool-Augmented Chatbot
**Traditional:** Chatbot gives generic answers  
**ArthaNethra:** Chatbot uses tools, returns actionable results
- Queries graph → returns subgraph + evidence
- Users can explore further or open source PDFs

### 4. Local-First Architecture
**Traditional:** Heavy cloud dependencies  
**ArthaNethra:** Runs locally for speed + stability
- Docker Compose → one-command startup
- Works offline (except ADE + Bedrock APIs)
- Fast iterations during development

### 5. Financial Graph AI
**Traditional:** Vector search OR graph analytics  
**ArthaNethra:** Semantic understanding + relational reasoning
- Weaviate: Find similar entities (semantic)
- Neo4j: Traverse relationships (relational)
- Combined: Comprehensive financial intelligence

---

## Use Cases

### 1. Loan Risk Assessment
**Scenario:** Bank needs to assess loan portfolio risk

**ArthaNethra:**
- Uploads loan agreements via ADE
- Builds graph of borrowers → loans → collateral
- Detects: "35% of portfolio has variable-rate terms"
- Highlights: "ACME Corp has $50M exposure, rate = 8.75%"

**Benefit:** 80% time savings, earlier risk detection

---

### 2. Compliance Audit
**Scenario:** Internal audit checks for missing covenants

**ArthaNethra:**
- Uploads contracts + agreements
- Parses entity structure (parent → subsidiaries)
- Detects: "Missing 'material adverse change' clause in TechSub agreement"
- Citation: [Document: TechSub_Agreement.pdf, Page 12, Section 4.2]

**Benefit:** 90% time savings, catch compliance gaps

---

### 3. Financial Analysis
**Scenario:** Analyst needs to understand subsidiary structure

**ArthaNethra:**
- Queries: "Show me all subsidiaries of ACME Corp"
- Returns: Subgraph with 12 subsidiaries across 3 continents
- Visualizes: Network diagram with filters (region, revenue)
- Dashboard: Exposure distribution by region

**Benefit:** Unified view, 70% faster analysis

---

### 4. Invoice Reconciliation
**Scenario:** Finance team reconciles invoices with GL

**ArthaNethra:**
- Uploads invoices + GL extracts via ADE
- Extracts: Invoice totals, GL line items, dates
- Detects: "3 invoices don't match GL entries"
- Flagged: Invoice #12345: expected $10K, GL shows $9.5K

**Benefit:** 85% time savings, catch errors early

---

## Future Roadmap

### Phase 1: MVP (Current)
✅ Document ingestion  
✅ ADE extraction  
✅ Graph construction  
✅ Basic visualization  
✅ Chatbot (tool-augmented)  
✅ Evidence viewer  

### Phase 2: Enhancement
- Multi-user support
- Advanced graph algorithms
- Temporal analysis (document versioning)
- ML-based risk scoring

### Phase 3: Production
- Deploy to AWS ECS
- Enterprise authentication
- API rate limiting + monitoring
- Audit trail

### Phase 4: Scale
- Multi-tenant SaaS
- White-label solutions
- Industry-specific fine-tuning
- API marketplace

---

## Key Differentiators

| Competitor Approach                    | ArthaNethra Approach                                    |
| -------------------------------------- | ------------------------------------------------------- |
| Generic document search                | **Financial-domain graph** with relationships           |
| Black-box AI                           | **Explainable AI** with citations                       |
| Single-step extraction                 | **Multi-step pipeline**: extraction → graph → risk → chat |
| Cloud-only deployment                  | **Local-first** with Docker Compose                     |
| General LLM chat                       | **Tool-augmented** chatbot with graph/evidence tools    |
| Static reports                         | **Interactive visualization** with real-time updates    |

---

## Business Model

### Target Users
- **Financial Analysts** — Risk assessment, compliance checks
- **Internal Auditors** — Gap analysis, reconciliation
- **CFOs/Controllers** — Subsidiary oversight, exposure management
- **Compliance Officers** — Regulatory filing preparation

### Pricing (Post-Hackathon)
- **Starter:** $99/month (100 documents/month)
- **Professional:** $499/month (unlimited documents)
- **Enterprise:** Custom (multi-user, SSO, API access)

### Go-to-Market
1. Pilot with 3-5 financial institutions
2. Case studies + testimonials
3. LandingAI marketplace listing
4. AWS marketplace listing

---

## Competition Analysis

| Competitor                    | Strength                                  | Weakness                                      |
| ----------------------------- | ----------------------------------------- | --------------------------------------------- |
| **Bloomberg Terminal**        | Real-time data                            | Expensive, no explainability                  |
| **FactSet / Refinitiv**       | Comprehensive datasets                    | Manual workflow, no AI reasoning              |
| **Generic AI Chatbots**       | Free/easy setup                           | No financial domain knowledge, no graph       |
| **Document Management**        | Organized storage                         | No extraction, no relationships, static        |
| **ArthaNethra**               | ✅ AI + Graph + Explainable + Tool-Augmented | None (yet!)                                   |

---

## Success Metrics

### Hackathon Success
- 🏆 Win or place in top 3
- 📊 Judges impressed by technical depth
- 💬 Positive feedback on explainability
- 🎤 Smooth demo with 0 crashes

### Post-Hackathon Success
- 🚀 3-5 pilot customers in 6 months
- 💰 $50K+ ARR in 12 months
- 📈 100+ paying users in 18 months
- 🔗 Partnership with LandingAI or AWS

---

## FAQ

### Q: How accurate is ArthaNethra's risk detection?
**A:** Hybrid approach ensures reliability:
- Numeric rules validate thresholds (100% deterministic)
- LLM identifies contextual anomalies (validated by citations)
- Users can always verify via evidence viewer

### Q: Can it handle documents in other languages?
**A:** Currently English-only, but easily extensible:
- ADE supports multi-language extraction
- Claude 3 is multilingual
- Future: Add language-specific fine-tuning

### Q: What about data privacy?
**A:** Privacy is core:
- Documents stored locally (dev) or encrypted S3 (prod)
- No PII in graph (only entity names + metrics)
- API keys managed securely (env vars)
- Optional: Self-hosted Weaviate/Neo4j

### Q: How do I integrate ArthaNethra into my workflow?
**A:** Multiple integration options:
- **Web UI** (current) — upload, query, visualize
- **API** (future) — programmatic access
- **Slack/Teams** (future) — chatbot integration
- **Excel plugin** (future) — export graph to spreadsheet

### Q: What's the cost to run ArthaNethra?
**A:** Local demo is free (except ADE/Bedrock APIs):
- ADE: ~$0.10 per document (first 100 free via hackathon)
- Bedrock: ~$0.003 per 1K tokens
- Production: Scale with AWS pricing

---

## Conclusion

**ArthaNethra** combines the best of modern AI (LLMs, vectors, graphs) with the practical needs of financial analysts. It doesn't replace humans — it empowers them with superhuman speed, accuracy, and explainability.

**The vision:** Every financial document becomes a node in a global knowledge graph. Every risk is detected automatically. Every claim is backed by evidence.

**The mission:** Build the AI-powered financial intelligence platform that analysts wish they had.

---

## Contact & Links

- **Demo:** [Live URL (to be added)]
- **GitHub:** [Repository link (to be added)]
- **Team:** [Team info (to be added)]
- **Hackathon:** Financial AI Hackathon Championship 2025

---

**Let's build the future of financial intelligence!** 🚀


# 🎯 Remaining Features & Implementation Gaps

**Date:** November 3, 2025  
**Project:** ArthaNethra  
**Status:** Pre-Hackathon Assessment

---

## ✅ **What's Complete & Working**

### Backend (FastAPI):
- ✅ Document upload & validation
- ✅ LandingAI ADE integration (Parse + Extract APIs)
- ✅ Async httpx client with retry/backoff
- ✅ Adaptive schema generation with Claude
- ✅ Knowledge graph normalization (entities + edges)
- ✅ Property-based & heuristic edge creation
- ✅ Rule-based risk detection
- ✅ AI chatbot with tool calling (graph_query, doc_lookup, metric_compute)
- ✅ PDF evidence viewer endpoint
- ✅ Job tracking & progress monitoring
- ✅ All CRUD endpoints for entities/risks/analytics
- ✅ Health check with service status

### Frontend (Angular):
- ✅ Document upload UI with drag-drop
- ✅ Graph visualization (Sigma.js)
- ✅ Chat interface with streaming
- ✅ Dashboard with statistics
- ✅ Document listing
- ✅ Risk display
- ✅ Job tracking UI
- ✅ Extraction schema selection

### Infrastructure:
- ✅ Docker Compose setup
- ✅ Weaviate configuration (optional)
- ✅ Neo4j configuration (optional)

---

## 🔴 **Critical Missing Features (Hackathon Blockers)**

### 1. ❌ **Risk Persistence**
**Issue:** Risks are computed on-demand but not stored

**Current State:**
```python
# backend/main.py - risks are returned but not persisted
@app.post(f"{settings.API_PREFIX}/risk")
async def detect_risks(graph_id: str):
    risks = await risk_detection_service.detect_risks(...)
    return {"risks": [r.model_dump() for r in risks]}  # ← Not stored!
```

**Missing:**
- Risk storage in `graphs_store` or database
- Risk retrieval from storage
- Risk history tracking

**Impact:** 
- Frontend `/risks` page is empty
- Cannot track risks over time
- Analytics dashboard shows 0 risks

**Fix Required:**
```python
# Store risks after detection
risks_store[graph_id] = risks

# Update endpoints to return stored risks
@app.get(f"{settings.API_PREFIX}/risks")
async def list_risks():
    all_risks = []
    for risks in risks_store.values():
        all_risks.extend([r.model_dump() for r in risks])
    return all_risks
```

**Priority:** 🔴 **CRITICAL**

---

### 2. ❌ **PDF Evidence Viewer (Frontend)**
**Issue:** Backend serves PDFs but frontend doesn't display them

**Current State:**
- ✅ Backend: `GET /api/v1/evidence/{document_id}?page=X` works
- ❌ Frontend: No PDF viewer component

**Missing:**
- PDF viewer component (ngx-extended-pdf-viewer)
- Route for `/evidence/:documentId`
- Page highlighting functionality

**From TODO list:**
```typescript
// frontend/README.md
- [ ] Add ngx-extended-pdf-viewer for evidence viewing
```

**Impact:**
- Users can't verify citations
- "Open Source" buttons don't work
- Explainability feature incomplete

**Fix Required:**
1. Install `ngx-extended-pdf-viewer`
2. Create `EvidenceViewerComponent`
3. Add route `/evidence/:documentId`
4. Implement page highlighting

**Priority:** 🔴 **CRITICAL** (for explainability demo)

---

### 3. ⚠️ **Adaptive Schema UI Toggle**
**Issue:** Backend supports adaptive schema but no UI to enable it

**Current State:**
- ✅ Backend: `use_adaptive_schema` parameter works
- ✅ Frontend API: Parameter added to `extractDocument()`
- ❌ Frontend UI: No checkbox/toggle to enable it

**Missing:**
- Checkbox in upload component: "🤖 Use AI to generate optimal schema"
- Help text explaining adaptive schema
- Loading indicator for schema generation

**Fix Required:**
```typescript
// upload.component.ts
useAdaptiveSchema = false;

// In template
<label>
  <input type="checkbox" [(ngModel)]="useAdaptiveSchema">
  🤖 Use AI to generate optimal schema (powered by Claude)
</label>

// In extraction call
this.apiService.extractDocument(
  this.currentDocument.id,
  this.selectedSchema,
  null,
  this.useAdaptiveSchema  // ← Pass flag
)
```

**Priority:** 🟠 **HIGH** (new feature needs UI)

---

## 🟡 **Medium Priority Gaps**

### 4. ⚠️ **Metric Computation Tool**
**Issue:** Chatbot has `metric_compute` tool but it's not implemented

**Current State:**
```python
# backend/services/chatbot.py
elif tool_name == "metric_compute":
    # TODO: Implement actual metric computation
    return {
        "metric_name": metric_name,
        "value": 0.0,  # ← Always returns 0!
        "entities_count": len(entity_ids)
    }
```

**Missing:**
- Actual metric aggregation logic
- Support for common metrics: total_debt, avg_rate, debt_ratio, revenue, etc.
- Entity filtering by type

**Impact:**
- Chatbot queries like "What's the total debt?" return 0
- Reduces chatbot usefulness

**Fix Required:**
```python
async def _compute_metric(self, metric_name: str, entity_ids: List[str]) -> float:
    """Compute aggregated metrics from entities"""
    entities = await self._get_entities(entity_ids)
    
    if metric_name == "total_debt":
        return sum(e.properties.get("principal", 0) for e in entities 
                   if e.type == EntityType.LOAN)
    elif metric_name == "avg_rate":
        rates = [e.properties.get("rate", 0) for e in entities 
                 if e.type == EntityType.LOAN]
        return sum(rates) / len(rates) if rates else 0
    # ... more metrics
```

**Priority:** 🟡 **MEDIUM**

---

### 5. ⚠️ **Risk Trend Analytics**
**Issue:** Analytics endpoint returns empty trends

**Current State:**
```python
@app.get(f"{settings.API_PREFIX}/analytics/risk-trends")
async def get_risk_trends():
    # TODO: Implement risk tracking over time
    return {
        "trends": [],  # ← Empty!
        "severity_distribution": {...}
    }
```

**Missing:**
- Risk timestamp tracking
- Trend calculation over time
- Severity distribution from stored risks

**Impact:**
- Dashboard analytics incomplete
- Cannot show risk evolution

**Fix Required:**
- Store risks with timestamps
- Aggregate by time period (daily/weekly)
- Calculate severity distribution from `risks_store`

**Priority:** 🟡 **MEDIUM**

---

### 6. ⚠️ **Database Persistence**
**Issue:** Everything stored in-memory, lost on restart

**Current State:**
```python
# backend/main.py
documents_store = {}  # ← In-memory only
graphs_store = {}
jobs_store = {}
risks_store = {}  # ← Needs to be added
```

**Missing:**
- PostgreSQL or SQLite database
- Database models (SQLAlchemy)
- Migration scripts
- Database initialization

**Impact:**
- Data lost on server restart
- Cannot scale horizontally
- Not production-ready

**Note:** Acceptable for hackathon demo, but document as limitation

**Priority:** 🟡 **MEDIUM** (post-hackathon)

---

## 🟢 **Low Priority / Nice-to-Have**

### 7. ⚠️ **Advanced Graph Visualization**
**Issue:** Basic graph works but missing advanced features

**Current Features:**
- ✅ Node/edge rendering
- ✅ Filters by entity type
- ✅ Search functionality
- ✅ Force-directed layout

**Missing:**
- ❌ Community detection coloring
- ❌ Path highlighting (between two nodes)
- ❌ Temporal graph (document versions)
- ❌ Export to image/SVG

**Priority:** 🟢 **LOW**

---

### 8. ⚠️ **Enhanced Risk Rules**
**Issue:** Only 4 basic risk rules implemented

**Current Rules:**
1. ✅ High variable rate (>8%)
2. ✅ High debt ratio (>0.6)
3. ✅ Negative cash flow
4. ✅ Approaching maturity (<12 months)

**Missing Common Rules:**
- ❌ Covenant violations (specific covenants)
- ❌ Currency mismatch risk
- ❌ Concentration risk (single lender >30%)
- ❌ Liquidity risk (current ratio <1.0)
- ❌ Credit rating changes
- ❌ Related party transactions

**Priority:** 🟢 **LOW** (can add more later)

---

### 9. ⚠️ **Multi-Document Comparison**
**Issue:** Each document processed independently

**Missing:**
- Cross-document entity resolution (same company in multiple docs)
- Consolidated graph across documents
- Discrepancy detection (Invoice vs GL)
- Timeline view (document versions)

**Priority:** 🟢 **LOW** (future feature)

---

### 10. ⚠️ **User Authentication**
**Issue:** No user management

**Missing:**
- User registration/login
- JWT token management
- Role-based access control
- API key management per user

**Note:** Not needed for hackathon demo

**Priority:** 🟢 **LOW** (post-hackathon)

---

### 11. ⚠️ **Testing**
**Issue:** No automated tests

**Missing:**
- Unit tests for services
- Integration tests for API endpoints
- Frontend component tests
- E2E tests

**Priority:** 🟢 **LOW** (but important for production)

---

### 12. ⚠️ **Rate Limiting & Monitoring**
**Issue:** No API protection or observability

**Missing:**
- Rate limiting per endpoint
- API usage tracking
- Error monitoring (Sentry)
- Performance metrics (Prometheus)
- Request logging

**Priority:** 🟢 **LOW** (post-hackathon)

---

## 📊 Feature Completeness Matrix

| Feature | Backend | Frontend | Docs | Priority | Status |
|---------|---------|----------|------|----------|--------|
| Document Upload | ✅ | ✅ | ✅ | 🔴 | Complete |
| ADE Extraction | ✅ | ✅ | ✅ | 🔴 | Complete |
| Adaptive Schema | ✅ | ⚠️ | ✅ | 🟠 | Backend only |
| Graph Normalization | ✅ | ✅ | ✅ | 🔴 | Complete |
| Risk Detection | ✅ | ✅ | ✅ | 🔴 | Complete |
| **Risk Persistence** | ❌ | ❌ | ✅ | 🔴 | **Missing** |
| **PDF Viewer** | ✅ | ❌ | ✅ | 🔴 | **Missing** |
| Chatbot | ✅ | ✅ | ✅ | 🔴 | Complete |
| **Metric Compute** | ⚠️ | ✅ | ✅ | 🟡 | Stub only |
| Graph Visualization | ✅ | ✅ | ✅ | 🔴 | Complete |
| Job Tracking | ✅ | ✅ | ✅ | 🔴 | Complete |
| Analytics Dashboard | ⚠️ | ✅ | ✅ | 🟡 | Partial |
| Evidence Linking | ✅ | ⚠️ | ✅ | 🔴 | Backend only |
| Database | ❌ | N/A | ✅ | 🟡 | In-memory only |
| Authentication | ❌ | ❌ | ✅ | 🟢 | Not started |
| Testing | ❌ | ❌ | ❌ | 🟢 | Not started |

**Legend:**
- ✅ Complete and working
- ⚠️ Partial or stub
- ❌ Missing
- N/A Not applicable

---

## 🎯 Hackathon MVP Requirements

### Mandatory (Must Have):
1. ✅ LandingAI ADE integration
2. ✅ AWS Bedrock integration
3. ✅ Working prototype (upload → extract → graph → chat)
4. ✅ Documentation
5. 🔴 **Evidence viewer** ← **Critical gap**
6. 🔴 **Risk persistence** ← **Critical gap**

### Optional (Should Have):
7. 🟠 Adaptive schema UI toggle
8. 🟡 Metric computation
9. 🟡 Analytics dashboard completion

### Not Required:
- Database persistence (in-memory OK)
- Authentication (demo doesn't need it)
- Testing (demo doesn't need it)
- Advanced features

---

## 🚀 Implementation Roadmap

### Phase 1: Critical Fixes (Before Hackathon) - **4-6 hours**
1. **Risk Persistence** (2 hours)
   - Add `risks_store` dictionary
   - Update risk endpoints to store/retrieve
   - Update analytics to show real risk counts

2. **PDF Evidence Viewer** (2-3 hours)
   - Install `ngx-extended-pdf-viewer`
   - Create `EvidenceViewerComponent`
   - Add route and navigation
   - Test with sample PDFs

3. **Adaptive Schema UI** (1 hour)
   - Add checkbox to upload component
   - Wire up to API call
   - Add help text

### Phase 2: Medium Priority (If Time) - **2-3 hours**
4. **Metric Computation** (1-2 hours)
   - Implement basic metrics (total_debt, avg_rate)
   - Test with chatbot queries

5. **Analytics Enhancement** (1 hour)
   - Calculate risk trends from stored risks
   - Show severity distribution

### Phase 3: Polish (If Time) - **2-3 hours**
6. **Error Handling**
   - Better error messages
   - Loading states
   - Graceful degradation

7. **UI Polish**
   - Consistent styling
   - Better transitions
   - Helpful tooltips

8. **Demo Preparation**
   - Sample documents
   - Demo script
   - Backup video

---

## 📝 Recommended Action Plan

### 🔴 **CRITICAL - Fix Before Demo:**
1. ✅ Implement risk persistence (2 hours)
2. ✅ Add PDF evidence viewer (3 hours)
3. ✅ Add adaptive schema UI toggle (1 hour)

**Total: 6 hours** ← **Must complete**

### 🟡 **OPTIONAL - If Time Permits:**
4. Implement metric computation (2 hours)
5. Complete analytics dashboard (1 hour)

**Total: +3 hours**

### 🟢 **SKIP for Hackathon:**
- Database migration
- Authentication
- Testing
- Advanced features

---

## 🎬 Demo Workarounds

If unable to complete all features, use these workarounds:

### For Missing PDF Viewer:
- **Workaround:** Open PDFs in separate tab/window
- **Demo Script:** "When you click 'Open Source', the PDF opens to the exact page with the evidence"

### For Missing Risk Persistence:
- **Workaround:** Detect risks live during demo
- **Demo Script:** "Let's run risk detection... here are the risks found"

### For Missing Metric Computation:
- **Workaround:** Show entities instead
- **Demo Script:** "Here are all the loan entities with their rates..."

---

## 🏆 Success Criteria

### Minimum Viable Demo:
- ✅ Upload document
- ✅ Extract with ADE (show JSON)
- ✅ Show graph visualization
- ✅ Query with chatbot
- ⚠️ Show evidence (workaround OK)
- ✅ Highlight citations

### Ideal Demo:
- ✅ All of the above
- ✅ PDF viewer with page highlighting
- ✅ Risk detection with persistence
- ✅ Adaptive schema selection
- ✅ Metric computation
- ✅ Full analytics dashboard

---

## 📞 Questions to Resolve

1. **Do we have sample financial documents ready?**
   - Need: 10-K filing, loan agreement, invoice

2. **Are API keys configured and tested?**
   - LandingAI API key
   - AWS credentials (Bedrock access)

3. **Is Docker Compose setup tested end-to-end?**
   - All services start correctly
   - No port conflicts

4. **Is the demo script prepared?**
   - Timing under 4 minutes
   - Backup video recorded

---

## 🎯 Final Recommendation

**Focus on these 3 critical items:**

1. 🔴 **Risk Persistence** (2 hrs) - Makes dashboard and risk page work
2. 🔴 **PDF Evidence Viewer** (3 hrs) - Core explainability feature
3. 🟠 **Adaptive Schema UI** (1 hr) - Showcases new AI feature

**Total: 6 hours of focused work**

Everything else can be demo'd with workarounds or is not required for hackathon success.

---

**Status:** Ready to implement critical features  
**Timeline:** 6 hours to demo-ready  
**Confidence:** HIGH - All infrastructure is in place, just need final UI/storage layers

🚀 **Let's build!**


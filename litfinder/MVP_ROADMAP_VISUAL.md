# LitFinder MVP: Visual Roadmap

## Quick Status Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  LITFINDER MVP PROGRESS                            15% Complete │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│                                                                  │
│  Week 1-2 [██████████] 70%  ← YOU ARE HERE                     │
│  Week 3-4 [░░░░░░░░░░]  0%                                      │
│  Week 5-6 [░░░░░░░░░░]  0%                                      │
│  Week 7   [░░░░░░░░░░]  0%                                      │
│  Week 8   [░░░░░░░░░░]  0%  → FIRST DEMO                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Feature Implementation Matrix

```
┌───────────────────────────────────────────────────────────────────────────┐
│ Feature                    │ Elicit Equivalent    │ Status     │ Priority │
├────────────────────────────┼──────────────────────┼────────────┼──────────┤
│ 1. Research Assistant      │ Elicit AI Search     │ ✅ DONE    │   P0     │
│ 2. Table Data Extraction   │ Elicit Extract       │ ❌ TODO    │   P0     │
│ 3. Chat with Library       │ Chat with Papers     │ ❌ TODO    │   P0     │
│ 4. Systematic Reviews      │ Review Pipeline      │ ❌ TODO    │   P1     │
│ 5. Concept Map             │ Concepts Tool        │ ❌ TODO    │   P1     │
│ 6. Alerts & Monitoring     │ Elicit Alerts        │ ❌ TODO    │   P2     │
│ 7. Reference Check         │ Scite Ref Check      │ ❌ TODO    │   P2     │
│ 8. GOST Formatter          │ ⭐ UNIQUE            │ ❌ TODO    │   P0     │
├────────────────────────────┼──────────────────────┼────────────┼──────────┤
│ Foundation: Auth           │ Standard             │ ⏳ 80%     │   P0     │
│ Foundation: Collections    │ Standard             │ ❌ TODO    │   P0     │
│ Foundation: OpenAlex       │ Standard             │ ⏳ 70%     │   P0     │
│ Foundation: Frontend       │ Standard             │ ❌ TODO    │   P0     │
└────────────────────────────┴──────────────────────┴────────────┴──────────┘

Legend: ✅ Done  ⏳ In Progress  ❌ Not Started
```

## 8-Week Development Timeline

```
Week 1-2: FOUNDATION (70% complete)
┌────────────────────────────────────────────────────────┐
│ ✅ Database schema (pgvector, users, articles)         │
│ ✅ Feature 1: Research Assistant (RAG)                 │
│ ✅ LLM service (Claude 4.x integration)                │
│ ✅ Embedding service (Gemini 768-dim)                  │
│ ✅ Cache service (Redis)                               │
│ ⏳ Auth system (JWT) - needs polish                    │
│ ⏳ OpenAlex integration - needs pagination             │
│ ❌ Collections CRUD - in progress                      │
└────────────────────────────────────────────────────────┘
                      ↓
Week 3-4: COLLECTIONS + GOST
┌────────────────────────────────────────────────────────┐
│ ❌ Collections CRUD endpoints                          │
│ ❌ Feature 8: GOST Formatter (VAK RB + GOST R)        │
│ ❌ Batch formatting                                    │
│ ❌ Export (.docx, .txt, BibTeX, JSON)                 │
└────────────────────────────────────────────────────────┘
                      ↓
Week 5-6: CORE AI FEATURES
┌────────────────────────────────────────────────────────┐
│ ❌ Feature 2: Table Data Extraction                    │
│    - Extraction jobs pipeline                          │
│    - Field-based LLM extraction (Haiku)                │
│    - Progress tracking                                 │
│ ❌ Feature 3: Chat with Library                        │
│    - Document chunking (512 tokens, 50 overlap)        │
│    - Semantic retrieval from chunks                    │
│    - Conversational LLM (Sonnet 4)                     │
│ ❌ Research Assistant optimization                     │
│    - Response streaming                                │
│    - Performance: P95 6s → 4s                          │
└────────────────────────────────────────────────────────┘
                      ↓
Week 7: REVIEW WORKFLOW + CONCEPT MAP
┌────────────────────────────────────────────────────────┐
│ ❌ Feature 4: Systematic Review Workflow               │
│    - Review management (state machine)                 │
│    - AI-assisted screening (Haiku)                     │
│    - Batch processing with statistics                  │
│ ❌ Feature 5: Concept Map                              │
│    - Concept extraction from topic                     │
│    - LLM clustering (Sonnet)                           │
│    - Graph generation                                  │
│ ❌ Frontend kickoff (Next.js + React + Tailwind)      │
└────────────────────────────────────────────────────────┘
                      ↓
Week 8: FRONTEND MVP + POLISH
┌────────────────────────────────────────────────────────┐
│ ❌ Core pages implementation                           │
│    - Home, Search, Collections, Research, Chat        │
│    - Data Extraction, Reviews, Concept Map            │
│ ❌ API integration with authentication                 │
│ ❌ Integration testing                                 │
│ ❌ UI/UX polish                                        │
└────────────────────────────────────────────────────────┘
                      ↓
            🎉 FIRST DEMO READY 🎉
```

## Feature Priority Matrix (MoSCoW)

```
┌─────────────────────────────────────────────────────┐
│ MUST HAVE (Week 1-6) - P0                           │
├─────────────────────────────────────────────────────┤
│ • Research Assistant (RAG)            ✅ DONE       │
│ • Table Data Extraction               ❌ Week 5-6   │
│ • Chat with Library                   ❌ Week 5-6   │
│ • GOST Formatter (unique)             ❌ Week 3-4   │
│ • Collections Management              ❌ Week 2-3   │
│ • Authentication                      ⏳ Week 2     │
│ • OpenAlex Search                     ⏳ Week 2     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ SHOULD HAVE (Week 7-8) - P1                         │
├─────────────────────────────────────────────────────┤
│ • Systematic Review Workflow          ❌ Week 7     │
│ • Concept Map                         ❌ Week 7     │
│ • Frontend MVP                        ❌ Week 8     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ COULD HAVE (Post-MVP) - P2                          │
├─────────────────────────────────────────────────────┤
│ • Alerts & Monitoring                 ❌ Week 9+    │
│ • Reference Check                     ❌ Week 11+   │
│ • Email verification                  ❌ Post-MVP   │
│ • OAuth2 providers                    ❌ Post-MVP   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ WON'T HAVE (Phase 2)                                │
├─────────────────────────────────────────────────────┤
│ • Collaboration features              ❌ Phase 2    │
│ • Mobile app                          ❌ Phase 2    │
│ • Institutional subscriptions         ❌ Phase 2    │
│ • Advanced analytics                  ❌ Phase 2    │
└─────────────────────────────────────────────────────┘
```

## User Journey at First Demo (Week 8)

```
┌───────────────────────────────────────────────────────────────────┐
│  1. DISCOVER                                                      │
│     User lands on homepage → sees clean search interface          │
│     [✅ Implemented in Week 8]                                    │
├───────────────────────────────────────────────────────────────────┤
│  2. SEARCH & ANSWER                                               │
│     Types query "machine learning for NLP"                        │
│     → Research Assistant generates AI answer with citations       │
│     [✅ Already working - Feature 1]                              │
├───────────────────────────────────────────────────────────────────┤
│  3. COLLECT                                                       │
│     Creates collection "My PhD Research"                          │
│     Adds 20 relevant papers to collection                         │
│     [✅ Implemented in Week 3-4]                                  │
├───────────────────────────────────────────────────────────────────┤
│  4. EXTRACT DATA                                                  │
│     Opens collection → clicks "Extract Data"                      │
│     Defines fields: Sample Size, Methodology, Main Finding        │
│     → Gets structured table with 20 rows                          │
│     [✅ Implemented in Week 5-6]                                  │
├───────────────────────────────────────────────────────────────────┤
│  5. CHAT                                                          │
│     Opens "Chat" tab in collection                                │
│     Asks: "What are the main controversies?"                      │
│     → AI responds with citations from collection                  │
│     [✅ Implemented in Week 5-6]                                  │
├───────────────────────────────────────────────────────────────────┤
│  6. FORMAT & EXPORT                                               │
│     Clicks "Format Bibliography"                                  │
│     Selects "VAK RB" standard                                     │
│     → Exports .docx with GOST-formatted references                │
│     [✅ Implemented in Week 3-4]                                  │
└───────────────────────────────────────────────────────────────────┘

🎯 Result: Complete workflow from search to formatted bibliography in 6 steps
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         LITFINDER MVP                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FRONTEND (Next.js 14 + React 18 + Tailwind)            │  │
│  │  - Homepage                                              │  │
│  │  - Search & Research Assistant                           │  │
│  │  - Collections Management                                │  │
│  │  - Data Extraction Interface                             │  │
│  │  - Chat Interface                                        │  │
│  │  - Review Workflow                                       │  │
│  │  - Concept Map Visualization                             │  │
│  │  - GOST Formatter                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↕ REST API                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  BACKEND API (FastAPI + Uvicorn)                        │  │
│  │  ┌─────────────────────────────────────────────────┐    │  │
│  │  │ API Endpoints                                    │    │  │
│  │  │ • /auth (JWT authentication)                     │    │  │
│  │  │ • /search (OpenAlex integration)                 │    │  │
│  │  │ • /collections (CRUD operations)                 │    │  │
│  │  │ • /research/answer (RAG pipeline)                │    │  │
│  │  │ • /extraction (data extraction jobs)             │    │  │
│  │  │ • /chat (conversational RAG)                     │    │  │
│  │  │ • /reviews (systematic review workflow)          │    │  │
│  │  │ • /concepts (concept map generation)             │    │  │
│  │  │ • /format (GOST formatter)                       │    │  │
│  │  └─────────────────────────────────────────────────┘    │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────┐    │  │
│  │  │ Services                                         │    │  │
│  │  │ • LLM Service (Claude 4.x routing)               │    │  │
│  │  │ • Embedding Service (Gemini 768-dim)             │    │  │
│  │  │ • Cache Service (Redis)                          │    │  │
│  │  └─────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↕                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  DATA LAYER                                              │  │
│  │  • PostgreSQL 15 + pgvector (articles, embeddings)       │  │
│  │  • Redis 7 (caching, sessions)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↕                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  EXTERNAL APIS                                           │  │
│  │  • OpenAlex (article search & metadata)                  │  │
│  │  • Claude API (LLM generation)                           │  │
│  │  • Gemini API (embeddings)                               │  │
│  │  • GOST Formatter Agent (bibliography formatting)        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Cost Breakdown (1000 Active Users)

```
┌────────────────────────────────────────────────────┐
│  MONTHLY OPERATING COSTS                           │
├────────────────────────────────────────────────────┤
│                                                     │
│  LLM APIs:                              $659/month │
│  ├─ Research Answer (Sonnet 4)           $150     │
│  ├─ Chat with Library (Sonnet 4)         $225     │
│  ├─ Data Extraction (Haiku 4.5)          $30      │
│  ├─ Screening (Haiku 4.5)                $60      │
│  ├─ Concept Map (Sonnet 4)               $60      │
│  ├─ Reference Check (Haiku 4.5)          $24      │
│  ├─ GOST Formatter (Haiku 4.5)           $90      │
│  └─ Embeddings (OpenAI)                  $20      │
│                                                     │
│  Infrastructure (Yandex Cloud):         $280/month │
│  ├─ Backend API (2 vCPU, 4GB RAM)        $150     │
│  ├─ Database (2 vCPU, 8GB RAM)           $80      │
│  ├─ Cache (1 vCPU, 2GB RAM)              $20      │
│  └─ Network + Storage                    $30      │
│                                                     │
│  Other:                                 $60/month  │
│  ├─ Domain + SSL                         $10      │
│  └─ External services                    $50      │
│                                                     │
│  ─────────────────────────────────────────────────│
│  TOTAL:                                $999/month  │
│  Cost per user:                        ~$1.00/mo   │
│                                                     │
│  Annual: $12,000/year for 1000 users               │
└────────────────────────────────────────────────────┘

🎯 Target: Keep cost under $1.50/user/month for profitability
```

## Key Milestones & Checkpoints

```
✅ MILESTONE 1: Foundation Complete (Week 2)
   • Database schema with pgvector
   • Feature 1: Research Assistant working
   • Auth + Collections + OpenAlex ready
   • All services containerized

⏳ MILESTONE 2: GOST Formatting Live (Week 4)
   • Users can create collections
   • GOST formatter integration complete
   • Export to .docx, BibTeX, JSON
   • First unique value proposition live

⏳ MILESTONE 3: Core AI Features (Week 6)
   • Data extraction pipeline working
   • Chat with library functional
   • Research Assistant optimized (P95 ≤4s)
   • All 3 core AI features deployed

⏳ MILESTONE 4: Complete Backend (Week 7)
   • Systematic review workflow
   • Concept map generation
   • All 8 backend features complete
   • API fully documented

🎯 MILESTONE 5: FIRST DEMO (Week 8)
   • Frontend MVP deployed
   • End-to-end user flows working
   • All features accessible via UI
   • Ready for pilot users (BGU students)
```

## Success Metrics Dashboard

```
┌────────────────────────────────────────────────────────────────┐
│  MVP SUCCESS METRICS (First 3 Months)                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Product Metrics:                                              │
│  • Registered users:              ≥100  [Current: TBD]         │
│  • Active users (weekly):         ≥30   [Current: TBD]         │
│  • Collections created:           ≥50   [Current: TBD]         │
│  • Articles added:                ≥1000 [Current: TBD]         │
│  • Retention rate (D7):           ≥30%  [Current: TBD]         │
│                                                                 │
│  Feature Adoption:                                             │
│  • Research Answer tried:         ≥50%  [Current: TBD]         │
│  • Data Extraction used:          ≥20%  [Current: TBD]         │
│  • Chat with Library used:        ≥30%  [Current: TBD]         │
│  • GOST Formatting used:          ≥60%  [Current: TBD]         │
│                                                                 │
│  Performance:                                                  │
│  • Research Answer P95:           ≤4s   [Current: ~6s]         │
│  • Data Extraction P95:           ≤30s  [Current: N/A]         │
│  • Chat with Library P95:         ≤5s   [Current: N/A]         │
│  • API uptime:                    ≥99.5%[Current: TBD]         │
│                                                                 │
│  User Satisfaction:                                            │
│  • NPS:                           ≥40   [Current: TBD]         │
│  • CSAT:                          ≥4.0  [Current: TBD]         │
│  • Feature usefulness:            ≥4.2  [Current: TBD]         │
│                                                                 │
└────────────────────────────────────────────────────────────────┘

Legend: TBD = To Be Determined (after first demo launch)
```

## What Makes LitFinder Different from Elicit

```
┌─────────────────────────────────────────────────────────────────┐
│  UNIQUE DIFFERENTIATION FACTORS                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ⭐ GOST Formatting (Feature 8)                                 │
│     • VAK RB (Belarus) standard                                 │
│     • GOST R 7.0.100-2018 (Russia, Kazakhstan)                  │
│     • Export to .docx with perfect formatting                   │
│     • Unique to CIS academic market                             │
│                                                                  │
│  🌍 Native Russian Language Support                            │
│     • Full UI in Russian and English                            │
│     • Russian academic paper support                            │
│     • Multilingual embeddings (Gemini)                          │
│                                                                  │
│  💰 10x More Affordable                                         │
│     • $1/user/month vs $10-50/user/month for Elicit            │
│     • Cost optimization via Haiku for fast tasks                │
│     • Aggressive caching (1-hour TTL)                           │
│                                                                  │
│  🚀 Modern Tech Stack                                           │
│     • FastAPI (faster than Django/Flask)                        │
│     • Next.js 14 (App Router)                                   │
│     • Claude 4.x (200K context, superior reasoning)             │
│     • pgvector (native PostgreSQL, no separate vector DB)       │
│                                                                  │
│  🎯 CIS Market Focus                                            │
│     • Built for Russian/Belarusian/Kazakh researchers           │
│     • Understands local academic requirements                   │
│     • Integration with local databases (eLIBRARY in Phase 2)    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Commands Cheatsheet

```bash
# Start all services
docker compose up -d

# Run database migrations
docker compose exec api alembic upgrade head

# Generate embeddings for existing articles
docker compose exec api python app/scripts/generate_embeddings.py

# Run tests
docker compose exec api pytest

# Check API health
curl http://localhost:8000/health

# Test Research Assistant
curl -X POST http://localhost:8000/api/v1/research/answer \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "machine learning", "max_results": 5}'

# View logs
docker compose logs -f api

# Stop all services
docker compose down
```

---

**Last Updated:** February 13, 2026
**Next Checkpoint:** End of Week 2 (Foundation complete)
**Contact:** See LITFINDER_MVP_IMPLEMENTATION_PLAN.md for full details

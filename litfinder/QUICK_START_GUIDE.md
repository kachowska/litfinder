# LitFinder MVP: Quick Start Guide

**For developers joining the project**

## TL;DR: Where We Are

- **Status:** Week 1.5/8 (~15% complete)
- **What Works:** Research Assistant (RAG) with semantic search + AI answers
- **What's Next:** Collections CRUD (Week 2), then GOST Formatter (Week 3-4)
- **First Demo:** End of Week 8

## ✅ What's Already Implemented

### Feature 1: Research Assistant (100% Complete)

- `POST /api/v1/research/answer` - AI-powered semantic search with answer synthesis
- Vector similarity search using pgvector + HNSW index
- Claude Sonnet 4 for answer generation with citations [1], [2], etc.
- Redis caching (1-hour TTL)
- Filters: year_from, year_to, language, max_results
- Performance: P95 ~6s (target: ~3s after optimization)

**Files:**

- `backend/app/api/research.py`
- `backend/alembic/versions/003_add_vector_index.py`
- `backend/app/scripts/generate_embeddings.py`
- `FEATURE_1_RESEARCH_ASSISTANT.md`

### Foundation Services (80-100%)

- ✅ Database: PostgreSQL 15 + pgvector extension
- ✅ LLM Service: Claude 4.x integration with task-based routing
- ✅ Embedding Service: Gemini text-embedding-004 (768-dim)
- ✅ Cache Service: Redis caching layer
- ⏳ Auth Service: JWT tokens (access + refresh) - needs polish
- ⏳ OpenAlex Integration: Basic search - needs cursor pagination

## ❌ What's NOT Done Yet (Coming Soon)

### Week 2 (Current): Foundation Polish

- [ ] Collections CRUD endpoints (PostgreSQL tables + FastAPI endpoints)
- [ ] Auth system polish (fix refresh flow bugs)
- [ ] OpenAlex cursor pagination (for >100 results)

### Week 3-4: Collections + GOST

- [ ] Feature 8: GOST Formatter (VAK RB + GOST R bibliographies)
- [ ] Export functionality (.docx, .txt, BibTeX, JSON)

### Week 5-6: Core AI Features

- [ ] Feature 2: Table Data Extraction (structured data extraction)
- [ ] Feature 3: Chat with Library (conversational RAG)
- [ ] Research Assistant optimization (streaming, P95 ≤4s)

### Week 7: Reviews + Concept Map

- [ ] Feature 4: Systematic Review Workflow
- [ ] Feature 5: Concept Map

### Week 8: Frontend MVP

- [ ] Next.js 14 + React 18 + Tailwind
- [ ] All UI pages connected to backend
- [ ] 🎯 **FIRST DEMO READY**

## 📋 Immediate Action Items (This Week)

### Priority 1: Collections CRUD (2 days)

1. Create database migration:

```sql
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE collection_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    work_id TEXT NOT NULL,  -- OpenAlex ID
    added_at TIMESTAMP DEFAULT NOW(),
    notes TEXT
);
CREATE INDEX idx_collection_work ON collection_items(collection_id, work_id);
```

2. Implement endpoints in `backend/app/api/collections.py`:

- `POST /api/v1/collections` - Create collection
- `GET /api/v1/collections` - List user's collections
- `GET /api/v1/collections/{id}` - Get collection with items
- `PATCH /api/v1/collections/{id}` - Update collection
- `DELETE /api/v1/collections/{id}` - Delete collection
- `POST /api/v1/collections/{id}/items` - Add article
- `DELETE /api/v1/collections/{id}/items/{work_id}` - Remove article

3. Add tests and permission checks

### Priority 2: Auth Polish (0.5 day)

- Fix JWT refresh token flow bugs
- Add proper error messages
- Test edge cases

### Priority 3: OpenAlex Polish (0.5 day)

- Add cursor-based pagination
- Add more filters (cited_by_count, concepts)
- Add retry logic for API failures

## 📦 Prerequisites

Before running LitFinder, ensure you have the following installed and configured:

### Required Tools

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ (included with Docker Desktop)
- **Git** 2.30+ ([Install Git](https://git-scm.com/downloads))
- **Python** 3.11+ (for local development/testing - optional if using Docker only)

### System Requirements

- **RAM**: ≥4GB available (8GB recommended)
- **Disk Space**: ≥10GB free (for Docker images, database, embeddings)
- **OS**: Linux, macOS, or Windows with WSL2

### Required API Keys

You'll need API keys from the following services:

1. **Anthropic Claude API** (for LLM features)
   - Sign up at: [https://console.anthropic.com](https://console.anthropic.com)
   - Get your API key: `sk-ant-...`
   - Used for: Research Assistant, answer generation, chat features

2. **Google Gemini API** (for embeddings)
   - Sign up at: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
   - Get your API key
   - Used for: Document embeddings (768-dimensional vectors)

### Optional (for full features)

- **OpenAlex** - Free API, no key required
  - Provide your email in `.env` for "polite pool" (faster rate limits)
  - `OPENALEX_EMAIL=your@email.com`

### Verification Commands

```bash
# Check Docker
docker --version  # Should be 20.10+
docker compose version  # Should be 2.0+

# Check Git
git --version  # Should be 2.30+

# Check Python (optional)
python3 --version  # Should be 3.11+
```

## 🚀 Quick Start Commands

```bash
# Clone and setup
git clone <repo_url>
cd litfinder
cp .env.example .env  # Add your API keys

# Start all services
docker compose up -d

# Run migrations
docker compose exec api alembic upgrade head

# Generate embeddings (if you have articles)
docker compose exec api python app/scripts/generate_embeddings.py

# Test Research Assistant
curl -X POST http://localhost:8000/api/v1/research/answer \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "machine learning for natural language processing",
    "max_results": 5,
    "year_from": 2020
  }'

# Run tests
docker compose exec api pytest

# View logs
docker compose logs -f api
```

## 📚 Key Documentation Files

1. **LITFINDER_MVP_IMPLEMENTATION_PLAN.md** - Comprehensive 10-section plan with all features, timelines, and requirements
2. **MVP_ROADMAP_VISUAL.md** - Visual diagrams and progress tracking
3. **FEATURE_1_RESEARCH_ASSISTANT.md** - Complete documentation of Research Assistant feature
4. **QUICK_START_GUIDE.md** (this file) - Quick reference for developers

## 🎯 Success Criteria for First Demo (Week 8)

### Must Work:

- ✅ User registration and login
- ✅ Search papers via OpenAlex
- ✅ Research Assistant (AI answers with citations)
- ✅ Create and manage collections
- ✅ Extract structured data from papers
- ✅ Chat with library (conversational RAG)
- ✅ Format bibliographies (GOST VAK RB / GOST R)
- ✅ Export collections (CSV, .docx, BibTeX)

### User Journey:

1. Register → Login
2. Search "machine learning NLP" → Get AI answer
3. Create collection "My PhD Research"
4. Add 20 papers to collection
5. Extract data: Sample Size, Methodology, Main Finding
6. Chat: "What are the main controversies?"
7. Format bibliography as VAK RB → Export to .docx

## 🔑 API Keys Needed

Add these to `.env`:

```bash
# LLM Services
CLAUDE_API_KEY=sk-ant-...           # From https://console.anthropic.com
GEMINI_API_KEY=...                  # From https://makersuite.google.com/app/apikey

# Database
DATABASE_URL=postgresql+asyncpg://...

# Cache
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET_KEY=...                  # Generate with: openssl rand -hex 32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# External APIs (optional for MVP)
OPENALEX_EMAIL=your@email.com      # For OpenAlex polite pool
```

## ⚠️ Common Pitfalls

1. **Missing pgvector extension:**

   ```bash
   docker compose exec db psql -U postgres -d litfinder -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```
2. **Articles without embeddings:**

   - Run `generate_embeddings.py` script
   - Or ensure GEMINI_API_KEY is set (otherwise uses mock mode)
3. **Research Assistant returns "No relevant articles found":**

   - Check if articles have embeddings: `SELECT COUNT(*) FROM articles WHERE embedding IS NOT NULL;`
   - If 0, run embedding generation script
4. **CORS errors (after frontend added):**

   - Update CORS settings in `backend/app/main.py`
   - Add frontend URL to allowed origins

## 📞 Getting Help

- **Full Plan:** See LITFINDER_MVP_IMPLEMENTATION_PLAN.md
- **Visual Guide:** See MVP_ROADMAP_VISUAL.md
- **Feature Docs:** See FEATURE_1_RESEARCH_ASSISTANT.md
- **Issues:** Create GitHub issue or contact team

## 🎓 Tech Stack Reference

**Backend:**

- FastAPI (Python 3.11+)
- PostgreSQL 15 + pgvector
- Redis 7
- SQLAlchemy (async)
- Alembic (migrations)
- Claude 4.x (LLM)
- Gemini text-embedding-004 (embeddings)

**Frontend (Week 7+):**

- Next.js 14 (App Router)
- React 18
- TypeScript
- TailwindCSS
- Shadcn/UI components

**Infrastructure:**

- Docker + Docker Compose
- Nginx (reverse proxy)
- Yandex Cloud or Vercel

## 🏆 Why This MVP Beats Elicit for CIS Market

1. **GOST Formatting** - Unique value prop (VAK RB + GOST R)
2. **Russian Language** - Native support for RU academic papers
3. **10x Cheaper** - $1/user/month vs $10-50/user/month
4. **Modern Stack** - FastAPI + Claude 4.x + pgvector
5. **Local Focus** - Built for CIS researchers, understands local requirements

---

**Last Updated:** February 13, 2026
**Current Phase:** Week 2 - Foundation Polish
**Next Milestone:** Collections CRUD complete by end of Week 2

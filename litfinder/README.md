# LitFinder - AI-powered Academic Literature Platform

ИИ-платформа для подбора академической литературы с семантическим поиском и генерацией библиографии по ГОСТ.

## 🚀 Quick Start

```bash
# Clone and setup
cd litfinder
cp .env.example .env
# Edit .env with your API keys

# Run with Docker
docker-compose up -d

# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

## 📁 Project Structure

```
litfinder/
├── backend/          # FastAPI Python backend
├── frontend/         # Next.js 14 web app
├── telegram_bot/     # aiogram 3.x bot
├── docs/             # Documentation
└── docker-compose.yml
```

## 🔧 Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, PostgreSQL + pgvector
- **Frontend**: Next.js 14, Tailwind CSS
- **Bot**: aiogram 3.x
- **LLM**: Claude API (Anthropic)
- **Integrations**: OpenAlex, CyberLeninka

## 📚 Documentation

- [TZ (Tech Spec)](../TZ_LitFinder_MVP_v1.0.md)
- [API Docs](http://localhost:8000/docs)

## 👥 Team

- Product Owner: [Your Name]
- Backend: [Your Name]
- Frontend: [Your Name]

---
**Version:** 0.1.0-mvp  
**License:** MIT

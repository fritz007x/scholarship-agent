# Scholarship Agent

Full-stack scholarship matching and application management platform with an AI-powered conversational agent.

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy (SQLite) + Pydantic
- **Frontend**: React 19 + Vite + Tailwind CSS + react-router-dom
- **LLM**: Google Gemini 1.5 Flash (via `google-generativeai`)
- **Auth**: JWT (python-jose) + bcrypt

## Project Structure

```
backend/
  app/
    main.py          # FastAPI entry point
    config.py        # Settings (from .env)
    database.py      # SQLAlchemy engine + session
    models/          # 8 ORM models (User, UserProfile, Scholarship, Application, Essay, Document, AgentSession, ScrapingJob)
    schemas/         # Pydantic request/response schemas
    services/        # Business logic (auth, profile, application, essay, document, agent, llm, scraper)
    routes/          # API routers (auth, profile, applications, essays, documents, scholarships, llm, agent, scraper)
    scraper/         # Web scraping framework (base, rss, edu scrapers + orchestrator)
    utils/           # Security helpers, prompt templates
  requirements.txt

frontend/
  src/
    main.jsx         # React entry
    App.jsx          # Router setup
    pages/           # 10 pages (Login, Register, Dashboard, Scholarships, ApplicationDetail, Profile, Essays, Documents, AgentChat, AdminScraper)
    components/      # Layout (Header, Layout) + common UI (Button, Card, Input, ProtectedRoute)
    contexts/        # AuthContext (global auth state)
    services/api.js  # Axios API client with JWT interceptor
  package.json
  vite.config.js
  tailwind.config.js
```

## Running the Project

```bash
# Backend (port 8000)
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configure GOOGLE_API_KEY, SECRET_KEY
uvicorn app.main:app --reload

# Frontend (port 5173)
cd frontend
npm install
npm run dev
```

## Key Architecture Patterns

- **ReAct Agent**: The AI agent uses a Reason+Act loop with tool calling (search scholarships, generate checklists, etc.). Limited to 5 iterations per message and 100k tokens per session.
- **Checklist System**: Applications auto-generate checklists from scholarship requirements (essays, documents, forms).
- **Essay/Document Reuse**: Essays and documents can be tagged and reused across multiple applications.
- **Scraping Pipeline**: Async scrapers (RSS, edu) with rate limiting, job queuing, and LLM-powered requirement extraction.

## API Routes

| Prefix | Auth | Purpose |
|--------|------|---------|
| `/auth` | None/Required | Register, login, JWT tokens |
| `/profile` | Required | User profile CRUD |
| `/applications` | Required | Application lifecycle + checklists |
| `/essays` | Required | Essay library CRUD |
| `/documents` | Required | File upload/download/versioning |
| `/scholarships` | Public | Search and filter scholarships |
| `/llm` | None | LLM parsing and match explanations |
| `/agent` | Required | Chat sessions and recommendations |
| `/scraper` | Admin | Scraping job control |

## Environment Variables

Backend `.env` requires: `SECRET_KEY`, `DATABASE_URL`, `GOOGLE_API_KEY`, `GEMINI_MODEL`, `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, `ACCESS_TOKEN_EXPIRE_DAYS`.

Frontend `.env` requires: `VITE_API_URL` (defaults to `http://localhost:8000`).

## Development Notes

- No git repository initialized yet
- SQLite used for development; switch to PostgreSQL for production
- CORS configured for local dev (localhost origins)
- No tests or Docker configuration present

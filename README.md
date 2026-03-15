# Scholarship Agent

A full-stack scholarship matching and application management platform with an AI-powered conversational agent. Helps students discover scholarships, track applications, manage essays and documents, and get personalized recommendations.

## Features

- **Scholarship Discovery** - Search and filter scholarships by category, amount, eligibility
- **AI Assistant** - Conversational agent powered by Google Gemini for personalized scholarship recommendations
- **Application Tracking** - Manage applications with auto-generated checklists and progress tracking
- **Essay Library** - Write, tag, and reuse essays across multiple applications
- **Document Management** - Upload and version transcripts, recommendations, and other files
- **Student Profile** - Comprehensive profile for academic, extracurricular, and demographic information
- **Automated Scraping** - Admin tools to scrape and parse scholarship data from RSS feeds and educational sites

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Vite, Tailwind CSS, React Router |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite (dev) / PostgreSQL (prod) |
| AI | Google Gemini 1.5 Flash |
| Auth | JWT + bcrypt |

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Google AI API key](https://aistudio.google.com/apikey) for Gemini

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY and a secure SECRET_KEY
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

## Project Structure

```
backend/
  app/
    main.py            # FastAPI application entry point
    config.py          # Environment-based settings
    database.py        # SQLAlchemy engine and session
    models/            # ORM models (User, Scholarship, Application, Essay, Document, etc.)
    schemas/           # Pydantic request/response schemas
    services/          # Business logic layer
    routes/            # API route handlers
    scraper/           # Web scraping framework
    utils/             # Security helpers and prompt templates

frontend/
  src/
    pages/             # Page components (Dashboard, Scholarships, AgentChat, etc.)
    components/        # Reusable UI components
    contexts/          # React Context (auth state)
    services/api.js    # Axios API client
```

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /auth/register` | Create account |
| `POST /auth/login` | Get JWT token |
| `GET /scholarships` | Search scholarships |
| `CRUD /applications` | Manage applications |
| `CRUD /essays` | Manage essays |
| `CRUD /documents` | Manage documents |
| `POST /agent/chat` | Chat with AI assistant |
| `POST /scraper/jobs` | Start scraping job (admin) |

## License

This project is for educational purposes.

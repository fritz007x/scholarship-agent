from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routes import auth, profile, applications, essays, documents, scholarships, llm, agent, scraper

# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Scholarship Agent API",
    description="Scholarship matching and application management system",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and CRA defaults
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(applications.router)
app.include_router(essays.router)
app.include_router(documents.router)
app.include_router(scholarships.router)
app.include_router(llm.router)
app.include_router(agent.router)
app.include_router(scraper.router)


@app.get("/")
def root():
    return {
        "message": "Scholarship Agent API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}

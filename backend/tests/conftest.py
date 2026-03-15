import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.scholarship import Scholarship
from app.utils.security import get_password_hash, create_access_token


SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("TestPass123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db):
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123"),
        is_admin=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_scholarship(db):
    scholarship = Scholarship(
        name="STEM Excellence Award",
        provider="Tech Foundation",
        description="For outstanding STEM students",
        award_amount=5000.0,
        eligibility={"gpa_minimum": 3.5, "majors": ["engineering", "computer science"]},
        application_requirements={
            "essays": [{"prompt": "Describe your passion for STEM", "word_count": 500}],
            "documents": ["transcript", "recommendation_letter"],
            "recommendations": 2,
            "other": ["Interview"]
        },
        keywords=["STEM", "engineering"],
        categories=["merit-based", "field-specific"]
    )
    db.add(scholarship)
    db.commit()
    db.refresh(scholarship)
    return scholarship

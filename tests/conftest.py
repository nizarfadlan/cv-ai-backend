import asyncio
import shutil
import sys
import tempfile
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings  # noqa: E402

settings.RATE_LIMIT_ENABLED = False

from app.core.rate_limiter.instance import get_rate_limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import get_db  # noqa: E402

# Test database setup
TEST_DATABASE_URL = f"postgresql+psycopg://{settings.POSTGRESQL_USER}:{settings.POSTGRESQL_PASSWORD}@{settings.POSTGRESQL_HOST}:{settings.POSTGRESQL_PORT}/cv_ai_test_db"
DEFAULT_DATABASE_URL = f"postgresql+psycopg://{settings.POSTGRESQL_USER}:{settings.POSTGRESQL_PASSWORD}@{settings.POSTGRESQL_HOST}:{settings.POSTGRESQL_PORT}/cv_ai_db"


def create_test_database():
    engine = create_engine(DEFAULT_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'cv_ai_test_db'")
            )
            if not result.fetchone():
                # Create database
                conn.execute(text("CREATE DATABASE cv_ai_test_db"))
                print("Test database created!")
            else:
                print("Test database already exists")
    except Exception as e:
        print(f"Error creating test database: {e}")
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def engine():
    create_test_database()

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_rate_limiter():
        class NoOpRateLimiter:
            async def is_allowed(self, *args, **kwargs):
                return True, None

            async def reset(self, *args, **kwargs):
                pass

            async def get_remaining(self, *args, **kwargs):
                return 999999

        return NoOpRateLimiter()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rate_limiter] = override_get_rate_limiter

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def temp_upload_dir():
    temp_dir = tempfile.mkdtemp()
    original_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = temp_dir

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    settings.UPLOAD_DIR = original_upload_dir


@pytest.fixture(scope="function")
def temp_chroma_dir():
    temp_dir = tempfile.mkdtemp()
    original_chroma_dir = settings.CHROMA_PERSIST_DIR
    settings.CHROMA_PERSIST_DIR = temp_dir

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    settings.CHROMA_PERSIST_DIR = original_chroma_dir


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Get path to test fixtures directory"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_cv_pdf_content(fixtures_dir: Path) -> bytes:
    pdf_file = fixtures_dir / "sample_cv.pdf"

    if not pdf_file.exists():
        raise FileNotFoundError(
            f"Sample PDF not found at {pdf_file}. "
            f"Please ensure tests/fixtures/sample_cv.pdf exists."
        )

    return pdf_file.read_bytes()


@pytest.fixture(scope="session")
def sample_project_pdf_content(fixtures_dir: Path) -> bytes:
    pdf_file = fixtures_dir / "sample_project.pdf"

    if not pdf_file.exists():
        pdf_file = fixtures_dir / "sample_cv.pdf"

    return pdf_file.read_bytes()


@pytest.fixture
def mock_llm_response():
    return {
        "cv_evaluation": {
            "technical_skills_score": 4,
            "experience_level_score": 3,
            "achievements_score": 4,
            "cultural_fit_score": 5,
            "cv_match_rate": 0.82,
            "feedback": "Strong technical skills with good experience",
        },
        "project_evaluation": {
            "correctness_score": 4,
            "code_quality_score": 5,
            "resilience_score": 4,
            "documentation_score": 5,
            "creativity_score": 3,
            "project_score": 4.5,
            "feedback": "Well-implemented solution with excellent documentation",
        },
        "summary": "Strong candidate with excellent technical skills and good project delivery",
    }


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

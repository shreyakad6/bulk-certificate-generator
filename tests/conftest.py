import os
import tempfile
import shutil
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.config import settings
from app.services.certificate_generator import certificate_service

import app.database as app_db

# Isolated SQLite in-memory test database using StaticPool
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Patch global database engine and session maker so background workers use test database
app_db.engine = engine
app_db.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure test environment variables and base directories are configured."""
    original_env = settings.APP_ENV
    settings.APP_ENV = "test"
    yield
    settings.APP_ENV = original_env


@pytest.fixture(autouse=True)
def isolate_database():
    """Create fresh database tables for each test and drop them afterward."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a standalone SQLAlchemy session for direct data setup and inspection."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def isolate_generated_storage():
    """Point file generation storage to a temporary directory for each test."""
    temp_dir = tempfile.mkdtemp(prefix="test_generated_")
    original_storage = settings.GENERATED_FILES_DIR
    original_service_dir = certificate_service.base_dir

    settings.GENERATED_FILES_DIR = temp_dir
    certificate_service.base_dir = temp_dir

    yield temp_dir

    settings.GENERATED_FILES_DIR = original_storage
    certificate_service.base_dir = original_service_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client configured with test database session overrides."""

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

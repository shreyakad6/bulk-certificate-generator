import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import GenerationJob, JobStatus


def test_job_status_completed(client: TestClient):
    """Test job status calculation and response fields for a fully completed job."""
    payload = {
        "event_name": "Docker & Kubernetes Workshop",
        "certificate_title": "Certificate of Participation",
        "event_date": "2026-10-07",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"},
        ],
    }

    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    res = client.get(f"/api/v1/jobs/{job_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["job_id"] == job_id
    assert data["status"] == "completed"
    assert data["total_count"] == 2
    assert data["successful_count"] == 2
    assert data["failed_count"] == 0
    assert data["pending_count"] == 0
    assert data["progress_percentage"] == 100.0
    assert data["completed_at"] is not None


def test_job_status_in_progress_calculation(client: TestClient, db_session: Session):
    """Test progress calculation when a job is currently marked as processing."""
    job_id = str(uuid.uuid4())
    job = GenerationJob(
        id=job_id,
        event_name="Cloud Architecture",
        certificate_title="Certificate of Attendance",
        event_date="2026-10-07",
        status=JobStatus.PROCESSING.value,
        total_count=100,
        successful_count=72,
        failed_count=3,
    )
    db_session.add(job)
    db_session.commit()

    res = client.get(f"/api/v1/jobs/{job_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["job_id"] == job_id
    assert data["status"] == "processing"
    assert data["total_count"] == 100
    assert data["successful_count"] == 72
    assert data["failed_count"] == 3
    assert data["pending_count"] == 25
    assert data["progress_percentage"] == 75.0
    assert data["completed_at"] is None


def test_job_status_completed_with_errors(client: TestClient, db_session: Session):
    """Test job status calculation when a job finishes with partial failures."""
    job_id = str(uuid.uuid4())
    job = GenerationJob(
        id=job_id,
        event_name="Security Summit",
        certificate_title="Certificate of Attendance",
        event_date="2026-10-07",
        status=JobStatus.COMPLETED_WITH_ERRORS.value,
        total_count=10,
        successful_count=8,
        failed_count=2,
        completed_at=datetime.utcnow(),
    )
    db_session.add(job)
    db_session.commit()

    res = client.get(f"/api/v1/jobs/{job_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "completed_with_errors"
    assert data["total_count"] == 10
    assert data["successful_count"] == 8
    assert data["failed_count"] == 2
    assert data["pending_count"] == 0
    assert data["progress_percentage"] == 100.0

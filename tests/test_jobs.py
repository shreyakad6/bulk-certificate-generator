import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import GenerationJob, Certificate, JobStatus


def test_create_generation_job_success(client: TestClient, db_session: Session):
    """Test POST /api/v1/jobs successfully initiates a job with 202 Accepted."""
    payload = {
        "event_name": "Python Workshop 2026",
        "certificate_title": "Certificate of Participation",
        "event_date": "2026-10-07",
        "recipients": [
            {"name": "Aarav Sharma", "email": "aarav@example.com"},
            {"name": "Priya Patil", "email": "priya@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()

    assert "job_id" in data
    assert data["total_count"] == 2
    assert "Certificate generation job created successfully" in data["message"]

    job_id = data["job_id"]

    # Verify database persistence after background processing
    db_session.expire_all()
    job = db_session.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    assert job is not None
    assert job.event_name == "Python Workshop 2026"
    assert job.certificate_title == "Certificate of Participation"
    assert job.total_count == 2

    # Because TestClient processes BackgroundTasks synchronously, job completes
    assert job.status in [JobStatus.COMPLETED.value, JobStatus.PROCESSING.value]
    assert job.successful_count == 2
    assert job.failed_count == 0

    certs = db_session.query(Certificate).filter(Certificate.job_id == job_id).all()
    assert len(certs) == 2
    names = {c.recipient_name for c in certs}
    assert names == {"Aarav Sharma", "Priya Patil"}


def test_get_job_not_found(client: TestClient):
    """Test GET /api/v1/jobs/{job_id} returns 404 for non-existent job UUID."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/jobs/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert f"Job with ID '{random_id}' not found" in data["detail"]


def test_list_job_certificates_pagination(client: TestClient, db_session: Session):
    """Test GET /api/v1/jobs/{job_id}/certificates returns paginated results."""
    recipients = [
        {"name": f"Student {i}", "email": f"student{i}@example.com"} for i in range(1, 11)
    ]
    payload = {
        "event_name": "Advanced FastApi Mastery",
        "certificate_title": "Certificate of Completion",
        "event_date": "2026-10-07",
        "recipients": recipients,
    }

    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    # Request first page with page_size=4
    page1_res = client.get(f"/api/v1/jobs/{job_id}/certificates?page=1&page_size=4")
    assert page1_res.status_code == 200
    p1_data = page1_res.json()
    assert p1_data["job_id"] == job_id
    assert p1_data["total"] == 10
    assert p1_data["page"] == 1
    assert p1_data["page_size"] == 4
    assert p1_data["total_pages"] == 3
    assert len(p1_data["items"]) == 4

    # Each item should have download_url populated once generated
    for item in p1_data["items"]:
        assert item["download_url"] is not None
        assert f"/api/v1/certificates/{item['id']}" == item["download_url"]
        assert item["status"] == "generated"

    # Request third page with page_size=4
    page3_res = client.get(f"/api/v1/jobs/{job_id}/certificates?page=3&page_size=4")
    assert page3_res.status_code == 200
    p3_data = page3_res.json()
    assert len(p3_data["items"]) == 2


def test_list_certificates_job_not_found(client: TestClient):
    """Test listing certificates for invalid job ID returns 404."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/jobs/{random_id}/certificates")
    assert response.status_code == 404

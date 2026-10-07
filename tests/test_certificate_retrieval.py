import os
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import GenerationJob, Certificate, JobStatus, CertificateStatus
from app.templates.certificate_template import build_certificate_pdf


def test_retrieve_generated_certificate_success(
    client: TestClient, db_session: Session, tmp_path
):
    """Test retrieving a successfully generated certificate returns 200 and PDF stream."""
    job_id = str(uuid.uuid4())
    cert_id = str(uuid.uuid4())
    pdf_path = str(tmp_path / f"{cert_id}.pdf")

    # Generate a real PDF file
    build_certificate_pdf(
        output_path=pdf_path,
        recipient_name="Aarav Sharma",
        event_name="Cloud Workshop",
        certificate_title="Certificate of Attendance",
        event_date="2026-10-07",
        certificate_id=cert_id,
    )

    job = GenerationJob(
        id=job_id,
        event_name="Cloud Workshop",
        certificate_title="Certificate of Attendance",
        event_date="2026-10-07",
        status=JobStatus.COMPLETED.value,
        total_count=1,
        successful_count=1,
        failed_count=0,
    )
    cert = Certificate(
        id=cert_id,
        job_id=job_id,
        recipient_name="Aarav Sharma",
        recipient_email="aarav@example.com",
        status=CertificateStatus.GENERATED.value,
        file_path=pdf_path,
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "Aarav_Sharma_certificate.pdf" in response.headers.get("content-disposition", "")
    assert response.content[:5] == b"%PDF-"


def test_retrieve_pending_certificate_returns_409(client: TestClient, db_session: Session):
    """Test attempting to download a certificate while pending returns 409 Conflict."""
    job_id = str(uuid.uuid4())
    cert_id = str(uuid.uuid4())

    job = GenerationJob(
        id=job_id,
        event_name="DevOps Summit",
        certificate_title="Certificate of Participation",
        event_date="2026-10-07",
        status=JobStatus.PROCESSING.value,
        total_count=1,
        successful_count=0,
        failed_count=0,
    )
    cert = Certificate(
        id=cert_id,
        job_id=job_id,
        recipient_name="Pending Recipient",
        recipient_email="pending@example.com",
        status=CertificateStatus.PENDING.value,
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert_id}")
    assert response.status_code == 409
    assert "Certificate generation is still in progress" in response.json()["detail"]


def test_retrieve_failed_certificate_returns_422(client: TestClient, db_session: Session):
    """Test attempting to download a failed certificate returns 422 with failure details."""
    job_id = str(uuid.uuid4())
    cert_id = str(uuid.uuid4())

    job = GenerationJob(
        id=job_id,
        event_name="Security Summit",
        certificate_title="Certificate of Attendance",
        event_date="2026-10-07",
        status=JobStatus.COMPLETED_WITH_ERRORS.value,
        total_count=1,
        successful_count=0,
        failed_count=1,
    )
    cert = Certificate(
        id=cert_id,
        job_id=job_id,
        recipient_name="Failed Recipient",
        recipient_email="failed@example.com",
        status=CertificateStatus.FAILED.value,
        error_message="Font descriptor missing",
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert_id}")
    assert response.status_code == 422
    assert "Certificate generation failed: Font descriptor missing" in response.json()["detail"]


def test_retrieve_nonexistent_certificate_returns_404(client: TestClient):
    """Test querying a certificate ID that does not exist returns 404."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/certificates/{random_id}")
    assert response.status_code == 404
    assert f"Certificate with ID '{random_id}' not found" in response.json()["detail"]


def test_retrieve_missing_file_on_disk_returns_404(client: TestClient, db_session: Session):
    """Test when DB record is generated but physical file was deleted returns 404."""
    job_id = str(uuid.uuid4())
    cert_id = str(uuid.uuid4())
    nonexistent_path = "/nonexistent/path/to/missing.pdf"

    job = GenerationJob(
        id=job_id,
        event_name="Data Science Week",
        certificate_title="Certificate of Attendance",
        event_date="2026-10-07",
        status=JobStatus.COMPLETED.value,
        total_count=1,
        successful_count=1,
        failed_count=0,
    )
    cert = Certificate(
        id=cert_id,
        job_id=job_id,
        recipient_name="Ghost Recipient",
        recipient_email="ghost@example.com",
        status=CertificateStatus.GENERATED.value,
        file_path=nonexistent_path,
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert_id}")
    assert response.status_code == 404
    assert "missing from local storage" in response.json()["detail"]

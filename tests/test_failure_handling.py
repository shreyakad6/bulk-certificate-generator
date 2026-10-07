import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import GenerationJob, Certificate, JobStatus, CertificateStatus
from app.services.job_processor import process_generation_job
from tests.conftest import TestingSessionLocal


def test_individual_certificate_failure_continues_processing(db_session: Session):
    """
    Critical Failure Test:
    Demonstrates that one certificate failure does NOT abort the batch.
    Mocks certificate generator to succeed for recipient 1, fail for recipient 2, and succeed for recipient 3.

    Verifies:
    - certificate 1 = generated
    - certificate 2 = failed (with error message preserved)
    - certificate 3 = generated
    - job successful_count = 2
    - job failed_count = 1
    - processing continues after the failure
    - final job status = completed_with_errors
    """
    job_id = str(uuid.uuid4())
    job = GenerationJob(
        id=job_id,
        event_name="Resilience Testing Workshop",
        certificate_title="Certificate of Attendance",
        event_date="2026-10-07",
        status=JobStatus.PENDING.value,
        total_count=3,
        successful_count=0,
        failed_count=0,
    )
    db_session.add(job)

    cert1 = Certificate(
        id=str(uuid.uuid4()),
        job_id=job_id,
        recipient_name="Recipient One",
        recipient_email="one@example.com",
        status=CertificateStatus.PENDING.value,
    )
    cert2 = Certificate(
        id=str(uuid.uuid4()),
        job_id=job_id,
        recipient_name="Recipient Two",
        recipient_email="two@example.com",
        status=CertificateStatus.PENDING.value,
    )
    cert3 = Certificate(
        id=str(uuid.uuid4()),
        job_id=job_id,
        recipient_name="Recipient Three",
        recipient_email="three@example.com",
        status=CertificateStatus.PENDING.value,
    )
    db_session.add_all([cert1, cert2, cert3])
    db_session.commit()

    # Mock generator service
    mock_generator = MagicMock()

    def mock_generate_side_effect(job_id, certificate_id, recipient_name, **kwargs):
        if recipient_name == "Recipient Two":
            raise RuntimeError("Simulated PDF font rendering fault")
        return f"generated/{job_id}/{certificate_id}.pdf"

    mock_generator.generate.side_effect = mock_generate_side_effect

    # Execute processor directly with mock generator and test session factory
    process_generation_job(
        job_id=job_id,
        db_factory=TestingSessionLocal,
        generator=mock_generator,
    )

    # Re-fetch from DB after separate worker session commits
    db_session.expire_all()
    updated_job = db_session.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    assert updated_job is not None
    assert updated_job.status == JobStatus.COMPLETED_WITH_ERRORS.value
    assert updated_job.successful_count == 2
    assert updated_job.failed_count == 1
    assert updated_job.completed_at is not None

    db_cert1 = db_session.query(Certificate).filter(Certificate.id == cert1.id).first()
    db_cert2 = db_session.query(Certificate).filter(Certificate.id == cert2.id).first()
    db_cert3 = db_session.query(Certificate).filter(Certificate.id == cert3.id).first()

    assert db_cert1.status == CertificateStatus.GENERATED.value
    assert db_cert1.file_path is not None
    assert db_cert1.error_message is None

    assert db_cert2.status == CertificateStatus.FAILED.value
    assert db_cert2.file_path is None
    assert "Simulated PDF font rendering fault" in db_cert2.error_message

    assert db_cert3.status == CertificateStatus.GENERATED.value
    assert db_cert3.file_path is not None
    assert db_cert3.error_message is None


def test_all_certificates_failing_marks_job_failed(db_session: Session):
    """Test that when all certificates fail, the overall job status is 'failed'."""
    job_id = str(uuid.uuid4())
    job = GenerationJob(
        id=job_id,
        event_name="Total Failure Event",
        certificate_title="Certificate of Participation",
        event_date="2026-10-07",
        status=JobStatus.PENDING.value,
        total_count=2,
        successful_count=0,
        failed_count=0,
    )
    db_session.add(job)

    cert1 = Certificate(
        id=str(uuid.uuid4()),
        job_id=job_id,
        recipient_name="Failure User 1",
        recipient_email="fail1@example.com",
    )
    cert2 = Certificate(
        id=str(uuid.uuid4()),
        job_id=job_id,
        recipient_name="Failure User 2",
        recipient_email="fail2@example.com",
    )
    db_session.add_all([cert1, cert2])
    db_session.commit()

    mock_generator = MagicMock()
    mock_generator.generate.side_effect = RuntimeError("Fatal disk write failure")

    process_generation_job(
        job_id=job_id,
        db_factory=TestingSessionLocal,
        generator=mock_generator,
    )

    db_session.expire_all()
    updated_job = db_session.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    assert updated_job.status == JobStatus.FAILED.value
    assert updated_job.successful_count == 0
    assert updated_job.failed_count == 2

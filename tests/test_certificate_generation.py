import os
import uuid
from app.services.certificate_generator import CertificateGeneratorService
from app.templates.certificate_template import build_certificate_pdf


def test_build_certificate_pdf_creates_valid_pdf(tmp_path):
    """Test that build_certificate_pdf produces a non-empty valid PDF file."""
    output_file = str(tmp_path / "test_cert.pdf")
    cert_id = str(uuid.uuid4())

    result_path = build_certificate_pdf(
        output_path=output_file,
        recipient_name="Aarav Sharma",
        event_name="Full Stack Python Mastery",
        certificate_title="Certificate of Excellence",
        event_date="2026-10-07",
        certificate_id=cert_id,
        organization_name="TechNova Academy",
    )

    assert result_path == output_file
    assert os.path.exists(output_file)
    assert os.path.getsize(output_file) > 1000  # Non-trivial PDF size

    # Verify standard PDF magic header bytes
    with open(output_file, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


def test_certificate_generator_service(tmp_path):
    """Test CertificateGeneratorService creates required subdirectories and PDF."""
    service = CertificateGeneratorService(base_dir=str(tmp_path))
    job_id = str(uuid.uuid4())
    cert_id = str(uuid.uuid4())

    created_path = service.generate(
        job_id=job_id,
        certificate_id=cert_id,
        recipient_name="Priya Patil",
        event_name="Machine Learning Bootcamp",
        certificate_title="Certificate of Completion",
        event_date="2026-10-07",
    )

    expected_path = os.path.join(str(tmp_path), job_id, f"{cert_id}.pdf")
    assert os.path.normpath(created_path) == os.path.normpath(expected_path)
    assert os.path.isfile(created_path)


def test_certificate_generation_with_long_strings(tmp_path):
    """Test certificate generation safely handles long recipient and event names."""
    output_file = str(tmp_path / "sub" / "long_cert.pdf")
    cert_id = str(uuid.uuid4())

    long_name = "Dr. Alexander Bartholomew Montgomery-Cunningham III, PhD"
    long_event = "International Conference on Advanced Quantum Algorithms and Distributed Systems 2026"
    long_title = "Honorary Certificate of Outstanding Research and Participation"

    result = build_certificate_pdf(
        output_path=output_file,
        recipient_name=long_name,
        event_name=long_event,
        certificate_title=long_title,
        event_date="October 7th, 2026",
        certificate_id=cert_id,
    )

    assert os.path.exists(result)
    assert os.path.getsize(result) > 1000

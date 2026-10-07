from fastapi.testclient import TestClient


def test_validation_missing_required_fields(client: TestClient):
    """Test 422 error when top-level required fields are omitted."""
    # Missing event_name
    res = client.post(
        "/api/v1/jobs",
        json={
            "certificate_title": "Certificate of Participation",
            "event_date": "2026-10-07",
            "recipients": [{"name": "Aarav", "email": "aarav@example.com"}],
        },
    )
    assert res.status_code == 422

    # Missing certificate_title
    res = client.post(
        "/api/v1/jobs",
        json={
            "event_name": "Python Workshop",
            "event_date": "2026-10-07",
            "recipients": [{"name": "Aarav", "email": "aarav@example.com"}],
        },
    )
    assert res.status_code == 422

    # Missing event_date
    res = client.post(
        "/api/v1/jobs",
        json={
            "event_name": "Python Workshop",
            "certificate_title": "Certificate of Participation",
            "recipients": [{"name": "Aarav", "email": "aarav@example.com"}],
        },
    )
    assert res.status_code == 422


def test_validation_blank_fields_rejected(client: TestClient):
    """Test 422 error when fields are whitespace-only."""
    payload = {
        "event_name": "   ",
        "certificate_title": "Certificate of Participation",
        "event_date": "2026-10-07",
        "recipients": [{"name": "Aarav", "email": "aarav@example.com"}],
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 422


def test_validation_empty_recipients_list(client: TestClient):
    """Test 422 error when recipient list is empty."""
    payload = {
        "event_name": "Python Workshop",
        "certificate_title": "Certificate of Participation",
        "event_date": "2026-10-07",
        "recipients": [],
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 422


def test_validation_invalid_recipient_name(client: TestClient):
    """Test 422 error when recipient name is blank or missing."""
    # Blank recipient name
    payload = {
        "event_name": "Python Workshop",
        "certificate_title": "Certificate of Participation",
        "event_date": "2026-10-07",
        "recipients": [{"name": "   ", "email": "aarav@example.com"}],
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 422

    # Missing recipient name
    payload = {
        "event_name": "Python Workshop",
        "certificate_title": "Certificate of Participation",
        "event_date": "2026-10-07",
        "recipients": [{"email": "aarav@example.com"}],
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 422


def test_validation_invalid_recipient_email(client: TestClient):
    """Test 422 error when recipient email is malformed."""
    invalid_emails = [
        "not-an-email",
        "@example.com",
        "user@",
        "user@.com",
        "user@com",
        "   ",
    ]
    for bad_email in invalid_emails:
        payload = {
            "event_name": "Python Workshop",
            "certificate_title": "Certificate of Participation",
            "event_date": "2026-10-07",
            "recipients": [{"name": "Aarav", "email": bad_email}],
        }
        res = client.post("/api/v1/jobs", json=payload)
        assert res.status_code == 422, f"Expected 422 for bad email: {bad_email}"


def test_validation_whitespace_trimming(client: TestClient):
    """Test leading and trailing whitespaces are cleanly trimmed."""
    payload = {
        "event_name": "   Python Workshop 2026   ",
        "certificate_title": "   Certificate of Participation   ",
        "event_date": "   2026-10-07   ",
        "recipients": [
            {"name": "   Aarav Sharma   ", "email": "   Aarav.Sharma@Example.COM   "}
        ],
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["event_name"] == "Python Workshop 2026"
    assert status_data["certificate_title"] == "Certificate of Participation"
    assert status_data["event_date"] == "2026-10-07"

    certs_res = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert certs_res.status_code == 200
    cert = certs_res.json()["items"][0]
    assert cert["recipient_name"] == "Aarav Sharma"
    assert cert["recipient_email"] == "aarav.sharma@example.com"


def test_validation_max_recipients_limit(client: TestClient):
    """Test 422 error when exceeding 1000 recipients limit."""
    recipients = [
        {"name": f"User {i}", "email": f"user{i}@example.com"} for i in range(1001)
    ]
    payload = {
        "event_name": "Massive Conference",
        "certificate_title": "Certificate of Attendance",
        "event_date": "2026-10-07",
        "recipients": recipients,
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 422
    assert "maximum limit of 1000 recipients" in res.text

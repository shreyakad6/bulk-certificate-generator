# Bulk Certificate Generator API

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![ReportLab](https://img.shields.io/badge/ReportLab-4.1+-orange.svg)](https://www.reportlab.com/)
[![Tests](https://img.shields.io/badge/tests-24%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A high-performance, asynchronous REST backend built with **FastAPI**, **SQLAlchemy 2.x**, and **ReportLab** designed to handle bulk certificate generation reliably. The system validates participant data, queues background generation jobs, renders deterministic landscape A4 PDF certificates, tracks live generation metrics, and provides individual retrieval endpoints.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Features](#2-features)
3. [Tech Stack](#3-tech-stack)
4. [Architecture](#4-architecture)
5. [Project Structure](#5-project-structure)
6. [Database Design](#6-database-design)
7. [API Endpoints](#7-api-endpoints)
8. [Request / Response Examples](#8-request--response-examples)
9. [Setup Instructions](#9-setup-instructions)
10. [Environment Variables](#10-environment-variables)
11. [Running Locally](#11-running-locally)
12. [Running Tests](#12-running-tests)
13. [Docker Instructions](#13-docker-instructions)
14. [Certificate Generation](#14-certificate-generation)
15. [Background Processing Design](#15-background-processing-design)
16. [Failure Handling](#16-failure-handling)
17. [Design Decisions](#17-design-decisions)
18. [Limitations](#18-limitations)
19. [Possible Future Improvements](#19-possible-future-improvements)

---

## 1. Overview

Organizations frequently conduct workshops, webinars, hackathons, and courses where hundreds or thousands of personalized certificates must be issued simultaneously. Generating hundreds of PDF documents synchronously within a single HTTP request causes connection timeouts, blocked workers, high memory spikes, and poor user experiences.

The **Bulk Certificate Generator API** solves this by:
1. Validating all recipient data immediately upon intake.
2. Persisting the batch job and recipient records with initial `pending` statuses.
3. Responding to the client immediately with `202 Accepted` and a unique `job_id`.
4. Asynchronously rendering each certificate PDF independently in the background.
5. Providing real-time progress metrics (percentage, counts, completed/failed status).
6. Serving downloadable PDF certificates via dedicated retrieval endpoints.

---

## 2. Features

- **Bulk Intake**: Process batches containing up to 1,000 recipients in a single API call.
- **Strict Data Validation**: Validates event details, dates, recipient names, and email formatting with descriptive 422 error feedback. Automatic trimming of whitespace.
- **Asynchronous Processing**: Immediate HTTP 202 acknowledgment while background workers generate certificates without blocking client requests.
- **Fault-Tolerant Execution**: A failure generating one recipient's certificate (e.g., rendering defect, character set error) **never** terminates or invalidates the remaining recipients.
- **Comprehensive Status Tracking**: Track batch progress in real-time, including `total_count`, `successful_count`, `failed_count`, `pending_count`, and `progress_percentage`.
- **Predefined Landscape A4 Template**: Beautiful, print-ready PDF certificate created with vector graphics, double borders, official seal emblem, and digital signature lines—with zero external image or network dependencies.
- **RESTful Endpoints**: Clean API design adhering to standard HTTP verbs and status codes (200, 202, 404, 409, 422).
- **Interactive Documentation**: Out-of-the-box Swagger UI (`/docs`) and ReDoc (`/redoc`).
- **Containerized**: Production-ready `Dockerfile` and `docker-compose.yml`.

---

## 3. Tech Stack

- **Language**: Python 3.11+ (tested on Python 3.11, 3.12, and 3.13)
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) (modern ASGI framework with asynchronous routing and dependency injection)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/) (high-performance ASGI server)
- **Validation & Serialization**: [Pydantic v2](https://docs.pydantic.dev/) and `pydantic-settings`
- **ORM & Database**: [SQLAlchemy 2.x](https://www.sqlalchemy.org/) (typed mapped columns, dual-compatible with SQLite and PostgreSQL)
- **PDF Engine**: [ReportLab](https://www.reportlab.com/) (canvas-level vector graphics and typography)
- **Testing**: [pytest](https://docs.pytest.org/), `pytest-asyncio`, and `httpx` / Starlette `TestClient`
- **Containerization**: Docker & Docker Compose

---

## 4. Architecture

```
                  +---------------------------+
                  |       HTTP Client         |
                  +---------------------------+
                     |                     ^
         POST /jobs  |                     |  GET /jobs/{id}
         (Batch)     |                     |  GET /certificates/{id}
                     v                     |
              +-------------------------------+
              |         FastAPI Router        |
              +-------------------------------+
                     |                     |
     1. Validate &   |                     | 3. Returns 202 Accepted
        Insert DB    v                     |    with job_id
              +----------------+           |
              |  Database      |           |
              |  (SQLite/PgSQL)|           |
              +----------------+           |
                     ^                     |
                     | 4. Read & Update    v
                     |    Status     +-----------------------+
                     +---------------|  FastAPI Background   |
                                     |  Worker (Async Task)  |
                                     +-----------------------+
                                                 |
                                                 | 5. Calls Service
                                                 v
                                     +-----------------------+
                                     | Certificate Generator |
                                     |      (ReportLab)      |
                                     +-----------------------+
                                                 |
                                                 | 6. Writes PDF
                                                 v
                                     +-----------------------+
                                     |  generated/{job_id}/  |
                                     |  {cert_id}.pdf        |
                                     +-----------------------+
```

### Lifecycle Flow:
1. **Client Request**: Client submits a JSON payload containing `event_name`, `certificate_title`, `event_date`, and a list of `recipients`.
2. **Synchronous Validation**: Pydantic validates field presence, non-blank strings, email format, and batch size.
3. **Database Transaction**: A `GenerationJob` is inserted alongside individual `Certificate` rows in `pending` state.
4. **Immediate Acknowledgment**: The client receives HTTP `202 Accepted` with the `job_id`.
5. **Background Execution**: A background task sequentially processes each certificate:
   - Evaluates the recipient record.
   - Renders the PDF via ReportLab to `generated/{job_id}/{certificate_id}.pdf`.
   - On success: marks certificate as `generated` and increments `successful_count`.
   - On failure: marks certificate as `failed`, saves `error_message`, increments `failed_count`, and continues to the next recipient.
6. **Finalization**: The job's status transitions to `completed`, `completed_with_errors`, or `failed`, recording `completed_at`.

---

## 5. Project Structure

```
bulk-certificate-generator/
│
├── app/
│   ├── __init__.py               # Package marker
│   ├── main.py                   # FastAPI application initialization & lifespan
│   ├── config.py                 # Pydantic BaseSettings environment configuration
│   ├── database.py               # SQLAlchemy 2.x engine, SessionLocal, and get_db dependency
│   ├── models.py                 # GenerationJob and Certificate ORM models
│   ├── schemas.py                # Pydantic v2 validation and response schemas
│   │
│   ├── routes/
│   │   ├── __init__.py           # Routes package marker
│   │   ├── jobs.py               # Job creation, status tracking, and certificates listing
│   │   └── certificates.py       # Certificate file download & error resolution
│   │
│   ├── services/
│   │   ├── __init__.py           # Services package marker
│   │   ├── certificate_generator.py # File path routing and PDF generator orchestration
│   │   └── job_processor.py      # Resilient background batch execution engine
│   │
│   └── templates/
│       ├── __init__.py           # Templates package marker
│       └── certificate_template.py # ReportLab Landscape A4 vector certificate design
│
├── tests/
│   ├── __init__.py               # Test suite package marker
│   ├── conftest.py               # In-memory SQLite fixtures, storage isolation, and client
│   ├── test_jobs.py              # Tests for job creation, status, and listing
│   ├── test_validation.py        # Tests for field constraints, emails, and edge cases
│   ├── test_certificate_generation.py # Tests for ReportLab PDF rendering & file output
│   ├── test_job_status.py        # Tests for status metrics and percentage calculations
│   ├── test_failure_handling.py  # Tests for single-failure resilience & all-failure states
│   └── test_certificate_retrieval.py # Tests for PDF streaming, 404, 409, and 422 errors
│
├── generated/
│   └── .gitkeep                  # Storage directory placeholder (PDFs ignored in git)
│
├── .env.example                  # Template configuration variables
├── .gitignore                    # Exclusion rules for virtualenv, DBs, cache, and PDFs
├── requirements.txt              # Pinned production and testing dependencies
├── README.md                     # Comprehensive documentation
├── Dockerfile                    # Container build file
├── docker-compose.yml            # Container orchestration specification
└── pytest.ini                    # Test runner configuration
```

---

## 6. Database Design

The schema uses SQLAlchemy 2.0 with portable types (`String(36)` UUIDs, ISO datetime fields, explicit indexes, and cascade deletions) ensuring seamless compatibility across SQLite and PostgreSQL.

### Table: `generation_jobs`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `VARCHAR(36)` | PRIMARY KEY, INDEX | Unique UUID4 string |
| `event_name` | `VARCHAR(255)` | NOT NULL | Name of the event or course |
| `certificate_title` | `VARCHAR(255)` | NOT NULL | Title displayed on the certificate |
| `event_date` | `VARCHAR(50)` | NOT NULL | Event date string |
| `status` | `VARCHAR(32)` | NOT NULL, INDEX | `pending`, `processing`, `completed`, `completed_with_errors`, `failed` |
| `total_count` | `INTEGER` | NOT NULL, DEFAULT 0 | Total recipients in the request |
| `successful_count` | `INTEGER` | NOT NULL, DEFAULT 0 | Count of successfully rendered certificates |
| `failed_count` | `INTEGER` | NOT NULL, DEFAULT 0 | Count of failed certificate renders |
| `created_at` | `DATETIME` | NOT NULL | UTC timestamp of job creation |
| `completed_at` | `DATETIME` | NULLABLE | UTC timestamp when processing concluded |

### Table: `certificates`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `VARCHAR(36)` | PRIMARY KEY, INDEX | Unique UUID4 string |
| `job_id` | `VARCHAR(36)` | NOT NULL, INDEX, FK(`generation_jobs.id`, ON DELETE CASCADE) | Parent job identifier |
| `recipient_name` | `VARCHAR(255)` | NOT NULL | Full name of recipient |
| `recipient_email` | `VARCHAR(255)` | NOT NULL | Validated email address |
| `status` | `VARCHAR(32)` | NOT NULL, INDEX | `pending`, `generated`, `failed` |
| `file_path` | `VARCHAR(500)` | NULLABLE | Filesystem path to the rendered PDF |
| `error_message` | `TEXT` | NULLABLE | Error trace/message if generation failed |
| `created_at` | `DATETIME` | NOT NULL | UTC timestamp of record creation |

---

## 7. API Endpoints

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `POST` | `/api/v1/jobs` | `202 Accepted` | Submit a bulk certificate generation job |
| `GET` | `/api/v1/jobs/{job_id}` | `200 OK` | Check live processing status and progress percentage |
| `GET` | `/api/v1/jobs/{job_id}/certificates` | `200 OK` | Paginated listing of certificates and download URLs |
| `GET` | `/api/v1/certificates/{certificate_id}` | `200 OK` | Download or stream the generated PDF certificate |
| `GET` | `/health` | `200 OK` | Service operational health check |
| `GET` | `/docs` | `200 OK` | Interactive Swagger API documentation |

---

## 8. Request / Response Examples

### 1. Create a Bulk Generation Job

**Request:**
```http
POST /api/v1/jobs HTTP/1.1
Content-Type: application/json

{
  "event_name": "Python Workshop 2026",
  "certificate_title": "Certificate of Participation",
  "event_date": "2026-10-07",
  "recipients": [
    {
      "name": "Aarav Sharma",
      "email": "aarav@example.com"
    },
    {
      "name": "Priya Patil",
      "email": "priya@example.com"
    }
  ]
}
```

**Response (`202 Accepted`):**
```json
{
  "job_id": "072cf88f-d783-4c1e-bd0f-f0dcb633ce8f",
  "status": "pending",
  "total_count": 2,
  "message": "Certificate generation job created successfully"
}
```

---

### 2. Check Job Status

**Request:**
```http
GET /api/v1/jobs/072cf88f-d783-4c1e-bd0f-f0dcb633ce8f HTTP/1.1
```

**Response while Processing (`200 OK`):**
```json
{
  "job_id": "072cf88f-d783-4c1e-bd0f-f0dcb633ce8f",
  "status": "processing",
  "total_count": 100,
  "successful_count": 72,
  "failed_count": 3,
  "pending_count": 25,
  "progress_percentage": 75.0,
  "event_name": "Python Workshop 2026",
  "certificate_title": "Certificate of Participation",
  "event_date": "2026-10-07",
  "created_at": "2026-10-07T06:43:17.225923",
  "completed_at": null
}
```

**Response upon Completion (`200 OK`):**
```json
{
  "job_id": "072cf88f-d783-4c1e-bd0f-f0dcb633ce8f",
  "status": "completed",
  "total_count": 2,
  "successful_count": 2,
  "failed_count": 0,
  "pending_count": 0,
  "progress_percentage": 100.0,
  "event_name": "Python Workshop 2026",
  "certificate_title": "Certificate of Participation",
  "event_date": "2026-10-07",
  "created_at": "2026-10-07T06:43:17.225923",
  "completed_at": "2026-10-07T06:43:17.346816"
}
```

---

### 3. List Certificates for a Job (Paginated)

**Request:**
```http
GET /api/v1/jobs/072cf88f-d783-4c1e-bd0f-f0dcb633ce8f/certificates?page=1&page_size=50 HTTP/1.1
```

**Response (`200 OK`):**
```json
{
  "job_id": "072cf88f-d783-4c1e-bd0f-f0dcb633ce8f",
  "total": 2,
  "page": 1,
  "page_size": 50,
  "total_pages": 1,
  "items": [
    {
      "id": "d3780990-6840-42b6-acf8-fe43e1db2581",
      "job_id": "072cf88f-d783-4c1e-bd0f-f0dcb633ce8f",
      "recipient_name": "Aarav Sharma",
      "recipient_email": "aarav@example.com",
      "status": "generated",
      "download_url": "/api/v1/certificates/d3780990-6840-42b6-acf8-fe43e1db2581",
      "error_message": null,
      "created_at": "2026-10-07T06:43:17.231378"
    },
    {
      "id": "5f6293b0-6620-488a-85a5-5d7cfd9667a1",
      "job_id": "072cf88f-d783-4c1e-bd0f-f0dcb633ce8f",
      "recipient_name": "Priya Patil",
      "recipient_email": "priya@example.com",
      "status": "generated",
      "download_url": "/api/v1/certificates/5f6293b0-6620-488a-85a5-5d7cfd9667a1",
      "error_message": null,
      "created_at": "2026-10-07T06:43:17.231391"
    }
  ]
}
```

---

### 4. Retrieve / Download Certificate PDF

**Request:**
```http
GET /api/v1/certificates/d3780990-6840-42b6-acf8-fe43e1db2581 HTTP/1.1
```

**Response (`200 OK`):**
- **Content-Type**: `application/pdf`
- **Content-Disposition**: `attachment; filename="Aarav_Sharma_certificate.pdf"`
- **Body**: Binary PDF stream.

**Error Responses:**
- If still rendering: `409 Conflict` (`"Certificate generation is still in progress. Please check again shortly."`)
- If render failed: `422 Unprocessable Entity` (`"Certificate generation failed: <reason>"`)
- If nonexistent: `404 Not Found` (`"Certificate with ID '...' not found"`)

---

## 9. Setup Instructions

### Prerequisites
- Python 3.11+ installed
- Git installed (optional)
- Docker & Docker Compose (optional, for containerized run)

### Clone / Navigate to Project
```bash
git clone https://github.com/<your-username>/bulk-certificate-generator.git
cd bulk-certificate-generator
```

### Create and Activate Virtual Environment

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 10. Environment Variables

Create a local `.env` file by copying `.env.example`:

```bash
cp .env.example .env
```

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./certificates.db` | SQLAlchemy database connection URI |
| `GENERATED_FILES_DIR` | `generated` | Directory path where PDF certificates are stored |
| `MAX_RECIPIENTS_PER_JOB` | `1000` | Upper limit on recipients per batch request |
| `APP_ENV` | `development` | Environment mode (`development`, `test`, `production`) |
| `DEBUG` | `false` | Enable verbose SQL logging and debugging |
| `API_V1_PREFIX` | `/api/v1` | URL prefix for version 1 endpoints |

---

## 11. Running Locally

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Once started:
- **API Base URL**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Quick cURL Verification Commands

#### 1. Create a Job:
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Full Stack Mastery 2026",
    "certificate_title": "Certificate of Completion",
    "event_date": "2026-10-07",
    "recipients": [
      {"name": "Aarav Sharma", "email": "aarav@example.com"},
      {"name": "Priya Patil", "email": "priya@example.com"}
    ]
  }'
```

#### 2. Check Job Status:
```bash
curl http://localhost:8000/api/v1/jobs/<JOB_ID>
```

#### 3. List Generated Certificates:
```bash
curl "http://localhost:8000/api/v1/jobs/<JOB_ID>/certificates?page=1&page_size=10"
```

#### 4. Download a Certificate:
```bash
curl -O -J http://localhost:8000/api/v1/certificates/<CERTIFICATE_ID>
```

---

## 12. Running Tests

The test suite runs against an isolated, in-memory SQLite database and isolated temporary storage directories. Tests do **not** depend on a running server.

Run the entire test suite with pytest:

```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

### Test Coverage Highlights:
- **`test_jobs.py`**: Job creation (202 status), database record persistence, job retrieval, and pagination.
- **`test_validation.py`**: Empty payload rejection, missing fields, whitespace trimming, malformed emails, and >1000 recipient limits.
- **`test_certificate_generation.py`**: Valid PDF binary headers (`%PDF-`), file creation, subfolder creation, and handling long text.
- **`test_job_status.py`**: Live progress calculation, completed state, completed_with_errors state, and 404 on missing jobs.
- **`test_failure_handling.py`**: Mocked service demonstrating that an error on recipient 2 does not interrupt recipients 1 and 3, setting `completed_with_errors` with proper error messages.
- **`test_certificate_retrieval.py`**: PDF file streaming (200), pending state (409), failure state (422), missing record (404), and missing disk file (404).

---

## 13. Docker Instructions

The project includes a lightweight Dockerfile and docker-compose configuration.

### Run with Docker Compose
```bash
docker compose up --build
```

The application will be available at:
```
http://localhost:8000
```
Swagger UI will be accessible at:
```
http://localhost:8000/docs
```

Generated certificates are stored in a mounted volume `./generated` on your host machine to ensure persistence across container restarts.

To stop the containers:
```bash
docker compose down
```

---

## 14. Certificate Generation

Certificate rendering is executed via **ReportLab**:
- **Format**: Landscape A4 (`841.89 x 595.27 points`).
- **Styling**:
  - Crisp parchment background (`#FCFDFD`).
  - Outer primary navy border (`#0F2942`) with 3.0pt stroke.
  - Inset secondary warm gold border (`#C59B27`) with geometric diamond corner ornaments.
  - Organization title banner: "TECHNOVA ACADEMY".
  - Centered recipient name with adaptive typography and decorative gold underline.
  - Custom event name and formatted event date.
  - Vector-drawn official seal emblem (no raster assets or external file downloads).
  - Digital signature flourish and authorized director signature section.
  - Unique Certificate UUID and verification tag.
- **Storage Location**: Certificates are deterministically written to:
  `generated/{job_id}/{certificate_id}.pdf`
  Directories are automatically created as needed.

---

## 15. Background Processing Design

### Why Background Processing?
PDF generation is CPU- and I/O-intensive. When processing batches of 100 or 1,000 certificates:
1. Synchronous rendering would hold HTTP connections open for 10-60+ seconds, causing gateway timeouts (`504 Gateway Timeout`) and connection resets.
2. Synchronous requests lock up Web/ASGI worker threads, preventing the API from serving other users.
3. Asynchronous background execution allows the client to receive immediate confirmation (`202 Accepted`) and poll progress via lightweight `GET` requests or integrate with progress bars.

### Chosen Approach: FastAPI `BackgroundTasks`
For this service, FastAPI's built-in `BackgroundTasks` was chosen instead of introducing Celery, Redis, or RabbitMQ:
- **Zero External Infrastructure**: Runs natively within the ASGI process without requiring extra brokers, daemons, or cache containers.
- **Easy Local Execution**: Evaluators and developers can clone and run the application immediately with zero configuration.
- **Low Operational Complexity**: Perfect balance between asynchronous bulk capabilities and architectural simplicity.

---

## 16. Failure Handling

Bulk processing must be fault-tolerant:
- **Isolated Per-Recipient Try-Catch**:
  ```python
  for cert in certificates:
      try:
          file_path = generator_service.generate(...)
          cert.status = CertificateStatus.GENERATED.value
          cert.file_path = file_path
          job.successful_count += 1
      except Exception as exc:
          cert.status = CertificateStatus.FAILED.value
          cert.error_message = str(exc)
          job.failed_count += 1
      db.commit()
  ```
- **Job Status State Machine**:
  - `failed_count == 0` &rarr; `completed`
  - `failed_count > 0` and `successful_count > 0` &rarr; `completed_with_errors`
  - `successful_count == 0` and `failed_count > 0` &rarr; `failed`
- **Granular Error Information**: When an individual certificate fails, the error reason is saved directly to that recipient's record and returned in the `/api/v1/jobs/{job_id}/certificates` response.

---

## 17. Design Decisions

1. **SQLite Default for Local Development**:
   - Zero-install, zero-configuration database that allows reviewers to clone and run immediately.
   - Using standard SQLAlchemy ORM types and connection parameters (`check_same_thread=False`) prevents database locks.
2. **PostgreSQL Compatibility**:
   - Models use database-agnostic types (`String(36)` UUIDs, standard DateTime, Integer, Text).
   - Migrating to PostgreSQL in production only requires setting `DATABASE_URL=postgresql://user:pass@host:5432/dbname` in `.env` without modifying a single line of application code.
3. **No Heavy Message Queues**:
   - Celery / Redis / Kafka were intentionally excluded to keep the application lightweight, self-contained, and clean for an SDE intern assignment while meeting all bulk background generation requirements.
4. **Vector-Only Certificate Template**:
   - Drawing borders, seals, and signatures programmatically in ReportLab removes the risk of missing image assets, broken relative paths, or network timeouts during rendering.

---

## 18. Limitations

- **Single Process In-Memory Workers**: FastAPI's `BackgroundTasks` runs inside the current Uvicorn process. If the server process crashes while a job is running, pending tasks in that job must be manually resumed or restarted.
- **Local Filesystem Storage**: PDFs are written to the local disk. In a multi-instance containerized cluster, an object storage service (e.g. AWS S3, Google Cloud Storage, or MinIO) would be required so all instances can access the generated files.
- **Fixed Template**: The service supports a single standardized certificate layout. Custom user-uploaded templates or drag-and-drop template builders are not supported.

---

## 19. Possible Future Improvements

1. **Distributed Task Queue**: Integrate Celery or ARQ with Redis for distributed multi-worker task execution with automatic retries and dead-letter queues.
2. **Cloud Storage Adapter**: Abstract certificate storage behind an S3-compatible interface (`StorageService`) with pre-signed download URLs.
3. **Batch Email Dispatch**: Optionally send the generated certificate PDF as an email attachment directly to each recipient's email address upon completion.
4. **Webhook Notifications**: Allow clients to provide a `webhook_url` in the request to receive an automated HTTP POST notification once the entire batch completes.
5. **ZIP Archive Download**: Add an endpoint `GET /api/v1/jobs/{job_id}/download-all` to download all certificates in a single ZIP file.

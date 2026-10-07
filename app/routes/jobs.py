from math import ceil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import GenerationJob, Certificate, JobStatus, CertificateStatus
from app.schemas import (
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
    PaginatedCertificatesResponse,
    CertificateItemResponse,
)
from app.services.job_processor import process_generation_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobCreateResponse,
    summary="Create a bulk certificate generation job",
    description="Validates recipient data, initializes batch records, and starts asynchronous background processing.",
)
def create_generation_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    """
    Accept a batch certificate generation request.

    - Validates event details and recipient list
    - Creates parent GenerationJob record
    - Initializes individual Certificate entries in 'pending' state
    - Enqueues background worker to generate PDF certificates
    - Returns HTTP 202 Accepted immediately
    """
    total_recipients = len(payload.recipients)

    # Create master job record
    job = GenerationJob(
        event_name=payload.event_name,
        certificate_title=payload.certificate_title,
        event_date=payload.event_date,
        status=JobStatus.PENDING.value,
        total_count=total_recipients,
        successful_count=0,
        failed_count=0,
    )
    db.add(job)
    db.flush()  # Obtain generated job.id

    # Create child certificate records
    certificates = [
        Certificate(
            job_id=job.id,
            recipient_name=rec.name,
            recipient_email=rec.email,
            status=CertificateStatus.PENDING.value,
        )
        for rec in payload.recipients
    ]
    db.add_all(certificates)
    db.commit()
    db.refresh(job)

    # Dispatch to background tasks for asynchronous processing
    background_tasks.add_task(process_generation_job, job.id)

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        message="Certificate generation job created successfully",
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get generation job status and progress",
    description="Returns current status, counts, and completion percentage for a given job.",
)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    """Retrieve the real-time processing status of a generation job."""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    processed_count = job.successful_count + job.failed_count
    pending_count = max(0, job.total_count - processed_count)

    if job.total_count == 0:
        progress_percentage = 100.0
    elif job.status in [
        JobStatus.COMPLETED.value,
        JobStatus.COMPLETED_WITH_ERRORS.value,
        JobStatus.FAILED.value,
    ]:
        progress_percentage = 100.0
    else:
        progress_percentage = round((processed_count / job.total_count) * 100.0, 2)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        pending_count=pending_count,
        progress_percentage=progress_percentage,
        event_name=job.event_name,
        certificate_title=job.certificate_title,
        event_date=job.event_date,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get(
    "/{job_id}/certificates",
    response_model=PaginatedCertificatesResponse,
    summary="List certificates for a job",
    description="Returns paginated certificate records with generation statuses and download links.",
)
def list_job_certificates(
    job_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> PaginatedCertificatesResponse:
    """Retrieve paginated certificates belonging to the specified job."""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    query = db.query(Certificate).filter(Certificate.job_id == job_id)
    total = query.count()

    total_pages = ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size

    certs = (
        query.order_by(Certificate.created_at.asc(), Certificate.id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for cert in certs:
        download_url = (
            f"{settings.API_V1_PREFIX}/certificates/{cert.id}"
            if cert.status == CertificateStatus.GENERATED.value
            else None
        )
        items.append(
            CertificateItemResponse(
                id=cert.id,
                job_id=cert.job_id,
                recipient_name=cert.recipient_name,
                recipient_email=cert.recipient_email,
                status=cert.status,
                download_url=download_url,
                error_message=cert.error_message,
                created_at=cert.created_at,
            )
        )

    return PaginatedCertificatesResponse(
        job_id=job_id,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )

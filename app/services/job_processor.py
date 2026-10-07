import logging
from typing import Optional, Callable
from sqlalchemy.orm import Session

import app.database
from app.models import GenerationJob, Certificate, JobStatus, CertificateStatus, utc_now
from app.services.certificate_generator import certificate_service, CertificateGeneratorService

logger = logging.getLogger("bulk_certificate_generator.job_processor")


def process_generation_job(
    job_id: str,
    db_factory: Optional[Callable[[], Session]] = None,
    generator: Optional[CertificateGeneratorService] = None,
) -> None:
    """
    Process all certificates in a bulk generation job sequentially and independently.

    A failure in generating any single recipient certificate does NOT abort
    the processing of subsequent recipients.

    Args:
        job_id: Unique UUID string of the GenerationJob.
        db_factory: Optional callable providing a SQLAlchemy session (defaults to app.database.SessionLocal).
        generator: Optional CertificateGeneratorService instance (defaults to global certificate_service).
    """
    session_factory = db_factory or app.database.SessionLocal
    generator_service = generator or certificate_service

    db: Session = session_factory()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            logger.error("Job %s was not found in the database. Aborting processing.", job_id)
            return

        logger.info("Starting processing for job %s (total: %d)", job.id, job.total_count)
        job.status = JobStatus.PROCESSING.value
        db.commit()

        certificates = (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id)
            .order_by(Certificate.created_at)
            .all()
        )

        for cert in certificates:
            try:
                file_path = generator_service.generate(
                    job_id=job.id,
                    certificate_id=cert.id,
                    recipient_name=cert.recipient_name,
                    event_name=job.event_name,
                    certificate_title=job.certificate_title,
                    event_date=job.event_date,
                )
                cert.status = CertificateStatus.GENERATED.value
                cert.file_path = file_path
                cert.error_message = None
                job.successful_count += 1
                logger.debug("Successfully generated certificate %s for %s", cert.id, cert.recipient_name)
            except Exception as exc:
                logger.exception(
                    "Failed to generate certificate %s for '%s' in job %s: %s",
                    cert.id,
                    cert.recipient_name,
                    job_id,
                    exc,
                )
                cert.status = CertificateStatus.FAILED.value
                cert.error_message = str(exc)
                job.failed_count += 1

            # Commit progress after each certificate for resilience
            db.commit()

        # Update final job completion state
        job.completed_at = utc_now()
        if job.failed_count == 0:
            job.status = JobStatus.COMPLETED.value
        elif job.successful_count > 0 and job.failed_count > 0:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value
        else:
            job.status = JobStatus.FAILED.value

        db.commit()
        logger.info(
            "Finished processing job %s. Status: %s (Successful: %d, Failed: %d)",
            job.id,
            job.status,
            job.successful_count,
            job.failed_count,
        )

    except Exception as exc:
        logger.critical("Unexpected error in background job processor for job %s: %s", job_id, exc)
        try:
            job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                job.completed_at = utc_now()
                db.commit()
        except Exception:
            logger.exception("Failed to update job status to FAILED after fatal error.")
    finally:
        db.close()

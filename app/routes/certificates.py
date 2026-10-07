import os
import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, CertificateStatus

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get(
    "/{certificate_id}",
    summary="Download or retrieve a generated certificate",
    description="Streams the generated PDF certificate file for download. Returns specific status codes if pending or failed.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "The generated PDF certificate file.",
        },
        404: {"description": "Certificate record or physical PDF file not found."},
        409: {"description": "Certificate is still pending or currently processing."},
        422: {"description": "Certificate generation failed for this recipient."},
    },
)
def get_certificate_file(
    certificate_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve and stream the generated certificate PDF file.

    - Returns HTTP 200 with FileResponse for generated certificates
    - Returns HTTP 409 Conflict if certificate is still pending
    - Returns HTTP 422 Unprocessable Entity if certificate generation failed
    - Returns HTTP 404 Not Found if certificate ID does not exist or file is missing
    """
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found",
        )

    if cert.status == CertificateStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate generation is still in progress. Please check again shortly.",
        )

    if cert.status == CertificateStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Certificate generation failed: {cert.error_message or 'Unknown error during rendering'}",
        )

    # For generated certificates, verify file exists on disk
    if not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate PDF file is missing from local storage.",
        )

    # Sanitize recipient name for safe Content-Disposition filename
    safe_name = re.sub(r"[^\w\-]", "_", cert.recipient_name.strip())
    filename = f"{safe_name}_certificate.pdf"

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=filename,
    )

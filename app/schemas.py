import re
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)


class RecipientCreate(BaseModel):
    """Schema for an individual recipient in a batch certificate creation request."""

    name: str = Field(..., description="Full name of the recipient", min_length=1)
    email: str = Field(..., description="Email address of the recipient", min_length=3)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Recipient name must not be blank")
        return trimmed

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Recipient email must not be blank")
        if not EMAIL_REGEX.match(trimmed):
            raise ValueError("Recipient email must be a valid email address")
        return trimmed.lower()

    model_config = ConfigDict(str_strip_whitespace=True)


class JobCreateRequest(BaseModel):
    """Request payload for creating a new bulk certificate generation job."""

    event_name: str = Field(..., description="Name of the event or course", min_length=1)
    certificate_title: str = Field(
        ..., description="Title appearing on the certificate", min_length=1
    )
    event_date: str = Field(..., description="Date of the event (e.g. YYYY-MM-DD or formatted string)")
    recipients: List[RecipientCreate] = Field(
        ...,
        description="List of recipients to generate certificates for (at least 1, max 1000)",
        min_length=1,
    )

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("event_name must not be blank")
        return trimmed

    @field_validator("certificate_title")
    @classmethod
    def validate_certificate_title(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("certificate_title must not be blank")
        return trimmed

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("event_date must not be blank")
        # Ensure it looks like a valid date format if ISO or readable string
        return trimmed

    @field_validator("recipients")
    @classmethod
    def validate_recipients_list(cls, value: List[RecipientCreate]) -> List[RecipientCreate]:
        if not value:
            raise ValueError("recipients list must contain at least one recipient")
        if len(value) > 1000:
            raise ValueError("recipients list exceeds maximum limit of 1000 recipients per job")
        return value

    model_config = ConfigDict(str_strip_whitespace=True)


class JobCreateResponse(BaseModel):
    """Immediate response returned upon successful acceptance of a generation job."""

    job_id: str = Field(..., description="Unique UUID identifier for the created job")
    status: str = Field(..., description="Initial status of the job (pending)")
    total_count: int = Field(..., description="Total number of recipients to be processed")
    message: str = Field(..., description="User-friendly status confirmation")

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    """Detailed progress and status information for a specific generation job."""

    job_id: str
    status: str
    total_count: int
    successful_count: int
    failed_count: int
    pending_count: int
    progress_percentage: float
    event_name: str
    certificate_title: str
    event_date: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CertificateItemResponse(BaseModel):
    """Details for a single certificate record."""

    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    status: str
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedCertificatesResponse(BaseModel):
    """Paginated list of certificate records belonging to a job."""

    job_id: str
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[CertificateItemResponse]

    model_config = ConfigDict(from_attributes=True)

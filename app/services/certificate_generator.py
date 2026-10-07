import os
from typing import Optional
from app.config import settings
from app.templates.certificate_template import build_certificate_pdf


class CertificateGeneratorService:
    """Service responsible for generating certificate PDF files using predefined templates."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or settings.GENERATED_FILES_DIR

    def get_output_path(self, job_id: str, certificate_id: str) -> str:
        """Construct the relative/absolute file path for the given certificate."""
        return os.path.join(self.base_dir, job_id, f"{certificate_id}.pdf")

    def generate(
        self,
        job_id: str,
        certificate_id: str,
        recipient_name: str,
        event_name: str,
        certificate_title: str,
        event_date: str,
    ) -> str:
        """
        Generate a certificate PDF for a recipient.

        Returns:
            str: The normalized path to the created PDF file.
        """
        output_path = self.get_output_path(job_id, certificate_id)
        # Delegate drawing to the template builder
        build_certificate_pdf(
            output_path=output_path,
            recipient_name=recipient_name,
            event_name=event_name,
            certificate_title=certificate_title,
            event_date=event_date,
            certificate_id=certificate_id,
        )
        return output_path


# Global instance
certificate_service = CertificateGeneratorService()

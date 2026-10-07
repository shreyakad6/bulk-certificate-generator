import math
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def draw_corner_ornament(c: canvas.Canvas, x: float, y: float, size: float = 12.0) -> None:
    """Draw a clean geometric corner ornament."""
    c.saveState()
    c.setStrokeColor(colors.HexColor("#C59B27"))
    c.setFillColor(colors.HexColor("#C59B27"))
    c.setLineWidth(1)
    # Small diamond accent
    diamond = c.beginPath()
    diamond.moveTo(x, y + size)
    diamond.lineTo(x + size, y)
    diamond.lineTo(x, y - size)
    diamond.lineTo(x - size, y)
    diamond.close()
    c.drawPath(diamond, fill=1, stroke=0)
    c.restoreState()


def draw_seal(c: canvas.Canvas, cx: float, cy: float, radius: float = 24.0) -> None:
    """Draw an elegant official seal emblem vector."""
    c.saveState()

    # Outer decorative notched ring
    num_teeth = 24
    outer_r = radius + 3
    inner_r = radius - 1
    c.setFillColor(colors.HexColor("#C59B27"))
    c.setStrokeColor(colors.HexColor("#A8811A"))
    c.setLineWidth(0.8)

    seal_path = c.beginPath()
    for i in range(num_teeth * 2):
        angle = i * (math.pi / num_teeth)
        r = outer_r if i % 2 == 0 else inner_r
        px = cx + r * math.cos(angle)
        py = cy + r * math.sin(angle)
        if i == 0:
            seal_path.moveTo(px, py)
        else:
            seal_path.lineTo(px, py)
    seal_path.close()
    c.drawPath(seal_path, fill=1, stroke=1)

    # Inner gold circle
    c.setFillColor(colors.HexColor("#0F2942"))
    c.setStrokeColor(colors.HexColor("#E5C158"))
    c.setLineWidth(1.5)
    c.circle(cx, cy, radius - 4, fill=1, stroke=1)

    # Core text inside seal
    c.setFillColor(colors.HexColor("#F7FAFC"))
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(cx, cy + 2, "OFFICIAL")
    c.drawCentredString(cx, cy - 6, "SEAL")

    c.restoreState()


def draw_signature_flourish(c: canvas.Canvas, start_x: float, y: float) -> None:
    """Draw a stylized signature flourish above the signature line."""
    c.saveState()
    c.setStrokeColor(colors.HexColor("#0F2942"))
    c.setLineWidth(1.4)
    # Smooth bezier curve simulating hand signature
    sig_path = c.beginPath()
    sig_path.moveTo(start_x + 15, y + 10)
    sig_path.curveTo(start_x + 35, y + 25, start_x + 45, y + 2, start_x + 70, y + 18)
    sig_path.curveTo(start_x + 90, y + 30, start_x + 110, y + 8, start_x + 140, y + 15)
    sig_path.curveTo(start_x + 160, y + 20, start_x + 175, y + 5, start_x + 190, y + 12)
    c.drawPath(sig_path, fill=0, stroke=1)
    c.restoreState()


def build_certificate_pdf(
    output_path: str,
    recipient_name: str,
    event_name: str,
    certificate_title: str,
    event_date: str,
    certificate_id: str,
    organization_name: str = "TechNova Academy",
) -> str:
    """
    Generate a professional Landscape A4 certificate PDF.

    Args:
        output_path: Absolute or relative file path to save the generated PDF.
        recipient_name: Full name of the recipient.
        event_name: Name of the event or course.
        certificate_title: Title (e.g. 'Certificate of Participation').
        event_date: Formatted date string for the event.
        certificate_id: Unique certificate UUID string.
        organization_name: Issuing organization.

    Returns:
        output_path on successful generation.
    """
    # Ensure destination directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Setup Landscape A4 Canvas (841.89 x 595.27 points)
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(output_path, pagesize=(page_width, page_height))
    c.setTitle(f"{certificate_title} - {recipient_name}")
    c.setAuthor(organization_name)
    c.setSubject(event_name)

    # Background fill
    c.setFillColor(colors.HexColor("#FCFDFD"))
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # Outer primary border (Deep Navy)
    outer_margin = 24.0
    c.setStrokeColor(colors.HexColor("#0F2942"))
    c.setLineWidth(3.0)
    c.rect(
        outer_margin,
        outer_margin,
        page_width - 2 * outer_margin,
        page_height - 2 * outer_margin,
        fill=0,
        stroke=1,
    )

    # Inner secondary border (Warm Gold)
    inner_margin = 32.0
    c.setStrokeColor(colors.HexColor("#C59B27"))
    c.setLineWidth(1.2)
    c.rect(
        inner_margin,
        inner_margin,
        page_width - 2 * inner_margin,
        page_height - 2 * inner_margin,
        fill=0,
        stroke=1,
    )

    # Corner diamond accents
    corner_offset = 32.0
    draw_corner_ornament(c, corner_offset, corner_offset)
    draw_corner_ornament(c, page_width - corner_offset, corner_offset)
    draw_corner_ornament(c, corner_offset, page_height - corner_offset)
    draw_corner_ornament(c, page_width - corner_offset, page_height - corner_offset)

    center_x = page_width / 2.0

    # 1. Organization Header
    c.setFillColor(colors.HexColor("#C59B27"))
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(center_x, page_height - 65, organization_name.upper())

    # Gold decorative separator under organization
    c.setStrokeColor(colors.HexColor("#C59B27"))
    c.setLineWidth(0.8)
    sep_width = 80
    c.line(center_x - sep_width, page_height - 74, center_x + sep_width, page_height - 74)

    # 2. Certificate Title (Dynamic, Uppercase)
    c.setFillColor(colors.HexColor("#0F2942"))
    title_font_size = 28 if len(certificate_title) <= 35 else 24
    c.setFont("Helvetica-Bold", title_font_size)
    c.drawCentredString(center_x, page_height - 120, certificate_title.upper())

    # 3. Presentation line
    c.setFillColor(colors.HexColor("#4A5568"))
    c.setFont("Helvetica-Oblique", 14)
    c.drawCentredString(center_x, page_height - 165, "This certificate is proudly presented to")

    # 4. Recipient Name (Prominent & Centered)
    c.setFillColor(colors.HexColor("#1A202C"))
    name_font_size = 32 if len(recipient_name) <= 28 else 26
    c.setFont("Helvetica-Bold", name_font_size)
    c.drawCentredString(center_x, page_height - 225, recipient_name)

    # Gold decorative underline under recipient name
    name_line_width = min(max(len(recipient_name) * 14, 220), 480)
    c.setStrokeColor(colors.HexColor("#C59B27"))
    c.setLineWidth(1.5)
    c.line(
        center_x - (name_line_width / 2),
        page_height - 238,
        center_x + (name_line_width / 2),
        page_height - 238,
    )

    # 5. Participation Statement
    c.setFillColor(colors.HexColor("#4A5568"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(center_x, page_height - 275, "for successfully participating in")

    # 6. Event Name
    c.setFillColor(colors.HexColor("#0F2942"))
    event_font_size = 20 if len(event_name) <= 40 else 17
    c.setFont("Helvetica-Bold", event_font_size)
    c.drawCentredString(center_x, page_height - 315, event_name)

    # 7. Event Date
    c.setFillColor(colors.HexColor("#718096"))
    c.setFont("Helvetica", 13)
    c.drawCentredString(center_x, page_height - 350, f"held on {event_date}")

    # ------------------- Bottom Section -------------------
    # Left: Official Seal & Certificate ID
    seal_x = 135.0
    seal_y = 105.0
    draw_seal(c, seal_x, seal_y, radius=22.0)

    c.setFillColor(colors.HexColor("#2D3748"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(175, 115, "CERTIFICATE ID:")

    c.setFillColor(colors.HexColor("#4A5568"))
    c.setFont("Helvetica", 8.5)
    c.drawString(175, 102, certificate_id)

    c.setFillColor(colors.HexColor("#A0AEC0"))
    c.setFont("Helvetica", 7.5)
    c.drawString(175, 90, "Officially verified & issued by TechNova Academy")

    # Right: Signature Block
    sig_start_x = page_width - 290.0
    sig_y = 95.0

    # Draw signature flourish
    draw_signature_flourish(c, sig_start_x, sig_y + 12)

    # Signature line
    c.setStrokeColor(colors.HexColor("#4A5568"))
    c.setLineWidth(1.0)
    c.line(sig_start_x, sig_y + 10, sig_start_x + 210, sig_y + 10)

    # Signature caption
    c.setFillColor(colors.HexColor("#1A202C"))
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(sig_start_x, sig_y - 6, "Authorized Signature")

    c.setFillColor(colors.HexColor("#718096"))
    c.setFont("Helvetica", 8.5)
    c.drawString(sig_start_x, sig_y - 18, f"Academic Director, {organization_name}")

    # Complete document
    c.showPage()
    c.save()

    return output_path

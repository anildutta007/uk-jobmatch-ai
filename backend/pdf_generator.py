"""
PDF Generator Module
Creates beautifully formatted, executive-standard PDF documents for tailored CVs and cover letters
using ReportLab with clean typography, borders, and structured layouts.
"""

import io
import re
from typing import List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Adds running footer with page numbers to every page."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        footer_text = f"Page {self._pageNumber} of {page_count}  •  Tailored Professional Application"
        self.drawRightString(A4[0] - 36, 20, footer_text)
        self.restoreState()


def clean_markdown_markup(text: str) -> str:
    """Cleans raw markdown formatting for ReportLab HTML-like paragraphs."""
    # Convert bold **text** to <b>text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Convert italic *text* to <i>text</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    # Convert markdown headers # Header to clean text
    text = re.sub(r'^#+\s*', '', text)
    return text.strip()


def build_cv_pdf(
    cv_text: str,
    candidate_name: str = "Candidate",
    target_role: str = "Target Position",
    target_company: str = "Target Company",
    key_skills: Optional[List[str]] = None
) -> bytes:
    """
    Generates a high-quality formatted PDF for an amended CV.
    Returns the binary PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom Palette
    primary_color = colors.HexColor("#0f172a")     # Slate 900
    brand_color = colors.HexColor("#4f46e5")       # Indigo 600
    accent_badge = colors.HexColor("#e0e7ff")      # Indigo 100
    text_dark = colors.HexColor("#1e293b")         # Slate 800
    text_muted = colors.HexColor("#475569")        # Slate 600
    border_color = colors.HexColor("#cbd5e1")      # Slate 300

    # Typography Styles
    name_style = ParagraphStyle(
        'CVName',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=3
    )

    role_style = ParagraphStyle(
        'CVRole',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=brand_color,
        spaceAfter=4
    )

    badge_style = ParagraphStyle(
        'CVBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=brand_color
    )

    section_heading = ParagraphStyle(
        'CVSectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'CVBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark,
        spaceAfter=3
    )

    bullet_style = ParagraphStyle(
        'CVBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=text_dark,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=2.5
    )

    callout_style = ParagraphStyle(
        'CVCallout',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=text_dark
    )

    story = []

    # 1. Header Block
    clean_name = candidate_name.strip() or "Candidate Profile"
    story.append(Paragraph(clean_name, name_style))
    story.append(Paragraph(f"Target Alignment: {target_role}", role_style))

    # Badge Table for Target Role & Company
    badge_text = f"<b>TAILORED SPECIFICATION:</b> Customized for {target_role} at {target_company}"
    badge_table = Table([[Paragraph(badge_text, badge_style)]], colWidths=['100%'])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), accent_badge),
        ('TEXTCOLOR', (0, 0), (-1, -1), brand_color),
        ('BOX', (0, 0), (-1, -1), 0.5, brand_color),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 8))

    # 2. Key Skills Highlight Bar (if provided)
    if key_skills:
        skills_str = "  •  ".join(key_skills[:10])
        skills_para = Paragraph(f"<b>Key Competencies Highlighted:</b> {skills_str}", callout_style)
        skills_box = Table([[skills_para]], colWidths=['100%'])
        skills_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(skills_box)
        story.append(Spacer(1, 8))

    # 3. Parse Markdown CV Text into Structured Sections
    lines = cv_text.splitlines()
    in_summary = False
    summary_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip main markdown name if already at top
        if stripped.startswith("# ") and clean_name.lower() in stripped.lower():
            continue

        # Section Headings (## Heading or UPPERCASE HEADING)
        if stripped.startswith("## ") or stripped.startswith("### ") or (
            stripped.isupper() and len(stripped) < 40 and not stripped.startswith("-") and not stripped.startswith("*")
        ):
            heading_text = clean_markdown_markup(stripped)
            story.append(Spacer(1, 4))
            story.append(Paragraph(heading_text.upper(), section_heading))
            story.append(HRFlowable(width="100%", thickness=1, color=brand_color, spaceAfter=6, spaceBefore=1))
            continue

        # Bullet points (- bullet, * bullet)
        if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("• "):
            content = clean_markdown_markup(stripped[2:])
            story.append(Paragraph(f"• &nbsp; {content}", bullet_style))
            continue

        # Normal text paragraph
        clean_line = clean_markdown_markup(stripped)
        if clean_line:
            story.append(Paragraph(clean_line, body_style))

    # Build the document with running footer
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def build_cover_letter_pdf(
    cover_letter_text: str,
    candidate_name: str = "Candidate",
    target_role: str = "Position",
    target_company: str = "Company"
) -> bytes:
    """
    Generates a beautifully formatted formal UK business cover letter in PDF format.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=44,
        rightMargin=44,
        topMargin=44,
        bottomMargin=44
    )

    styles = getSampleStyleSheet()

    body_style = ParagraphStyle(
        'LetterBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=10
    )

    header_style = ParagraphStyle(
        'LetterHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )

    story = []

    # Clean text into paragraphs
    paragraphs = cover_letter_text.strip().split("\n\n")
    for idx, para in enumerate(paragraphs):
        clean_para = clean_markdown_markup(para.replace("\n", "<br/>"))
        if idx == 0 and ("hiring" in clean_para.lower() or candidate_name.lower() in clean_para.lower()):
            story.append(Paragraph(clean_para, header_style))
        else:
            story.append(Paragraph(clean_para, body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

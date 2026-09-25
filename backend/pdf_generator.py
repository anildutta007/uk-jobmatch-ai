"""
PDF Generator Module
Creates executive-standard, print-ready PDF documents for tailored CVs and cover letters
using ReportLab with clean typography, balanced margins, and professional layouts.
No extraneous meta-tags or prospective employer references in the CV document.
"""

import io
import re
from typing import List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Adds a subtle, running professional footer with page numbers."""
    candidate_name = ""
    doc_label = "Curriculum Vitae"

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
        prefix = f"{NumberedCanvas.candidate_name}  •  " if NumberedCanvas.candidate_name else ""
        footer_text = f"{prefix}{NumberedCanvas.doc_label}  •  Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 18, footer_text)
        self.restoreState()


def clean_markdown_markup(text: str) -> str:
    """Cleans markdown formatting for ReportLab HTML-like paragraphs."""
    # Convert bold **text** to <b>text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Convert italic *text* or _text_ to <i>text</i>
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)(.*?)(?<!_)_(?!_)', r'<i>\1</i>', text)
    # Convert markdown headers # Header to clean text
    text = re.sub(r'^#+\s*', '', text)
    # Clean up empty tags
    text = text.replace("<b></b>", "").replace("<i></i>", "")
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
    Strictly excludes prospective employer names from the CV body and header.
    Produces a ready-to-submit executive UK resume.
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

    # Executive Color Palette
    primary_color = colors.HexColor("#0f172a")     # Slate 900
    brand_color = colors.HexColor("#4f46e5")       # Indigo 600
    text_dark = colors.HexColor("#1e293b")         # Slate 800
    text_muted = colors.HexColor("#475569")        # Slate 600

    # Typography Styles
    name_style = ParagraphStyle(
        'CVName',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=2
    )

    headline_style = ParagraphStyle(
        'CVHeadline',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=brand_color,
        spaceAfter=3
    )

    contact_style = ParagraphStyle(
        'CVContact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_muted,
        spaceAfter=6
    )

    section_heading = ParagraphStyle(
        'CVSectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=2
    )

    job_role_style = ParagraphStyle(
        'CVJobTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13.5,
        textColor=primary_color,
        spaceBefore=5,
        spaceAfter=1
    )
    job_title_style = job_role_style

    job_date_style = ParagraphStyle(
        'CVJobDate',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=text_muted,
        spaceAfter=2
    )

    body_style = ParagraphStyle(
        'CVBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=text_dark,
        spaceAfter=4
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
        spaceAfter=2
    )

    story = []

    # Parse metadata from CV lines
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]

    extracted_name = candidate_name.strip() if candidate_name and candidate_name != "Candidate" else ""
    extracted_headline = target_role.strip() if target_role and target_role != "Target Position" else ""
    extracted_contact = ""

    # Parse candidate header items
    non_section_lines = []
    for l in lines[:6]:
        if l.startswith("## ") or (l.isupper() and len(l) < 35 and "SUMMARY" in l):
            break
        non_section_lines.append(l)

    for l in non_section_lines:
        clean = l.replace("#", "").strip()
        if not extracted_name and len(clean) < 40 and not any(c in clean for c in ["@", "+", "|", "http"]):
            extracted_name = clean
        elif not extracted_headline and any(w in clean.lower() for w in [
            "developer", "engineer", "manager", "leader", "specialist", "architect", "lead", "director", "consultant"
        ]):
            extracted_headline = clean.replace("**", "").replace("*", "").strip()
        elif any(marker in clean.lower() for marker in ["@", "+44", "+", "uk", "london", "linkedin", "github"]):
            if not extracted_contact:
                extracted_contact = clean.replace("**", "").replace("*", "").strip()

    if not extracted_name:
        extracted_name = "Candidate Profile"
    if not extracted_headline:
        extracted_headline = "Experienced Professional"

    NumberedCanvas.candidate_name = extracted_name
    NumberedCanvas.doc_label = "Curriculum Vitae"

    # 1. Header Block (Ready-to-use executive layout)
    story.append(Paragraph(clean_markdown_markup(extracted_name), name_style))
    story.append(Paragraph(clean_markdown_markup(extracted_headline), headline_style))
    if extracted_contact:
        story.append(Paragraph(clean_markdown_markup(extracted_contact), contact_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_color, spaceAfter=8, spaceBefore=2))

    # 2. Parse Markdown CV Text into Structured Sections
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip main markdown name or contact line if already in header
        if stripped.startswith("# ") and extracted_name.lower() in stripped.lower():
            continue
        if extracted_contact and stripped.lower() in extracted_contact.lower():
            continue
        if extracted_headline and stripped.lower() in extracted_headline.lower():
            continue

        # Filter out any accidental meta-tag lines
        lower_line = stripped.lower()
        if any(marker in lower_line for marker in [
            "target role:", "targeted specification:", "customized for",
            "optimized and aligned with", "priority requirements for"
        ]):
            continue

        # Major Section Headings (## Heading or UPPERCASE HEADING)
        if stripped.startswith("## ") or (
            stripped.isupper() and len(stripped) < 40 and not stripped.startswith("-") and not stripped.startswith("*") and "|" not in stripped
        ):
            heading_text = clean_markdown_markup(stripped)
            story.append(Spacer(1, 4))
            story.append(Paragraph(heading_text.upper(), section_heading))
            story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor('#94a3b8'), spaceAfter=5, spaceBefore=1))
            continue

        # Job Role Sub-Headings (### Heading or Title | Company lines)
        if stripped.startswith("### "):
            role_text = clean_markdown_markup(stripped[4:])
            story.append(Spacer(1, 3))
            story.append(Paragraph(role_text, job_role_style))
            continue

        # Job Dates (*Date - Date* or (Date - Date))
        if (stripped.startswith("*") and stripped.endswith("*") and len(stripped) < 50) or (
            re.search(r"\b(19\d\d|20\d\d)\b", stripped) and ("-" in stripped or "–" in stripped or "present" in stripped.lower()) and len(stripped) < 50 and not stripped.startswith("-") and not stripped.startswith("•")
        ):
            date_text = clean_markdown_markup(stripped)
            story.append(Paragraph(date_text, job_date_style))
            continue

        # Bullet points (- bullet, * bullet, • bullet)
        if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("• "):
            content = clean_markdown_markup(stripped[2:])
            story.append(Paragraph(f"• &nbsp; {content}", bullet_style))
            continue

        # Normal text paragraph (e.g. Professional Summary)
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
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )

    story = []

    NumberedCanvas.candidate_name = candidate_name.strip() if candidate_name and candidate_name != "Candidate" else ""
    NumberedCanvas.doc_label = "Cover Letter"

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

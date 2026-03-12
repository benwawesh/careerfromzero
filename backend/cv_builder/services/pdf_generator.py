"""
CV PDF Generator
Generates PDF versions of tailored CVs using ReportLab
"""

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
import io
import re
import logging

logger = logging.getLogger(__name__)


class CVPDFGenerator:
    """Generate PDF from CV version text"""

    def __init__(self, cv_version):
        self.cv_version = cv_version
        self.cv_data = cv_version.cv.data
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='CVName',
            parent=self.styles['Normal'],
            fontSize=22,
            spaceAfter=4,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1e3a8a'),
            alignment=1,
        ))
        self.styles.add(ParagraphStyle(
            name='CVContact',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=12,
            textColor=colors.HexColor('#4b5563'),
            alignment=1,
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=14,
            spaceAfter=4,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1e40af'),
        ))
        self.styles.add(ParagraphStyle(
            name='CVBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=4,
            leading=15,
        ))
        self.styles.add(ParagraphStyle(
            name='CVBullet',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=16,
            spaceAfter=3,
            leading=14,
        ))
        self.styles.add(ParagraphStyle(
            name='CVSubheading',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=2,
            fontName='Helvetica-Bold',
        ))

    def generate_pdf(self):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        story = []
        self._add_header(story)

        optimized = self.cv_version.optimized_text
        if optimized and len(optimized.strip()) > 50:
            self._render_optimized_text(story, optimized)
        else:
            # Fallback: render from structured cv_data fields
            self._render_from_cv_data(story)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    # ------------------------------------------------------------------ #
    #  Header — always from cv_data contact fields                        #
    # ------------------------------------------------------------------ #

    def _add_header(self, story):
        name = self.cv_version.cv.title or "Curriculum Vitae"
        story.append(Paragraph(self._esc(name), self.styles['CVName']))

        parts = []
        if self.cv_data and self.cv_data.email:
            parts.append(self.cv_data.email)
        if self.cv_data and self.cv_data.phone:
            parts.append(self.cv_data.phone)
        if self.cv_data and self.cv_data.location:
            parts.append(self.cv_data.location)
        if self.cv_data and self.cv_data.linkedin_url:
            parts.append("LinkedIn")
        if self.cv_data and self.cv_data.github_url:
            parts.append("GitHub")

        if parts:
            story.append(Paragraph(" · ".join(self._esc(p) for p in parts), self.styles['CVContact']))

        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e40af'), spaceAfter=6))

    # ------------------------------------------------------------------ #
    #  Render Claude's optimized_text                                     #
    # ------------------------------------------------------------------ #

    # All-caps section header patterns Claude uses
    SECTION_RE = re.compile(
        r'^(PROFESSIONAL SUMMARY|SUMMARY|OBJECTIVE|WORK EXPERIENCE|EXPERIENCE|'
        r'EDUCATION|SKILLS|TECHNICAL SKILLS|PROJECTS|CERTIFICATIONS|LANGUAGES|'
        r'ACHIEVEMENTS|AWARDS|PUBLICATIONS|REFERENCES|VOLUNTEER|INTERESTS|PROFILE)\s*$',
        re.IGNORECASE | re.MULTILINE,
    )

    def _render_optimized_text(self, story, text):
        """
        Parse Claude's plain-text CV and render with proper styles.
        Sections are detected by ALL-CAPS lines; bullets by leading - or •.
        """
        lines = text.splitlines()
        i = 0
        in_section = False

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Blank line → small gap
            if not stripped:
                story.append(Spacer(1, 4))
                i += 1
                continue

            # Section header detection: all-caps, optional trailing colon
            clean = stripped.rstrip(':')
            if self.SECTION_RE.match(clean):
                story.append(Paragraph(self._esc(clean.upper()), self.styles['SectionHeading']))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#93c5fd'), spaceAfter=4))
                in_section = True
                i += 1
                continue

            # Bullet lines
            if stripped.startswith(('-', '•', '*', '–')):
                bullet_text = stripped.lstrip('-•*– ').strip()
                story.append(Paragraph(f"• {self._esc(bullet_text)}", self.styles['CVBullet']))
                i += 1
                continue

            # Bold subheading heuristic: short line that looks like "Job Title | Company | Year"
            # or lines with bold markers **text**
            if stripped.startswith('**') and stripped.endswith('**'):
                inner = stripped.strip('*').strip()
                story.append(Paragraph(f"<b>{self._esc(inner)}</b>", self.styles['CVSubheading']))
                i += 1
                continue

            # Regular paragraph line
            story.append(Paragraph(self._esc(stripped), self.styles['CVBody']))
            i += 1

    # ------------------------------------------------------------------ #
    #  Fallback: render from structured cv_data                          #
    # ------------------------------------------------------------------ #

    def _render_from_cv_data(self, story):
        if not self.cv_data:
            story.append(Paragraph("No CV content available.", self.styles['CVBody']))
            return

        if self.cv_data.summary:
            self._section(story, "PROFESSIONAL SUMMARY")
            story.append(Paragraph(self._esc(self.cv_data.summary), self.styles['CVBody']))

        if self.cv_data.experience:
            self._section(story, "WORK EXPERIENCE")
            for exp in self.cv_data.experience:
                role = exp.get('role', '')
                company = exp.get('company', '')
                duration = exp.get('duration', '')
                story.append(Paragraph(f"<b>{self._esc(role)}</b>", self.styles['CVSubheading']))
                story.append(Paragraph(self._esc(f"{company}  |  {duration}"), self.styles['CVBody']))
                if exp.get('description'):
                    story.append(Paragraph(self._esc(exp['description']), self.styles['CVBody']))
                story.append(Spacer(1, 6))

        if self.cv_data.education:
            self._section(story, "EDUCATION")
            for edu in self.cv_data.education:
                story.append(Paragraph(f"<b>{self._esc(edu.get('degree', ''))}</b>", self.styles['CVSubheading']))
                story.append(Paragraph(self._esc(f"{edu.get('institution', '')}  |  {edu.get('year', '')}"), self.styles['CVBody']))
                story.append(Spacer(1, 6))

        if self.cv_data.skills:
            self._section(story, "SKILLS")
            if isinstance(self.cv_data.skills, list):
                story.append(Paragraph(self._esc(", ".join(self.cv_data.skills)), self.styles['CVBody']))

        if self.cv_data.projects:
            self._section(story, "PROJECTS")
            for proj in self.cv_data.projects:
                story.append(Paragraph(f"<b>{self._esc(proj.get('name', ''))}</b>", self.styles['CVSubheading']))
                if proj.get('description'):
                    story.append(Paragraph(self._esc(proj['description']), self.styles['CVBody']))
                story.append(Spacer(1, 6))

        if self.cv_data.certifications:
            self._section(story, "CERTIFICATIONS")
            for cert in self.cv_data.certifications:
                story.append(Paragraph(f"• {self._esc(cert)}", self.styles['CVBullet']))

        if self.cv_data.languages:
            self._section(story, "LANGUAGES")
            story.append(Paragraph(self._esc(", ".join(self.cv_data.languages)), self.styles['CVBody']))

    def _section(self, story, title):
        story.append(Paragraph(title, self.styles['SectionHeading']))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#93c5fd'), spaceAfter=4))

    @staticmethod
    def _esc(text):
        """Escape XML special chars for ReportLab Paragraph."""
        if not text:
            return ""
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text

"""
CV PDF Generator
Generates PDF versions of tailored CVs using ReportLab
"""

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
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
        """Setup custom styles for CV"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CVTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.HexColor('#1e3a8a'),
            alignment=1,  # Center
        ))
        
        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=12,
            spaceAfter=8,
            textColor=colors.HexColor('#1e40af'),
            borderWidth=1,
            borderColor=colors.HexColor('#3b82f6'),
            borderPadding=5,
        ))
        
        # Normal text style
        self.styles.add(ParagraphStyle(
            name='CVBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leading=14,
        ))
        
        # Bullet style (use unique name to avoid conflict with ReportLab's default)
        self.styles.add(ParagraphStyle(
            name='CVBullet',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20,
            spaceAfter=4,
            leading=14,
        ))
        
        # Subheading style
        self.styles.add(ParagraphStyle(
            name='Subheading',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=4,
            fontName='Helvetica-Bold',
            leading=14,
        ))
    
    def generate_pdf(self):
        """Generate PDF from CV version"""
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )
        
        # Build story (content elements)
        story = []
        
        # Add header section
        self._add_header(story)
        story.append(Spacer(1, 20))
        
        # Add summary if available
        if self.cv_data.summary:
            self._add_section(story, 'Professional Summary', self.cv_data.summary)
        
        # Add experience
        if self.cv_data.experience:
            self._add_experience(story)
        
        # Add education
        if self.cv_data.education:
            self._add_education(story)
        
        # Add skills
        if self.cv_data.skills:
            self._add_skills(story)
        
        # Add projects
        if self.cv_data.projects:
            self._add_projects(story)
        
        # Add certifications
        if self.cv_data.certifications:
            self._add_certifications(story)
        
        # Add languages
        if self.cv_data.languages:
            self._add_languages(story)
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _add_header(self, story):
        """Add CV header with contact info"""
        # Name/Title
        name = f"<b>{self.cv_version.cv.title}</b>"
        story.append(Paragraph(name, self.styles['CVTitle']))
        
        # Contact information
        contact_lines = []
        if self.cv_data.email:
            contact_lines.append(f"📧 {self.cv_data.email}")
        if self.cv_data.phone:
            contact_lines.append(f"📱 {self.cv_data.phone}")
        if self.cv_data.location:
            contact_lines.append(f"📍 {self.cv_data.location}")
        if self.cv_data.linkedin_url:
            contact_lines.append(f"💼 LinkedIn")
        if self.cv_data.github_url:
            contact_lines.append(f"💻 GitHub")
        
        if contact_lines:
            contact_text = " | ".join(contact_lines)
            story.append(Paragraph(contact_text, self.styles['CVBody']))
    
    def _add_section(self, story, title, content):
        """Add a section with title and content"""
        story.append(Spacer(1, 12))
        story.append(Paragraph(title, self.styles['SectionHeading']))
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip(), self.styles['CVBody']))
    
    def _add_experience(self, story):
        """Add experience section"""
        story.append(Spacer(1, 12))
        story.append(Paragraph("Work Experience", self.styles['SectionHeading']))
        
        for exp in self.cv_data.experience:
            # Role and company
            role_line = f"<b>{exp.get('role', '')}</b>"
            company_line = f"{exp.get('company', '')} | {exp.get('duration', '')}"
            
            story.append(Paragraph(role_line, self.styles['Subheading']))
            story.append(Paragraph(company_line, self.styles['CVBody']))
            
            # Description if available
            if exp.get('description'):
                story.append(Paragraph(exp['description'], self.styles['CVBody']))
            
            story.append(Spacer(1, 8))
    
    def _add_education(self, story):
        """Add education section"""
        story.append(Spacer(1, 12))
        story.append(Paragraph("Education", self.styles['SectionHeading']))
        
        for edu in self.cv_data.education:
            degree_line = f"<b>{edu.get('degree', '')}</b>"
            school_line = f"{edu.get('institution', '')} | {edu.get('year', '')}"
            
            story.append(Paragraph(degree_line, self.styles['Subheading']))
            story.append(Paragraph(school_line, self.styles['CVBody']))
            story.append(Spacer(1, 8))
    
    def _add_skills(self, story):
        """Add skills section"""
        story.append(Spacer(1, 12))
        story.append(Paragraph("Skills", self.styles['SectionHeading']))
        
        # Group skills by category if available, otherwise list all
        if isinstance(self.cv_data.skills, list):
            skills_text = ", ".join(self.cv_data.skills)
            story.append(Paragraph(skills_text, self.styles['CVBody']))
    
    def _add_projects(self, story):
        """Add projects section"""
        story.append(Spacer(1, 12))
        story.append(Paragraph("Projects", self.styles['SectionHeading']))
        
        for proj in self.cv_data.projects:
            name_line = f"<b>{proj.get('name', '')}</b>"
            story.append(Paragraph(name_line, self.styles['Subheading']))
            
            if proj.get('description'):
                story.append(Paragraph(proj['description'], self.styles['CVBody']))
            
            if proj.get('technologies'):
                tech_line = f"<i>Technologies: {proj['technologies']}</i>"
                story.append(Paragraph(tech_line, self.styles['CVBody']))
            
            story.append(Spacer(1, 8))
    
    def _add_certifications(self, story):
        """Add certifications section"""
        story.append(Spacer(1, 12))
        story.append(Paragraph("Certifications", self.styles['SectionHeading']))
        
        for cert in self.cv_data.certifications:
            story.append(Paragraph(f"• {cert}", self.styles['CVBullet']))
    
    def _add_languages(self, story):
        """Add languages section"""
        story.append(Spacer(1, 12))
        story.append(Paragraph("Languages", self.styles['SectionHeading']))
        
        languages_text = ", ".join(self.cv_data.languages)
        story.append(Paragraph(languages_text, self.styles['CVBody']))
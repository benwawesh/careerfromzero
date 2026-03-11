"""
CV Parser Service
Extracts structured data from PDF and DOCX CV files
"""

import re
import logging
from typing import Dict, List, Any
from pathlib import Path

# PDF parsing
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("pdfplumber not installed. PDF parsing will be limited.")

# DOCX parsing
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logging.warning("python-docx not installed. DOCX parsing will be limited.")

logger = logging.getLogger(__name__)


class CVParser:
    """Parse CV files and extract structured data"""
    
    def __init__(self, file_path: str, file_type: str):
        """
        Initialize CV parser
        
        Args:
            file_path: Path to CV file
            file_type: File type (PDF or DOCX)
        """
        self.file_path = file_path
        self.file_type = file_type.upper()
        self.raw_text = ""
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse CV file and extract structured data
        
        Returns:
            Dictionary with parsed CV data
        """
        try:
            # Extract raw text
            self.raw_text = self._extract_text()
            
            if not self.raw_text:
                raise ValueError("No text extracted from CV")
            
            logger.info(f"Extracted {len(self.raw_text)} characters from CV")
            
            # Extract structured data
            data = {
                'raw_text': self.raw_text,
                'email': self._extract_email(),
                'phone': self._extract_phone(),
                'location': self._extract_location(),
                'linkedin_url': self._extract_linkedin(),
                'github_url': self._extract_github(),
                'website_url': self._extract_website(),
                'summary': self._extract_summary(),
                'skills': self._extract_skills(),
                'experience': self._extract_experience(),
                'education': self._extract_education(),
                'projects': self._extract_projects(),
                'certifications': self._extract_certifications(),
                'languages': self._extract_languages(),
                'interests': self._extract_interests(),
            }
            
            logger.info(f"Successfully parsed CV with {len(data['skills'])} skills and {len(data['experience'])} experiences")
            return data
            
        except Exception as e:
            logger.error(f"Error parsing CV: {str(e)}", exc_info=True)
            raise
    
    def _extract_text(self) -> str:
        """Extract raw text from file"""
        if self.file_type == 'PDF':
            return self._extract_pdf_text()
        elif self.file_type == 'DOCX':
            return self._extract_docx_text()
        else:
            raise ValueError(f"Unsupported file type: {self.file_type}")
    
    def _extract_pdf_text(self) -> str:
        """Extract text from PDF using pdfplumber"""
        if not PDF_AVAILABLE:
            raise ImportError("pdfplumber not installed")
        
        text_parts = []
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            raise
        
        return '\n'.join(text_parts)
    
    def _extract_docx_text(self) -> str:
        """Extract text from DOCX using python-docx"""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not installed")
        
        try:
            doc = Document(self.file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return '\n'.join(paragraphs)
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {str(e)}")
            raise
    
    def _extract_email(self) -> str:
        """Extract email address using regex"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, self.raw_text)
        return matches[0] if matches else None
    
    def _extract_phone(self) -> str:
        """Extract phone number using regex"""
        # Match various phone formats
        phone_patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # +1 (123) 456-7890
            r'\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # +1 123 456 7890
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (123) 456-7890 or 123-456-7890
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, self.raw_text)
            if matches:
                return matches[0]
        return None
    
    def _extract_location(self) -> str:
        """Extract location/city using pattern matching"""
        # Look for location keywords followed by location
        location_keywords = ['Location:', 'City:', 'Address:', 'Based in:', 'Located in:']
        
        for keyword in location_keywords:
            pattern = rf'{keyword}\s*([^\n]+)'
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_linkedin(self) -> str:
        """Extract LinkedIn URL"""
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        matches = re.findall(linkedin_pattern, self.raw_text)
        if matches:
            return f"https://{matches[0]}"
        return None
    
    def _extract_github(self) -> str:
        """Extract GitHub URL"""
        github_pattern = r'github\.com/[\w-]+'
        matches = re.findall(github_pattern, self.raw_text)
        if matches:
            return f"https://{matches[0]}"
        return None
    
    def _extract_website(self) -> str:
        """Extract personal website URL"""
        # Look for portfolio or website keywords
        website_pattern = r'(?:website|portfolio|portfolio)\s*:?\s*(https?://[^\s]+)'
        match = re.search(website_pattern, self.raw_text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Generic URL extraction (excluding LinkedIn and GitHub)
        url_pattern = r'https?://(?:www\.)?(?!linkedin|github)[^\s]+'
        matches = re.findall(url_pattern, self.raw_text)
        return matches[0] if matches else None
    
    def _extract_summary(self) -> str:
        """Extract professional summary/objective"""
        summary_keywords = ['Summary', 'Professional Summary', 'Objective', 'Profile', 'About']
        
        for keyword in summary_keywords:
            # Find section start
            pattern = rf'{keyword}\s*:?\s*([^\n]+(?:\n[^\n]+){{0,5}})'
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                # Get text until next section header
                summary_text = match.group(1)
                # Stop at next major section
                next_section = re.search(r'\n\s*(?:Experience|Education|Skills|Projects)\s*:?\s*:', summary_text)
                if next_section:
                    summary_text = summary_text[:next_section.start()]
                return summary_text.strip()
        
        return None
    
    def _extract_skills(self) -> List[str]:
        """Extract skills list"""
        skills = []
        
        # Look for skills section
        skills_keywords = ['Skills', 'Technical Skills', 'Technologies', 'Tech Stack', 'Competencies']
        
        for keyword in skills_keywords:
            pattern = rf'{keyword}\s*:?\s*([^\n]+(?:\n[^\n]+){{0,10}})'
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                skills_text = match.group(1)
                # Extract skills from comma-separated list, bullets, or pipe-separated
                # Remove common delimiters and split
                skills_text = re.sub(r'[\n•\-\*|/]', ',', skills_text)
                skills_text = re.sub(r'\s*,\s*', ',', skills_text)
                
                # Split and clean
                potential_skills = [s.strip() for s in skills_text.split(',')]
                
                # Filter out empty strings and common non-skill words
                common_words = ['and', 'or', 'the', 'with', 'including', 'etc', 'such as']
                skills = [s for s in potential_skills if s and len(s) > 1 and s.lower() not in common_words]
                
                if skills:
                    logger.info(f"Extracted {len(skills)} skills from '{keyword}' section")
                    break
        
        return skills[:50]  # Limit to top 50 skills
    
    def _extract_experience(self) -> List[Dict[str, Any]]:
        """Extract work experience"""
        experiences = []
        
        # Look for experience section
        experience_keywords = ['Experience', 'Work Experience', 'Work History', 'Employment']
        
        for keyword in experience_keywords:
            pattern = rf'{keyword}\s*:?\s*(.*?)(?=\n\s*(?:Education|Skills|Projects|Certifications)\s*:?\s*:|$)'
            match = re.search(pattern, self.raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                experience_text = match.group(1)
                
                # Try to extract individual experiences using common patterns
                # Pattern: Company/Role at Date
                exp_pattern = r'([^\n]+?)\s+(?:at|@|–|-)\s+([^\n]+?)\s+([A-Za-z]+\s+\d{4}\s*(?:–|-|to)\s*(?:present|[A-Za-z]+\s+\d{4}))'
                
                matches = re.findall(exp_pattern, experience_text, re.IGNORECASE)
                for role, company, duration in matches:
                    experiences.append({
                        'role': role.strip(),
                        'company': company.strip(),
                        'duration': duration.strip(),
                    })
                
                if experiences:
                    logger.info(f"Extracted {len(experiences)} experiences from '{keyword}' section")
                    break
        
        return experiences[:20]  # Limit to last 20 experiences
    
    def _extract_education(self) -> List[Dict[str, Any]]:
        """Extract education history"""
        educations = []
        
        # Look for education section
        education_keywords = ['Education', 'Academic', 'Qualifications', 'Degrees']
        
        for keyword in education_keywords:
            pattern = rf'{keyword}\s*:?\s*(.*?)(?=\n\s*(?:Experience|Skills|Projects)\s*:?\s*:|$)'
            match = re.search(pattern, self.raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                education_text = match.group(1)
                
                # Extract degree/institution/year
                # Pattern: Degree at Institution, Year
                edu_pattern = r'([^\n]+?)(?:\s+at\s+|\s*,\s*)([^\n,]+?),?\s*(\d{4})'
                
                matches = re.findall(edu_pattern, education_text, re.IGNORECASE)
                for degree, institution, year in matches:
                    educations.append({
                        'degree': degree.strip(),
                        'institution': institution.strip(),
                        'year': year.strip(),
                    })
                
                if educations:
                    logger.info(f"Extracted {len(educations)} education entries from '{keyword}' section")
                    break
        
        return educations[:10]  # Limit to last 10 education entries
    
    def _extract_projects(self) -> List[Dict[str, Any]]:
        """Extract projects"""
        projects = []
        
        # Look for projects section
        project_keywords = ['Projects', 'Personal Projects', 'Portfolio']
        
        for keyword in project_keywords:
            pattern = rf'{keyword}\s*:?\s*(.*?)(?=\n\s*(?:Experience|Education|Skills)\s*:?\s*:|$)'
            match = re.search(pattern, self.raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                project_text = match.group(1)
                
                # Extract project names and descriptions
                # Pattern: Project Name - Description
                project_pattern = r'([^\n]+?)\s*[-–]\s*([^\n]+)'
                
                matches = re.findall(project_pattern, project_text, re.IGNORECASE)
                for name, description in matches:
                    projects.append({
                        'name': name.strip(),
                        'description': description.strip()[:200],  # Limit description length
                    })
                
                if projects:
                    logger.info(f"Extracted {len(projects)} projects from '{keyword}' section")
                    break
        
        return projects[:20]  # Limit to top 20 projects
    
    def _extract_certifications(self) -> List[str]:
        """Extract certifications"""
        certifications = []
        
        # Look for certifications section
        cert_keywords = ['Certifications', 'Certificates', 'Credentials']
        
        for keyword in cert_keywords:
            pattern = rf'{keyword}\s*:?\s*([^\n]+(?:\n[^\n]+){{0,10}})'
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                cert_text = match.group(1)
                
                # Extract individual certifications
                cert_pattern = r'[A-Z][^,\n]+(?:\s+[A-Z][^,\n]+)*'
                matches = re.findall(cert_pattern, cert_text)
                
                certifications = [m.strip() for m in matches if len(m) > 10]
                
                if certifications:
                    logger.info(f"Extracted {len(certifications)} certifications from '{keyword}' section")
                    break
        
        return certifications[:20]  # Limit to top 20 certifications
    
    def _extract_languages(self) -> List[str]:
        """Extract languages"""
        languages = []
        
        # Look for languages section
        language_keywords = ['Languages', 'Language Proficiency']
        
        for keyword in language_keywords:
            pattern = rf'{keyword}\s*:?\s*([^\n]+)'
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                lang_text = match.group(1)
                
                # Extract languages
                lang_pattern = r'[A-Za-z]+\s*(?:\([^)]+\))?'
                matches = re.findall(lang_pattern, lang_text)
                
                languages = [m.strip() for m in matches if m.lower() not in ['language', 'languages']]
                
                if languages:
                    logger.info(f"Extracted {len(languages)} languages from '{keyword}' section")
                    break
        
        return languages[:10]  # Limit to top 10 languages
    
    def _extract_interests(self) -> List[str]:
        """Extract interests/hobbies"""
        interests = []
        
        # Look for interests section
        interest_keywords = ['Interests', 'Hobbies', 'Activities', 'Personal']
        
        for keyword in interest_keywords:
            pattern = rf'{keyword}\s*:?\s*([^\n]+)'
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                interest_text = match.group(1)
                
                # Extract interests
                interest_pattern = r'[A-Za-z][^,]+'
                matches = re.findall(interest_pattern, interest_text)
                
                interests = [m.strip() for m in matches if len(m) > 2]
                
                if interests:
                    logger.info(f"Extracted {len(interests)} interests from '{keyword}' section")
                    break
        
        return interests[:20]  # Limit to top 20 interests
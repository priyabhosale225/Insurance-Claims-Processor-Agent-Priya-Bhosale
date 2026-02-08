"""
Document Text Extractor
Supports both PDF and TXT file formats.
"""
import os


class DocumentExtractor:
    """Extracts raw text from PDF and TXT documents."""

    def extract(self, filepath: str) -> str:
        """
        Extract text from a document file.
        Automatically detects file type (PDF or TXT) and uses appropriate method.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()

        if ext == '.pdf':
            return self._extract_from_pdf(filepath)
        elif ext == '.txt':
            return self._extract_from_txt(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}. Only PDF and TXT are supported.")

    def _extract_from_pdf(self, filepath: str) -> str:
        """Extract text from a PDF file using pdfplumber."""
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except Exception as e:
            # Fallback to pypdf if pdfplumber fails
            try:
                from pypdf import PdfReader
                reader = PdfReader(filepath)
                text_parts = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                return "\n\n".join(text_parts)
            except Exception as e2:
                raise RuntimeError(f"Failed to extract text from PDF: {e}, fallback also failed: {e2}")

    def _extract_from_txt(self, filepath: str) -> str:
        """Extract text from a TXT file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            with open(filepath, 'r', encoding='latin-1') as f:
                return f.read()
"""
Document text extraction service.

Responsible only for extracting raw text from supported document formats.

Supported:
- PDF (.pdf)
- Microsoft Word (.docx)
- Plain Text (.txt)

This service performs NO cleaning or chunking.
"""

from pathlib import Path

import fitz  # PyMuPDF
from docx import Document


class TextExtractor:
    """Extract raw text from uploaded documents."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx"}

    def extract(self, file_path: str) -> str:
        """
        Detect the document type and extract text.

        Args:
            file_path: Absolute path of uploaded document.

        Returns:
            Raw extracted text.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}")

        if suffix == ".pdf":
            return self._extract_pdf(path)

        if suffix == ".docx":
            return self._extract_docx(path)

        if suffix == ".txt":
            return self._extract_txt(path)

        if suffix == ".csv":
            return self._extract_csv(path)

        if suffix == ".xlsx":
            return self._extract_xlsx(path)

        raise ValueError(f"Unsupported document type: {suffix}")

    def _extract_pdf(self, path: Path) -> str:
        """Extract text from PDF using PyMuPDF."""

        text = []

        with fitz.open(path) as pdf:
            for page in pdf:
                text.append(page.get_text())

        return "\n".join(text)

    def _extract_docx(self, path: Path) -> str:
        """Extract text from Microsoft Word."""

        document = Document(path)

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        return "\n".join(paragraphs)

    def _extract_txt(self, path: Path) -> str:
        """Extract text from plain text file."""

        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    def _extract_csv(self, path: Path) -> str:
        """Extract text from CSV."""
        import csv
        text = []
        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    text.append(" ".join(cell.strip() for cell in row if cell.strip()))
        return "\n".join(text)

    def _extract_xlsx(self, path: Path) -> str:
        """Extract text from XLSX spreadsheet using openpyxl."""
        import openpyxl
        text = []
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for sheet in wb.worksheets:
            text.append(f"Sheet: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                row_str = " ".join(str(cell).strip() for cell in row if cell is not None and str(cell).strip())
                if row_str:
                    text.append(row_str)
        return "\n".join(text)

    def extract_pages(self, file_path: str) -> list[tuple[int, str]]:
        """
        Extract text from document page-by-page.
        Returns a list of (page_number, text) tuples.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            pages = []
            with fitz.open(path) as pdf:
                for idx, page in enumerate(pdf):
                    pages.append((idx + 1, page.get_text()))
            return pages
        # For non-page-based formats, return the entire extracted text as page 1
        return [(1, self.extract(file_path))]
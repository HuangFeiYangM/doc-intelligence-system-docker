"""
Document parser module for extracting text from various document formats.
"""
import os
from pathlib import Path
from typing import Optional, Union

import pandas as pd
import pdfplumber
from docx import Document as DocxDocument

from app.config import get_settings
from app.models import DocumentType

settings = get_settings()


class DocumentParserError(Exception):
    """Exception raised for document parsing errors."""
    pass


class DocumentParser:
    """Parser for extracting text from PDF, Word, and Excel documents."""

    @staticmethod
    def get_document_type(file_path: Union[str, Path]) -> DocumentType:
        """Determine document type from file extension."""
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return DocumentType.PDF
        elif ext in [".docx", ".doc"]:
            return DocumentType.WORD
        elif ext in [".xlsx", ".xls"]:
            return DocumentType.EXCEL
        else:
            raise DocumentParserError(f"Unsupported file extension: {ext}")

    @staticmethod
    def parse_pdf(file_path: Union[str, Path]) -> str:
        """Extract text from PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            DocumentParserError: If parsing fails
        """
        try:
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            raise DocumentParserError(f"Failed to parse PDF: {str(e)}")

    @staticmethod
    def parse_word(file_path: Union[str, Path]) -> str:
        """Extract text from Word document.

        Args:
            file_path: Path to the Word document

        Returns:
            Extracted text content

        Raises:
            DocumentParserError: If parsing fails
        """
        try:
            doc = DocxDocument(file_path)
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_parts.append(" | ".join(row_text))

            return "\n".join(text_parts)
        except Exception as e:
            raise DocumentParserError(f"Failed to parse Word document: {str(e)}")

    @staticmethod
    def parse_excel(file_path: Union[str, Path]) -> str:
        """Extract text from Excel file.

        Args:
            file_path: Path to the Excel file

        Returns:
            Extracted text content (CSV-like format)

        Raises:
            DocumentParserError: If parsing fails
        """
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            text_parts = []

            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                text_parts.append(f"Sheet: {sheet_name}")
                text_parts.append(df.to_string(index=False))
                text_parts.append("-" * 50)

            return "\n".join(text_parts)
        except Exception as e:
            raise DocumentParserError(f"Failed to parse Excel file: {str(e)}")

    @classmethod
    def extract_text(cls, file_path: Union[str, Path]) -> str:
        """Unified entry point for extracting text from any supported document.

        Args:
            file_path: Path to the document file

        Returns:
            Extracted text content

        Raises:
            DocumentParserError: If file not found or parsing fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise DocumentParserError(f"File not found: {file_path}")

        doc_type = cls.get_document_type(file_path)

        if doc_type == DocumentType.PDF:
            return cls.parse_pdf(file_path)
        elif doc_type == DocumentType.WORD:
            return cls.parse_word(file_path)
        elif doc_type == DocumentType.EXCEL:
            return cls.parse_excel(file_path)
        else:
            raise DocumentParserError(f"Unsupported document type: {doc_type}")

    @classmethod
    def extract_text_with_metadata(cls, file_path: Union[str, Path]) -> dict:
        """Extract text with metadata.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary containing text content and metadata
        """
        file_path = Path(file_path)
        text = cls.extract_text(file_path)
        doc_type = cls.get_document_type(file_path)

        return {
            "text": text,
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "document_type": doc_type.value,
        }

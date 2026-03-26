"""
Tests for data models.
"""
import uuid
from datetime import datetime

import pytest

from app.models import Task, Document, Template, TaskStatus, DocumentType


class TestTaskModel:
    """Test cases for Task model."""

    def test_task_creation(self):
        """Test creating a Task instance."""
        task_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())

        task = Task(
            id=task_id,
            document_id=doc_id,
            status=TaskStatus.PENDING,
            progress=0,
        )

        assert task.id == task_id
        assert task.document_id == doc_id
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0
        # created_at is set at database level, not during Python instantiation

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_task_with_all_fields(self):
        """Test creating a Task with all fields populated."""
        task = Task(
            id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            template_id=str(uuid.uuid4()),
            status=TaskStatus.COMPLETED,
            progress=100,
            extracted_data={"field1": "value1", "field2": "value2"},
            output_file_path="/path/to/output.xlsx",
            error_message=None,
        )

        assert task.extracted_data == {"field1": "value1", "field2": "value2"}
        assert task.output_file_path == "/path/to/output.xlsx"


class TestDocumentModel:
    """Test cases for Document model."""

    def test_document_creation(self):
        """Test creating a Document instance."""
        doc_id = str(uuid.uuid4())

        doc = Document(
            id=doc_id,
            filename="test.pdf",
            original_filename="original.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            doc_type=DocumentType.PDF,
            mime_type="application/pdf",
        )

        assert doc.id == doc_id
        assert doc.filename == "test.pdf"
        assert doc.original_filename == "original.pdf"
        assert doc.file_size == 1024
        assert doc.doc_type == DocumentType.PDF
        assert doc.mime_type == "application/pdf"

    def test_document_type_values(self):
        """Test DocumentType enum values."""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.WORD.value == "word"
        assert DocumentType.EXCEL.value == "excel"

    def test_document_with_extracted_text(self):
        """Test Document with extracted text."""
        doc = Document(
            id=str(uuid.uuid4()),
            filename="test.docx",
            original_filename="test.docx",
            file_path="/uploads/test.docx",
            file_size=2048,
            doc_type=DocumentType.WORD,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            extracted_text="This is the extracted text content.",
        )

        assert doc.extracted_text == "This is the extracted text content."


class TestTemplateModel:
    """Test cases for Template model."""

    def test_template_creation(self):
        """Test creating a Template instance."""
        template_id = str(uuid.uuid4())

        template = Template(
            id=template_id,
            name="Contract Template",
            description="Template for contract documents",
            file_path="/templates/contract.xlsx",
            field_mapping={
                "合同编号": "B2",
                "甲方": "B3",
                "金额": "B4",
            },
        )

        assert template.id == template_id
        assert template.name == "Contract Template"
        assert template.description == "Template for contract documents"
        assert template.field_mapping["合同编号"] == "B2"

    def test_template_field_mapping(self):
        """Test Template field mapping structure."""
        mapping = {
            "字段1": "A1",
            "字段2": "B2",
            "字段3": "C3",
        }

        template = Template(
            id=str(uuid.uuid4()),
            name="Test",
            file_path="/test.xlsx",
            field_mapping=mapping,
        )

        assert len(template.field_mapping) == 3
        assert "字段1" in template.field_mapping


class TestModelRelationships:
    """Tests for model relationships."""

    def test_task_document_relationship(self):
        """Test Task-Document relationship."""
        # Note: This test validates the model structure
        # Full relationship testing requires database

        doc = Document(
            id=str(uuid.uuid4()),
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1000,
            doc_type=DocumentType.PDF,
            mime_type="application/pdf",
        )

        task = Task(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            status=TaskStatus.PENDING,
        )

        assert task.document_id == doc.id

    def test_task_template_relationship(self):
        """Test Task-Template relationship."""
        template = Template(
            id=str(uuid.uuid4()),
            name="Invoice Template",
            file_path="/templates/invoice.xlsx",
            field_mapping={"发票号": "A1"},
        )

        task = Task(
            id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            template_id=template.id,
            status=TaskStatus.PENDING,
        )

        assert task.template_id == template.id
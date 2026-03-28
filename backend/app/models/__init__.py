"""
SQLAlchemy models for the document intelligence system.
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Enum, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class TaskStatus(str, enum.Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    """Document type enumeration."""
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"


class Task(Base):
    """Task model for document processing."""

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    progress = Column(Integer, default=0)  # 0-100

    # Document info
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    template_id = Column(String(36), ForeignKey("templates.id"), nullable=True)

    # Processing results
    extracted_data = Column(JSON, nullable=True)
    output_file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="tasks")
    template = relationship("Template", back_populates="tasks")


class Document(Base):
    """Document model for uploaded files."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    doc_type = Column(Enum(DocumentType), nullable=False)
    mime_type = Column(String(100), nullable=False)

    # Content (optional, for small documents)
    extracted_text = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="document")


class Template(Base):
    """Excel template model."""

    __tablename__ = "templates"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)

    # Field mapping configuration (JSON)
    # Example: {"字段1": "A1", "字段2": "B2"}
    field_mapping = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="template")

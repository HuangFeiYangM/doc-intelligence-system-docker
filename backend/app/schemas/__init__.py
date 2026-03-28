"""
Pydantic schemas for request and response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import TaskStatus, DocumentType


# Task Schemas
class TaskBase(BaseModel):
    document_id: str
    template_id: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    progress: int
    document_id: str
    template_id: Optional[str]
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    extracted_data: Optional[Dict[str, Any]] = None
    output_file_path: Optional[str] = None


# Document Schemas
class DocumentBase(BaseModel):
    filename: str
    doc_type: DocumentType


class DocumentCreate(DocumentBase):
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str
    file_size: int
    doc_type: str
    mime_type: str
    created_at: Optional[datetime] = None


# Template Schemas
class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None


class TemplateCreate(TemplateBase):
    field_mapping: Dict[str, str]


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str]
    field_mapping: Dict[str, str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TemplateListResponse(BaseModel):
    templates: List[TemplateResponse]


# Upload Response
class UploadResponse(BaseModel):
    document_id: str
    task_id: str
    message: str


# Error Response
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
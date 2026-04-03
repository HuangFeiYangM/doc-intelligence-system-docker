"""
Document upload API endpoints.
"""
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, DocumentType, User
from app.schemas import DocumentResponse, UploadResponse, ErrorResponse
from app.services import TaskService
from app.utils.file_utils import validate_file_type, save_upload_file

router = APIRouter(prefix="/documents", tags=["Documents"])
settings = get_settings()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    template_id: Optional[UUID4] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document for processing.

    Args:
        file: The document file to upload (PDF, Word, or Excel, max 500MB)
        template_id: Optional template ID to use for processing
        db: Database session

    Returns:
        Upload response with document and task IDs
    """
    # Check file size
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB"
        )

    # Validate file type
    if not validate_file_type(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )

    # Generate unique ID and filename
    doc_id = str(uuid.uuid4())
    original_filename = file.filename
    file_ext = Path(original_filename).suffix.lower()
    stored_filename = f"{doc_id}{file_ext}"
    file_path = settings.UPLOAD_DIR / stored_filename

    # Determine document type
    doc_type_map = {
        ".pdf": DocumentType.PDF,
        ".docx": DocumentType.WORD,
        ".doc": DocumentType.WORD,
        ".xlsx": DocumentType.EXCEL,
        ".xls": DocumentType.EXCEL,
    }
    doc_type = doc_type_map.get(file_ext, DocumentType.PDF)

    # Save file
    try:
        file_size = await save_upload_file(file, file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Create document record
    document = Document(
        id=doc_id,
        filename=stored_filename,
        original_filename=original_filename,
        file_path=str(file_path),
        file_size=file_size,
        doc_type=doc_type,
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(document)
    await db.flush()

    # Create processing task
    task_service = TaskService(db)
    task = await task_service.create_task(document.id, template_id)

    # Commit transaction
    await db.commit()

    return UploadResponse(
        document_id=document.id,
        task_id=task.id,
        message="Document uploaded successfully. Processing started."
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document information.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        Document information
    """
    from sqlalchemy.future import select
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document
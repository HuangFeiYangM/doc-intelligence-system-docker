"""
Template management API endpoints.
"""
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Template, User
from app.repositories import TemplateRepository
from app.schemas import TemplateCreate, TemplateResponse, TemplateListResponse, ErrorResponse

router = APIRouter(prefix="/templates", tags=["Templates"])
settings = get_settings()


def secure_filename(filename: str) -> str:
    """Secure a filename by removing potentially dangerous characters."""
    # Remove path traversal characters
    filename = Path(filename).name
    # Keep only safe characters
    import re
    filename = re.sub(r'[^\w\s.-]', '', filename).strip()
    return filename


@router.post("", response_model=TemplateResponse)
async def create_template(
    name: str = Form(..., min_length=1, max_length=255),
    description: Optional[str] = Form(None, max_length=1000),
    field_mapping: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new Excel template.

    Args:
        name: Template name
        description: Template description
        field_mapping: JSON string mapping field names to cell addresses
        file: Optional Excel template file (max 500MB)
        db: Database session

    Returns:
        Created template
    """
    import json
    try:
        mapping = json.loads(field_mapping)
        if not isinstance(mapping, dict):
            raise ValueError("field_mapping must be a JSON object")
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid field_mapping JSON"
        )

    # Validate file if provided
    if file:
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB"
            )

        # Validate file extension
        safe_filename = secure_filename(file.filename)
        ext = Path(safe_filename).suffix.lower()

        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )

    template_id = str(uuid.uuid4())
    file_path = None

    if file:
        # Save uploaded file
        ext = Path(safe_filename).suffix.lower()
        stored_filename = f"{template_id}{ext}"
        file_path = settings.TEMPLATE_DIR / stored_filename

        try:
            content = await file.read()
            # Use async file write (simulated with thread pool in production)
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save template file: {str(e)}"
            )
    else:
        # Create empty template
        from app.services import TableGenerator
        file_path = settings.TEMPLATE_DIR / f"{template_id}.xlsx"
        try:
            headers = list(mapping.keys())
            TableGenerator.create_template(file_path, headers, mapping)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create template: {str(e)}"
            )

    template = Template(
        id=template_id,
        name=name,
        description=description,
        file_path=str(file_path),
        field_mapping=mapping
    )

    repo = TemplateRepository(db)
    try:
        template = await repo.create(template)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )

    return template


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all available templates.

    Args:
        limit: Maximum number of results
        offset: Number of results to skip
        db: Database session

    Returns:
        List of templates
    """
    repo = TemplateRepository(db)
    templates = await repo.list_all(limit, offset)
    return TemplateListResponse(templates=templates)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a template by ID.

    Args:
        template_id: Template ID
        db: Database session

    Returns:
        Template information
    """
    repo = TemplateRepository(db)
    template = await repo.get_by_id(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a template.

    Args:
        template_id: Template ID
        db: Database session

    Returns:
        Deletion result
    """
    repo = TemplateRepository(db)
    deleted = await repo.delete(template_id)
    await db.commit()

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return {"message": "Template deleted successfully"}
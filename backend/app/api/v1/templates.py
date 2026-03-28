"""
Template management API endpoints.
"""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Template
from app.repositories import TemplateRepository
from app.schemas import TemplateCreate, TemplateResponse, TemplateListResponse

router = APIRouter(prefix="/templates", tags=["Templates"])
settings = get_settings()


@router.post("", response_model=TemplateResponse)
async def create_template(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    field_mapping: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """Create a new Excel template.

    Args:
        name: Template name
        description: Template description
        field_mapping: JSON string mapping field names to cell addresses
        file: Optional Excel template file
        db: Database session

    Returns:
        Created template
    """
    import json
    try:
        mapping = json.loads(field_mapping)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid field_mapping JSON"
        )

    template_id = str(uuid.uuid4())
    file_path = None

    if file:
        # Save uploaded file
        ext = Path(file.filename).suffix
        stored_filename = f"{template_id}{ext}"
        file_path = settings.TEMPLATE_DIR / stored_filename

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    else:
        # Create empty template
        from app.services import TableGenerator
        file_path = settings.TEMPLATE_DIR / f"{template_id}.xlsx"
        headers = list(mapping.keys())
        TableGenerator.create_template(file_path, headers, mapping)

    template = Template(
        id=template_id,
        name=name,
        description=description,
        file_path=str(file_path),
        field_mapping=mapping
    )

    repo = TemplateRepository(db)
    template = await repo.create(template)
    await db.commit()

    return template


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
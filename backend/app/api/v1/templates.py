"""
模板管理 API 端点。
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

router = APIRouter(prefix="/templates", tags=["templates"])
settings = get_settings()


def secure_filename(filename: str) -> str:
    """通过移除潜在危险字符来保护文件名。"""
    # 移除路径遍历字符
    filename = Path(filename).name
    # 仅保留安全字符
    import re
    filename = re.sub(r'[^\w\s.-]', '', filename).strip()
    return filename


@router.post("", response_model=TemplateResponse, summary="创建模板", description="创建一个新的 Excel 模板")
async def create_template(
    name: str = Form(..., min_length=1, max_length=255, description="模板名称"),
    description: Optional[str] = Form(None, max_length=1000, description="模板描述（可选）"),
    field_mapping: str = Form(..., description="JSON 字符串，映射字段名到单元格地址"),
    file: Optional[UploadFile] = File(None, description="可选的 Excel 模板文件（最大 500MB）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建一个新的 Excel 模板。

    Args:
        name: 模板名称
        description: 模板描述
        field_mapping: JSON 字符串，映射字段名到单元格地址
        file: 可选的 Excel 模板文件（最大 500MB）
        db: 数据库会话

    Returns:
        创建的模板
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


@router.get("", response_model=TemplateListResponse, summary="模板列表", description="列出所有可用模板")
async def list_templates(
    limit: int = Query(100, ge=1, le=1000, description="返回结果的最大数量"),
    offset: int = Query(0, ge=0, description="跳过的结果数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """列出所有可用模板。

    Args:
        limit: 返回结果的最大数量
        offset: 跳过的结果数量
        db: 数据库会话

    Returns:
        模板列表
    """
    repo = TemplateRepository(db)
    templates = await repo.list_all(limit, offset)
    return TemplateListResponse(templates=templates)


@router.get("/{template_id}", response_model=TemplateResponse, summary="获取模板", description="根据ID获取模板信息")
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据ID获取模板信息。

    Args:
        template_id: 模板ID
        db: 数据库会话

    Returns:
        模板信息
    """
    repo = TemplateRepository(db)
    template = await repo.get_by_id(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return template


@router.delete("/{template_id}", summary="删除模板", description="删除指定的模板")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除指定的模板。

    Args:
        template_id: 模板ID
        db: 数据库会话

    Returns:
        删除结果
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

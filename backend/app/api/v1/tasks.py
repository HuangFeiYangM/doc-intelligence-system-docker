"""
任务管理 API 端点。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import TaskStatus, User
from app.schemas import (
    TaskResponse,
    TaskStatusResponse,
    TaskResultResponse,
    ErrorResponse
)
from app.services import TaskService, TaskServiceError

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}/status", response_model=TaskStatusResponse, summary="获取任务状态", description="获取处理任务的状态")
async def get_task_status(
    task_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取处理任务的状态。

    Args:
        task_id: 任务ID（UUID格式）
        db: 数据库会话

    Returns:
        任务状态信息
    """
    task_service = TaskService(db)
    try:
        return await task_service.get_task_status(str(task_id))
    except TaskServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{task_id}/result", response_model=TaskResultResponse, summary="获取任务结果", description="获取已完成任务的提取结果")
async def get_task_result(
    task_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取已完成任务的提取结果。

    Args:
        task_id: 任务ID（UUID格式）
        db: 数据库会话

    Returns:
        任务结果，包含提取的数据
    """
    task_service = TaskService(db)
    task = await task_service.get_task(str(task_id))

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return TaskResultResponse(
        task_id=task.id,
        status=task.status.value,
        extracted_data=task.extracted_data
    )


@router.get("", response_model=list[TaskResponse], summary="任务列表", description="列出任务，支持按状态筛选")
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="按任务状态筛选"),
    limit: int = Query(100, ge=1, le=1000, description="返回结果的最大数量"),
    offset: int = Query(0, ge=0, description="跳过的结果数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """列出任务，支持按状态筛选。

    Args:
        status: 按任务状态筛选
        limit: 返回结果的最大数量
        offset: 跳过的结果数量
        db: 数据库会话

    Returns:
        任务列表
    """
    task_service = TaskService(db)
    tasks = await task_service.list_tasks(status, limit, offset)
    return tasks


@router.post("/{task_id}/cancel", response_model=ErrorResponse, summary="取消任务", description="取消一个待处理的任务")
async def cancel_task(
    task_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消一个待处理的任务。

    Args:
        task_id: 任务ID（UUID格式）
        db: 数据库会话

    Returns:
        取消结果
    """
    task_service = TaskService(db)
    cancelled = await task_service.cancel_task(str(task_id))

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found or cannot be cancelled (already processing/completed)"
        )

    return ErrorResponse(error="Success", detail="Task cancelled successfully")

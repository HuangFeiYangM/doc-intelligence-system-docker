"""
Task management API endpoints.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import TaskStatus
from app.schemas import (
    TaskResponse,
    TaskStatusResponse,
    TaskResultResponse,
    ErrorResponse
)
from app.services import TaskService, TaskServiceError

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the status of a processing task.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Task status information
    """
    task_service = TaskService(db)
    try:
        return await task_service.get_task_status(task_id)
    except TaskServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the result of a completed task.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Task result with extracted data
    """
    task_service = TaskService(db)
    task = await task_service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return TaskResultResponse(
        task_id=task.id,
        status=task.status.value,
        extracted_data=task.extracted_data,
        output_file_path=task.output_file_path
    )


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List tasks with optional filtering.

    Args:
        status: Filter by task status
        limit: Maximum number of results
        offset: Number of results to skip
        db: Database session

    Returns:
        List of tasks
    """
    task_service = TaskService(db)
    tasks = await task_service.list_tasks(status, limit, offset)
    return tasks


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending task.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Cancellation result
    """
    task_service = TaskService(db)
    cancelled = await task_service.cancel_task(task_id)

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found or cannot be cancelled (already processing/completed)"
        )

    return {"message": "Task cancelled successfully"}
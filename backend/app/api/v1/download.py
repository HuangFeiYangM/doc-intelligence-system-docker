"""
File download API endpoints.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import TaskService

router = APIRouter(prefix="/download", tags=["Download"])


@router.get("/{task_id}")
async def download_result(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download the generated Excel file for a completed task.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        File download response
    """
    task_service = TaskService(db)
    task = await task_service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    if task.status.value != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task not completed. Current status: {task.status.value}"
        )

    if not task.output_file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output file not found"
        )

    file_path = Path(task.output_file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output file not found on disk"
        )

    return FileResponse(
        path=str(file_path),
        filename=f"result_{task_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
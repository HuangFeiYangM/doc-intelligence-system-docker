"""
Task repository for database operations.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import Task, TaskStatus


class TaskRepository:
    """Repository for Task model operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task: Task) -> Task:
        """Create a new task."""
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: str) -> Optional[Task]:
        """Get task by ID with relationships loaded."""
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.document), selectinload(Task.template))
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[int] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        extracted_data: Optional[dict] = None,
        output_file_path: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update task status and related fields."""
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            return False

        task.status = status
        if progress is not None:
            task.progress = progress
        if started_at:
            task.started_at = started_at
        if completed_at:
            task.completed_at = completed_at
        if extracted_data is not None:
            task.extracted_data = extracted_data
        if output_file_path:
            task.output_file_path = output_file_path
        if error_message:
            task.error_message = error_message

        await self.db.flush()
        return True

    async def update_progress(self, task_id: str, progress: int) -> bool:
        """Update task progress percentage."""
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            return False

        task.progress = progress
        await self.db.flush()
        return True

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """List tasks with optional filtering."""
        query = select(Task).order_by(Task.created_at.desc())

        if status:
            query = query.where(Task.status == status)

        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

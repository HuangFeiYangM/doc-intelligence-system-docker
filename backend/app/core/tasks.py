"""
Celery background tasks.
"""
import asyncio

from app.core.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.services import TaskService


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, task_id: str):
    """Process document in background using Celery.

    Args:
        task_id: Task ID to process
    """
    async def _process():
        async with AsyncSessionLocal() as db:
            task_service = TaskService(db)
            try:
                await task_service.process_task(task_id)
                return {"status": "completed", "task_id": task_id}
            except Exception as exc:
                # Retry on failure
                raise self.retry(exc=exc, countdown=60)

    # Run async function in Celery worker
    return asyncio.run(_process())

"""
Celery background tasks.
"""
import asyncio
import logging
import datetime
from app.core.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.services import TaskService

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, name='process_document_task')
def process_document_task(self, task_id: str):
    """Process document in background using Celery.

    Args:
        task_id: Task ID to process
    """
    print(f"[Celery Task] 收到任务: {task_id}")
    
    async def _process():
        print(f"[Celery Task] 开始异步处理: {task_id}")
        async with AsyncSessionLocal() as db:
            task_service = TaskService(db)
            try:
                # 首先更新状态为处理中
                print(f"[Celery Task] 更新状态为处理中: {task_id}")
                task = await task_service.get_task(task_id)
                if not task:
                    print(f"[Celery Task] 错误: 任务不存在 {task_id}")
                    return {"status": "failed", "error": "Task not found"}
                
                # 更新状态
                await task_service.task_repo.update_status(
                    task_id, 
                    'processing',
                    # started_at=asyncio.get_event_loop().time()
                    started_at=datetime.utcnow()  # 正确的datetime对象
                )
                await task_service.task_repo.update_progress(task_id, 10)
                
                # 实际处理逻辑
                print(f"[Celery Task] 调用process_task: {task_id}")
                await task_service.process_task(task_id)
                
                print(f"[Celery Task] 任务处理完成: {task_id}")
                return {"status": "completed", "task_id": task_id}
                
            except Exception as exc:
                print(f"[Celery Task] 任务处理失败: {task_id}, 错误: {exc}")
                # 记录错误
                await task_service.task_repo.update_status(
                    task_id, 
                    'failed',
                    error_message=str(exc)
                )
                raise self.retry(exc=exc, countdown=60)

    # 在Celery中运行异步函数
    return asyncio.run(_process())

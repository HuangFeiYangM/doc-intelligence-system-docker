"""
Celery background tasks.
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.config import get_settings
from app.services.task_service import TaskService
from app.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(bind=True, max_retries=3, name='process_document_task')
def process_document_task(self, task_id: str):
    """Process document in background using Celery.

    Args:
        task_id: Task ID to process
    """
    print(f"[Celery Task] 收到任务: {task_id}")

    async def _process():
        print(f"[Celery Task] 开始异步处理: {task_id}")

        # 在任务内部创建独立的引擎和会话，避免事件循环冲突
        engine = create_async_engine(
            settings.DATABASE_URL,
            poolclass=NullPool,  # Celery 任务使用 NullPool 避免连接池问题
            echo=settings.DEBUG,
        )
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        try:
            async with AsyncSessionLocal() as db:
                task_repo = TaskRepository(db)
                task_service = TaskService(db)

                try:
                    # 首先检查任务是否存在
                    print(f"[Celery Task] 查询任务: {task_id}")
                    task = await task_service.get_task(task_id)
                    if not task:
                        print(f"[Celery Task] 错误: 任务不存在 {task_id}")
                        return {"status": "failed", "error": "Task not found"}

                    # 更新状态为处理中
                    print(f"[Celery Task] 更新状态为处理中: {task_id}")
                    await task_repo.update_status(
                        task_id,
                        'processing',
                        started_at=datetime.utcnow()
                    )
                    await task_repo.update_progress(task_id, 10)
                    await db.commit()

                    # 实际处理逻辑
                    print(f"[Celery Task] 调用process_task: {task_id}")
                    await task_service.process_task(task_id)
                    await db.commit()

                    print(f"[Celery Task] 任务处理完成: {task_id}")
                    return {"status": "completed", "task_id": task_id}

                except Exception as exc:
                    await db.rollback()
                    print(f"[Celery Task] 任务处理失败: {task_id}, 错误: {exc}")
                    # 记录错误
                    try:
                        await task_repo.update_status(
                            task_id,
                            'failed',
                            error_message=str(exc)
                        )
                        await db.commit()
                    except Exception as e:
                        print(f"[Celery Task] 更新失败状态也出错: {e}")
                    raise self.retry(exc=exc, countdown=60)

        finally:
            # 确保引擎被正确关闭
            await engine.dispose()

    # 在Celery中运行异步函数
    return asyncio.run(_process())

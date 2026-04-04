"""
Celery application configuration.
"""
from celery import Celery
from app.config import get_settings

settings = get_settings()

# 创建Celery应用实例
celery_app = Celery(
    'doc_intelligence',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.core.tasks']  # 明确包含任务模块
)

# 配置Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3 * 60,  # 30分钟超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# 自动发现所有任务
celery_app.autodiscover_tasks(['app.core'])

print(f"[Celery] 应用已初始化，Broker: {settings.CELERY_BROKER_URL}")

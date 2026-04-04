"""
API v1 路由器初始化。
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.templates import router as templates_router
from app.api.v1.download import router as download_router

router = APIRouter(prefix="/v1")

# 包含所有子路由器
router.include_router(auth_router)
router.include_router(documents_router)
router.include_router(tasks_router)
router.include_router(templates_router)
router.include_router(download_router)

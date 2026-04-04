"""
FastAPI 应用程序主入口点。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api import router as api_router
from app.config import get_settings, ensure_directories
from app.database import init_db, close_db, get_db
from app.dependencies import create_default_admin
from app.middleware import setup_middleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期处理器。"""
    # 启动
    ensure_directories()
    await init_db()

    # 创建默认管理员用户
    async for db in get_db():
        await create_default_admin(db)
        break  # 只需要一个会话

    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    yield

    # 关闭
    await close_db()
    print("Application shutdown complete")


def create_application() -> FastAPI:
    """创建并配置 FastAPI 应用程序。

    Returns:
        配置好的 FastAPI 应用
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="文档智能系统 API - 使用大语言模型从文档中提取结构化数据",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "documents",
                "description": "文档上传与处理"
            },
            {
                "name": "authentication",
                "description": "用户认证与授权"
            },
            {
                "name": "tasks",
                "description": "任务管理"
            },
            {
                "name": "templates",
                "description": "模板管理"
            },
            {
                "name": "download",
                "description": "文件下载"
            }
        ]
    )

    # 设置中间件
    setup_middleware(app)

    # 包含 API 路由
    app.include_router(api_router)

    # 健康检查端点
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.APP_VERSION}

    # 根端点
    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.DEBUG else None
        }

    return app


# 创建应用程序实例
app = create_application()

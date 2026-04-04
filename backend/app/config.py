"""
Configuration management for the document intelligence system.
"""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator, FieldValidationInfo
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "文档智能系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Database
    DATABASE_URL: str = "mysql+asyncmy://user:password@localhost:3306/doc_intel"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # DeepSeek LLM API
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_MAX_TOKENS: int = 4096
    DEEPSEEK_TEMPERATURE: float = 0.7
    DEEPSEEK_TIMEOUT: int = 90

    # File Upload
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".doc", ".xlsx", ".xls"]

    # Paths (can be overridden by environment variables)
    # Note: These should be relative to the project root or absolute paths
    BASE_DIR: Path = Path(__file__).parent.parent.absolute()
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    TEMPLATE_DIR: Path = BASE_DIR / "templates"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    LOG_DIR: Path = BASE_DIR / "logs"

    # Task Processing
    MAX_CONCURRENT_TASKS: int = 5
    TASK_TIMEOUT: int = 300  # 5 minutes

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Default Admin User
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"  # Change in production!

    # Optional advanced configuration
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ALLOWED_ORIGINS: str = "*"
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        # Multiple possible .env file locations for flexibility
        # Priority: .env.backend > .env (backward compatibility)
        env_file = [
            # Primary: backend directory .env.backend files
            ".env.backend",                # Current directory (backend/app)
            "../.env.backend",             # Parent directory (backend)
            "/app/.env.backend",           # Docker container absolute path

        ]
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables not defined

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v):
        """Parse ALLOWED_EXTENSIONS from JSON string or comma-separated list."""
        if isinstance(v, str):
            # Try to parse as JSON first
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Try comma-separated list
            if "," in v:
                # Remove brackets and quotes if present
                cleaned = v.strip().strip("[]").replace('"', '').replace("'", "")
                return [ext.strip() for ext in cleaned.split(",") if ext.strip()]
            # Single extension
            return [v.strip()]
        return v

    @field_validator("UPLOAD_DIR", "TEMPLATE_DIR", "OUTPUT_DIR", "LOG_DIR", mode="before")
    @classmethod
    def validate_paths(cls, v, info: FieldValidationInfo):
        """Convert string paths to Path objects and resolve relative paths."""
        if isinstance(v, str):
            # If path is relative and starts with ./, resolve relative to BASE_DIR
            if v.startswith("./") or v.startswith("../"):
                # Get BASE_DIR from values if available
                values = info.data
                base_dir = values.get("BASE_DIR", Path(__file__).parent.parent.absolute())
                return (base_dir.parent / v).resolve()
            else:
                # Absolute path or relative without ./
                return Path(v).resolve()
        return v

    @field_validator("MAX_UPLOAD_SIZE", mode="before")
    @classmethod
    def parse_max_upload_size(cls, v):
        """Parse MAX_UPLOAD_SIZE from string with size suffixes."""
        if isinstance(v, str):
            v = v.strip().upper()
            if v.endswith("KB"):
                return int(v[:-2]) * 1024
            elif v.endswith("MB"):
                return int(v[:-2]) * 1024 * 1024
            elif v.endswith("GB"):
                return int(v[:-2]) * 1024 * 1024 * 1024
            else:
                try:
                    return int(v)
                except ValueError:
                    pass
        return v

    @field_validator("DEEPSEEK_API_KEY")
    @classmethod
    def validate_api_key(cls, v):
        """Warn if API key is empty (but allow for testing)."""
        if not v:
            import warnings
            warnings.warn(
                "DEEPSEEK_API_KEY is empty. LLM features will not work.",
                UserWarning
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Ensure directories exist
def ensure_directories():
    """Create necessary directories if they don't exist."""
    settings = get_settings()
    for directory in [settings.UPLOAD_DIR, settings.TEMPLATE_DIR,
                      settings.OUTPUT_DIR, settings.LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

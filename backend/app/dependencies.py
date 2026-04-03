"""
FastAPI dependencies.
"""
from fastapi import Depends
from fastapi.security import HTTPBearer

from app.api.v1.auth import get_current_user, verify_token, create_default_admin
from app.database import get_db

security = HTTPBearer()

# Re-export for backward compatibility
__all__ = ["security", "verify_token", "get_current_user", "create_default_admin"]

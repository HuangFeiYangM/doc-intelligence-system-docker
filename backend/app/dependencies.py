"""
FastAPI dependencies.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.database import get_db

settings = get_settings()
security = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Verify Bearer token (placeholder for auth implementation).

    Args:
        credentials: HTTP Authorization credentials

    Returns:
        User identifier

    Raises:
        HTTPException: If authentication fails
    """
    # Placeholder: Implement actual JWT or API key validation
    # For now, allow all requests in development
    return "anonymous"


async def get_current_user(token: str = Depends(verify_token)) -> dict:
    """Get current authenticated user.

    Args:
        token: Verified token

    Returns:
        User dictionary
    """
    return {"id": token, "name": "Anonymous User"}

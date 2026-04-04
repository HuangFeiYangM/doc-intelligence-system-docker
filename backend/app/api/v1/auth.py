"""
用户认证 API 端点。
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["authentication"])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码与哈希值是否匹配。"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希值。"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌。"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """根据用户名获取用户。"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """使用用户名和密码验证用户。"""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if user.is_active != "1":
        return None
    return user


async def create_default_admin(db: AsyncSession) -> None:
    """如果不存在用户，则创建默认管理员用户。"""
    # 检查是否存在任何用户
    result = await db.execute(select(User))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return

    # 创建默认管理员用户
    admin_user = User(
        id=str(uuid4()),
        username=settings.ADMIN_USERNAME,
        password_hash=get_password_hash(settings.ADMIN_PASSWORD),
        is_active="1"
    )
    db.add(admin_user)
    await db.commit()

    print(f"Default admin user created: {settings.ADMIN_USERNAME}")


@router.post("/login", response_model=TokenResponse, summary="用户登录", description="使用用户名和密码登录获取访问令牌")
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """使用用户名和密码登录获取访问令牌。

    Args:
        login_data: 登录凭据
        db: 数据库会话

    Returns:
        令牌响应，包含访问令牌

    Raises:
        HTTPException: 如果认证失败
    """
    user = await authenticate_user(db, login_data.username, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    await db.commit()

    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """从令牌中获取当前认证用户。

    Args:
        credentials: HTTP 认证凭据
        db: 数据库会话

    Returns:
        用户对象

    Raises:
        HTTPException: 如果认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")

        if username is None or user_id is None:
            raise credentials_exception

        # Check token expiration
        exp = payload.get("exp")
        if exp is None or datetime.utcnow().timestamp() > exp:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Get user from database
    user = await get_user_by_username(db, username)

    if user is None:
        raise credentials_exception

    if user.is_active != "1":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> str:
    """验证 Bearer 令牌并返回用户名。

    Args:
        credentials: HTTP 认证凭据
        db: 数据库会话

    Returns:
        用户名

    Raises:
        HTTPException: 如果认证失败
    """
    user = await get_current_user(credentials, db)
    return user.username

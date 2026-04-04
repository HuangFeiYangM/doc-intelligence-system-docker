"""
用于请求和响应验证的 Pydantic 模式。
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, UUID4

from app.models import TaskStatus, DocumentType


# 任务模式
class TaskBase(BaseModel):
    document_id: UUID4 = Field(..., description="文档ID")
    template_id: Optional[UUID4] = Field(None, description="模板ID")


class TaskCreate(TaskBase):
    pass


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4 = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., ge=0, le=100, description="任务进度 (0-100)")
    document_id: UUID4 = Field(..., description="文档ID")
    template_id: Optional[UUID4] = Field(None, description="模板ID")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")


class TaskStatusResponse(BaseModel):
    task_id: UUID4 = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., ge=0, le=100, description="任务进度 (0-100)")
    created_at: Optional[str] = Field(None, description="创建时间")
    started_at: Optional[str] = Field(None, description="开始时间")
    completed_at: Optional[str] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")


class TaskResultResponse(BaseModel):
    task_id: UUID4 = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    extracted_data: Optional[Dict[str, Any]] = Field(None, description="提取的数据")


# 文档模式
class DocumentBase(BaseModel):
    filename: str = Field(..., description="文件名")
    doc_type: DocumentType = Field(..., description="文档类型")


class DocumentCreate(DocumentBase):
    original_filename: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小（字节）")
    mime_type: str = Field(..., description="MIME 类型")


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    original_filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    doc_type: str = Field(..., description="文档类型")
    mime_type: str = Field(..., description="MIME 类型")
    created_at: Optional[datetime] = Field(None, description="创建时间")


# 模板模式
class TemplateBase(BaseModel):
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")


class TemplateCreate(TemplateBase):
    field_mapping: Dict[str, str] = Field(..., description="字段映射配置（字段名到单元格地址）")


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    field_mapping: Dict[str, str] = Field(..., description="字段映射配置")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class TemplateListResponse(BaseModel):
    templates: List[TemplateResponse] = Field(..., description="模板列表")


# 上传响应
class UploadResponse(BaseModel):
    document_id: str = Field(..., description="文档ID")
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="消息")


# 错误响应
class ErrorResponse(BaseModel):
    error: str = Field(..., description="错误类型")
    detail: Optional[str] = Field(None, description="错误详情")


# 认证模式
class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")

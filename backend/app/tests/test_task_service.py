"""
Tests for TaskService module.
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import Task, Document, Template, TaskStatus, DocumentType
from app.services.task_service import TaskService, TaskServiceError
from app.services.document_parser import DocumentParserError
from app.services.llm_service import LLMServiceError


class TestTaskService:
    """Test cases for TaskService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def task_service(self, mock_db):
        """Create a TaskService instance with mock DB."""
        return TaskService(mock_db)

    @pytest.mark.asyncio
    async def test_create_task(self, task_service, mock_db):
        """Test creating a new task."""
        doc_id = str(uuid.uuid4())
        template_id = str(uuid.uuid4())

        task = await task_service.create_task(doc_id, template_id)

        assert task.document_id == doc_id
        assert task.template_id == template_id
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_without_template(self, task_service, mock_db):
        """Test creating a task without template."""
        doc_id = str(uuid.uuid4())

        task = await task_service.create_task(doc_id, None)

        assert task.document_id == doc_id
        assert task.template_id is None
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_task_status_existing(self, task_service, mock_db):
        """Test getting status of existing task."""
        task_id = str(uuid.uuid4())

        # Create mock task
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.status = TaskStatus.PROCESSING
        mock_task.progress = 50
        mock_task.created_at = datetime.utcnow()
        mock_task.started_at = datetime.utcnow()
        mock_task.completed_at = None
        mock_task.error_message = None

        # Mock repository response
        with patch.object(task_service.task_repo, 'get_by_id', return_value=mock_task):
            status = await task_service.get_task_status(task_id)

        assert status["task_id"] == task_id
        assert status["status"] == "processing"
        assert status["progress"] == 50

    @pytest.mark.asyncio
    async def test_get_task_status_nonexistent(self, task_service):
        """Test getting status of non-existent task."""
        task_id = str(uuid.uuid4())

        with patch.object(task_service.task_repo, 'get_by_id', return_value=None):
            with pytest.raises(TaskServiceError) as exc_info:
                await task_service.get_task_status(task_id)

        assert "Task not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self, task_service):
        """Test cancelling a pending task."""
        task_id = str(uuid.uuid4())

        mock_task = MagicMock()
        mock_task.status = TaskStatus.PENDING

        with patch.object(task_service, 'get_task', return_value=mock_task):
            with patch.object(task_service.task_repo, 'update_status', return_value=True):
                result = await task_service.cancel_task(task_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_processing_task(self, task_service):
        """Test cancelling a processing task (should fail)."""
        task_id = str(uuid.uuid4())

        mock_task = MagicMock()
        mock_task.status = TaskStatus.PROCESSING

        with patch.object(task_service, 'get_task', return_value=mock_task):
            result = await task_service.cancel_task(task_id)

        assert result is False


class TestTaskServiceEdgeCases:
    """Edge case tests for TaskService."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def task_service(self, mock_db):
        service = TaskService(mock_db)
        # Properly mock async methods
        service.task_repo.update_status = AsyncMock(return_value=True)
        service.task_repo.update_progress = AsyncMock(return_value=True)
        return service

    @pytest.mark.asyncio
    async def test_process_task_nonexistent(self, task_service):
        """Test processing non-existent task."""
        task_id = str(uuid.uuid4())

        with patch.object(task_service, 'get_task', return_value=None):
            with pytest.raises(TaskServiceError) as exc_info:
                await task_service.process_task(task_id)

        assert "Task not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_task_document_parse_error(self, task_service):
        """Test processing task with document parse error."""
        task_id = str(uuid.uuid4())

        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.document = MagicMock()
        mock_task.document.file_path = "/invalid/file.pdf"
        mock_task.template_id = None

        with patch.object(task_service, 'get_task', return_value=mock_task):
            with patch.object(task_service.parser, 'extract_text', side_effect=DocumentParserError("Parse failed")):
                with pytest.raises(TaskServiceError) as exc_info:
                    await task_service.process_task(task_id)

        assert "Document parsing failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_tasks_with_filter(self, task_service):
        """Test listing tasks with status filter."""
        mock_tasks = [MagicMock(), MagicMock()]

        with patch.object(task_service.task_repo, 'list_tasks', return_value=mock_tasks):
            tasks = await task_service.list_tasks(status=TaskStatus.COMPLETED, limit=10)

        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_list_tasks_no_filter(self, task_service):
        """Test listing all tasks."""
        mock_tasks = []

        with patch.object(task_service.task_repo, 'list_tasks', return_value=mock_tasks):
            tasks = await task_service.list_tasks()

        assert tasks == []
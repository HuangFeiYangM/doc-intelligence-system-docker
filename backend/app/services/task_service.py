"""
Task service for managing document processing tasks.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import get_settings
from app.models import Task, TaskStatus, Document, Template, DocumentType
from app.repositories.task_repository import TaskRepository
from app.repositories.template_repository import TemplateRepository
from app.services.document_parser import DocumentParser, DocumentParserError
from app.services.llm_service import LLMService, LLMServiceError
from app.services.table_generator import TableGenerator, TableGeneratorError

settings = get_settings()


class TaskServiceError(Exception):
    """Exception raised for task service errors."""
    pass


class TaskService:
    """Service for managing document processing tasks."""

    def __init__(self, db: AsyncSession):
        """Initialize the task service.

        Args:
            db: Database session
        """
        self.db = db
        self.task_repo = TaskRepository(db)
        self.template_repo = TemplateRepository(db)
        self.parser = DocumentParser()
        self.llm_service = LLMService()
        self.table_generator = TableGenerator()

    async def create_task(
        self,
        document_id: str,
        template_id: Optional[str] = None
    ) -> Task:
        """Create a new processing task.

        Args:
            document_id: ID of the document to process
            template_id: Optional ID of the template to use

        Returns:
            Created task
        """
        task = Task(
            id=str(uuid.uuid4()),
            document_id=document_id,
            template_id=str(template_id) if template_id else None,
            status=TaskStatus.PENDING,
            progress=0
        )
        await self.task_repo.create(task)
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        return await self.task_repo.get_by_id(task_id)

    async def get_task_status(self, task_id: str) -> dict:
        """Get task status information.

        Args:
            task_id: Task ID

        Returns:
            Task status dictionary
        """
        task = await self.get_task(task_id)
        if not task:
            raise TaskServiceError(f"Task not found: {task_id}")

        return {
            "task_id": task.id,
            "status": task.status.value,
            "progress": task.progress,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
        }

    async def process_task(self, task_id: str) -> None:
        """Process a task (intended for background execution).

        Args:
            task_id: Task ID to process
        """
        task = await self.get_task(task_id)
        if not task:
            raise TaskServiceError(f"Task not found: {task_id}")

        try:
            # Update status to processing
            await self.task_repo.update_status(
                task_id,
                TaskStatus.PROCESSING,
                started_at=datetime.utcnow()
            )

            # Step 1: Parse document
            await self.task_repo.update_progress(task_id, 10)
            document = task.document
            text = await self._parse_document(document)

            # Step 2: Extract fields using LLM (as list for multiple records)
            await self.task_repo.update_progress(task_id, 40)
            template = None
            field_mapping = {}
            if task.template_id:
                template = await self.template_repo.get_by_id(task.template_id)
                if template and template.field_mapping:
                    field_mapping = template.field_mapping

            if not field_mapping:
                # Default fields if no template
                field_mapping = {
                    "名称": "A2",
                    "日期": "B2",
                    "金额": "C2",
                    "描述": "D2"
                }

            # Use extract_fields_list with field_mapping to guide LLM output
            extracted_data_list = await self.llm_service.extract_fields_list_with_mapping(text, field_mapping)

            # Step 3: Generate output file
            await self.task_repo.update_progress(task_id, 80)
            output_path = await self._generate_output_list(
                task_id,
                extracted_data_list,
                template
            )

            # Update task as completed
            await self.task_repo.update_status(
                task_id,
                TaskStatus.COMPLETED,
                progress=100,
                completed_at=datetime.utcnow(),
                extracted_data=extracted_data_list,
                output_file_path=str(output_path) if output_path else None
            )

        except Exception as e:
            # Update task as failed
            await self.task_repo.update_status(
                task_id,
                TaskStatus.FAILED,
                error_message=str(e)
            )
            raise TaskServiceError(f"Task processing failed: {str(e)}")

    async def _parse_document(self, document: Document) -> str:
        """Parse document and extract text.

        Args:
            document: Document model

        Returns:
            Extracted text
        """
        try:
            return self.parser.extract_text(document.file_path)
        except DocumentParserError as e:
            raise TaskServiceError(f"Document parsing failed: {str(e)}")

    async def _generate_output(
        self,
        task_id: str,
        data: dict,
        template: Optional[Template]
    ) -> Optional[Path]:
        """Generate output Excel file.

        Args:
            task_id: Task ID
            data: Extracted data
            template: Template model

        Returns:
            Path to generated file or None
        """
        try:
            output_path = settings.OUTPUT_DIR / f"{task_id}.xlsx"

            if template and template.file_path:
                # Use template
                field_mapping = template.field_mapping or {}
                self.table_generator.generate_from_template(
                    template.file_path,
                    data,
                    field_mapping,
                    output_path
                )
            else:
                # Create new file with headers from data keys
                TableGenerator.create_template(
                    output_path,
                    list(data.keys())
                )
                # Fill data
                generator = TableGenerator()
                generator.load_template(output_path)
                generator.fill_data(data)
                generator.save(output_path)

            return output_path
        except TableGeneratorError as e:
            raise TaskServiceError(f"Table generation failed: {str(e)}")

    async def _generate_output_list(
        self,
        task_id: str,
        data_list: list,
        template: Optional[Template]
    ) -> Optional[Path]:
        """Generate output Excel file for list of records.

        Args:
            task_id: Task ID
            data_list: List of extracted data records
            template: Template model

        Returns:
            Path to generated file or None
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            output_path = settings.OUTPUT_DIR / f"{task_id}.xlsx"

            # Debug logging
            logger.info(f"[_generate_output_list] Task {task_id}: {len(data_list)} records")
            logger.info(f"[_generate_output_list] Data list: {data_list}")
            logger.info(f"[_generate_output_list] Template: {template}")
            if template:
                logger.info(f"[_generate_output_list] Field mapping: {template.field_mapping}")

            if not data_list:
                # Empty list, create empty file with headers
                if template and template.field_mapping:
                    headers = list(template.field_mapping.keys())
                else:
                    headers = ["名称", "日期", "金额", "描述"]
                TableGenerator.create_template(output_path, headers)
                return output_path

            if template and template.file_path:
                # Use template with multiple rows
                field_mapping = template.field_mapping or {}
                self.table_generator.generate_from_template_list(
                    template.file_path,
                    data_list,
                    field_mapping,
                    output_path
                )
            else:
                # Create new file with headers from first record
                headers = list(data_list[0].keys())
                TableGenerator.create_template(output_path, headers)
                # Fill multiple rows of data
                generator = TableGenerator()
                generator.load_template(output_path)
                generator.fill_data_list(data_list)
                generator.save(output_path)

            return output_path
        except TableGeneratorError as e:
            raise TaskServiceError(f"Table generation failed: {str(e)}")

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """List tasks with optional filtering.

        Args:
            status: Filter by status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of tasks
        """
        return await self.task_repo.list_tasks(status, limit, offset)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled, False otherwise
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        if task.status == TaskStatus.PENDING:
            await self.task_repo.update_status(
                task_id,
                TaskStatus.FAILED,
                error_message="Task cancelled by user"
            )
            return True

        return False

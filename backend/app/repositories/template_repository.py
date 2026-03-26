"""
Template repository for database operations.
"""
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Template


class TemplateRepository:
    """Repository for Template model operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, template: Template) -> Template:
        """Create a new template."""
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def get_by_id(self, template_id: str) -> Optional[Template]:
        """Get template by ID."""
        result = await self.db.execute(
            select(Template).where(Template.id == template_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Template]:
        """List all templates."""
        result = await self.db.execute(
            select(Template)
            .order_by(Template.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def delete(self, template_id: str) -> bool:
        """Delete a template."""
        result = await self.db.execute(
            select(Template).where(Template.id == template_id)
        )
        template = result.scalar_one_or_none()

        if not template:
            return False

        await self.db.delete(template)
        await self.db.flush()
        return True

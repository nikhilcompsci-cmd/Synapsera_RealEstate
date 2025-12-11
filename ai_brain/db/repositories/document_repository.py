from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.models import Document
from typing import Sequence, Optional


class DocumentRepository:
    """Repository for Document database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        project_id: int,
        filename: str,
        file_path: str,
        file_size: int,
        content_hash: str,
        page_count: Optional[int] = None,
        extracted_text_length: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> Document:
        """
        Create a new document.
        NOTE: Does NOT commit - transaction handled by caller.
        """
        document = Document(
            project_id=project_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            content_hash=content_hash,
            page_count=page_count,
            extracted_text_length=extracted_text_length,
            metadata=metadata,
            status="pending"
        )
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document
    
    async def get_by_id(self, document_id: int) -> Optional[Document]:
        """Get a document by ID."""
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_content_hash(self, content_hash: str) -> Optional[Document]:
        """Get a document by content hash (for deduplication)."""
        result = await self.session.execute(
            select(Document).where(Document.content_hash == content_hash)
        )
        return result.scalar_one_or_none()
    
    async def get_by_project(self, project_id: int) -> Sequence[Document]:
        """Get all documents for a project."""
        result = await self.session.execute(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()
    
    async def update_status(
        self,
        document_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Document]:
        """
        Update document status.
        NOTE: Does NOT commit - transaction handled by caller.
        """
        document = await self.get_by_id(document_id)
        if document:
            document.status = status
            if error_message:
                document.error_message = error_message
            await self.session.flush()
            await self.session.refresh(document)
        return document
    
    async def count_by_project(self, project_id: int) -> int:
        """Count documents in a project."""
        result = await self.session.execute(
            select(func.count(Document.id))
            .where(Document.project_id == project_id)
        )
        return result.scalar_one()

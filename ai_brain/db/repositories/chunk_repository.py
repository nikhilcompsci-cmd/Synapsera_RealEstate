from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from db.models import Chunk
from typing import Sequence, Optional, List


class ChunkRepository:
    """Repository for Chunk database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_many(
        self,
        document_id: int,
        chunks_data: List[dict]
    ) -> Sequence[Chunk]:
        """
        Create multiple chunks for a document.
        NOTE: Does NOT commit - transaction handled by caller.
        
        chunks_data: List of dicts with keys: chunk_index, text, char_count, start_page, end_page
        """
        chunks = []
        for data in chunks_data:
            chunk = Chunk(
                document_id=document_id,
                chunk_index=data["chunk_index"],
                text=data["text"],
                char_count=data["char_count"],
                start_page=data.get("start_page"),
                end_page=data.get("end_page")
            )
            chunks.append(chunk)
            self.session.add(chunk)
        
        await self.session.flush()
        
        # Refresh all chunks to get IDs
        for chunk in chunks:
            await self.session.refresh(chunk)
        
        return chunks
    
    async def get_by_document(self, document_id: int) -> Sequence[Chunk]:
        """Get all chunks for a document, ordered by chunk_index."""
        stmt = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .options(joinedload(Chunk.embedding_metadata))
        )
        result = await self.session.execute(stmt)
        return result.unique().scalars().all()
    
    async def get_by_id(self, chunk_id: int) -> Optional[Chunk]:
        """Get a chunk by ID."""
        result = await self.session.execute(
            select(Chunk).where(Chunk.id == chunk_id)
        )
        return result.scalar_one_or_none()
    
    async def count_by_document(self, document_id: int) -> int:
        """Count chunks for a document."""
        result = await self.session.execute(
            select(func.count(Chunk.id))
            .where(Chunk.document_id == document_id)
        )
        return result.scalar_one()

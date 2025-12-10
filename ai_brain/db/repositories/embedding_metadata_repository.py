from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.models import EmbeddingMetadata, Chunk
from typing import Sequence, Optional, List


class EmbeddingMetadataRepository:
    """Repository for EmbeddingMetadata database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_many(
        self,
        embeddings_data: List[dict]
    ) -> Sequence[EmbeddingMetadata]:
        """
        Create multiple embedding metadata records.
        NOTE: Does NOT commit - transaction handled by caller.
        
        embeddings_data: List of dicts with keys: chunk_id, model_name, vector_dimension, faiss_index_id
        """
        embeddings = []
        for data in embeddings_data:
            embedding = EmbeddingMetadata(
                chunk_id=data["chunk_id"],
                model_name=data["model_name"],
                vector_dimension=data["vector_dimension"],
                faiss_index_id=data["faiss_index_id"]
            )
            embeddings.append(embedding)
            self.session.add(embedding)
        
        await self.session.flush()
        
        # Refresh all embeddings to get IDs
        for embedding in embeddings:
            await self.session.refresh(embedding)
        
        return embeddings
    
    async def get_by_chunk_id(self, chunk_id: int) -> Optional[EmbeddingMetadata]:
        """Get embedding metadata for a chunk."""
        result = await self.session.execute(
            select(EmbeddingMetadata).where(EmbeddingMetadata.chunk_id == chunk_id)
        )
        return result.scalar_one_or_none()
    
    async def count_by_project(self, project_id: int) -> int:
        """Count embeddings for all documents in a project."""
        result = await self.session.execute(
            select(func.count(EmbeddingMetadata.id))
            .select_from(EmbeddingMetadata)
            .join(Chunk, EmbeddingMetadata.chunk_id == Chunk.id)
            .join(Chunk.document)
            .where(Chunk.document.has(project_id=project_id))
        )
        return result.scalar_one()
    
    async def get_by_document(self, document_id: int) -> Sequence[EmbeddingMetadata]:
        """Get all embedding metadata for a document's chunks."""
        result = await self.session.execute(
            select(EmbeddingMetadata)
            .join(Chunk, EmbeddingMetadata.chunk_id == Chunk.id)
            .where(Chunk.document_id == document_id)
            .order_by(EmbeddingMetadata.faiss_index_id)
        )
        return result.scalars().all()

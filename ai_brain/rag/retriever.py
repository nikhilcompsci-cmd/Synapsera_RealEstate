"""
RAG Retriever - Handles query embedding and vector search
"""
import numpy as np
import asyncio
import logging
import faiss
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from db.models import Chunk
from services.faiss_service import FAISSService
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class Retriever:
    """Handles query embedding and retrieval of relevant chunks"""
    
    def __init__(self):
        self.faiss_service = FAISSService()
        self.embedding_service = EmbeddingService()  # Real embeddings for queries
        self.embedding_dimension = 384  # Same as Sprint 2
    
    def embed_query(self, text: str) -> np.ndarray:
        """
        Convert query text to embedding vector using real semantic model.
        Uses the same model as document ingestion for consistent similarity matching.
        
        Args:
            text: Query text to embed
            
        Returns:
            Normalized embedding vector of shape (embedding_dimension,)
        """
        return self.embedding_service.embed_text(text)
    
    async def search_faiss(
        self,
        project_id: int,
        query_vector: np.ndarray,
        top_k: int = 5
        ):
        """
        Async-safe FAISS search using a background thread.
        Prevents blocking the event loop and avoids greenlet errors.
        """

        index_path = Path("data") / "faiss_indexes" / f"project_{project_id}.faiss"
        mapping_path = Path("data") / "faiss_indexes" / f"project_{project_id}_mapping.npy"

        if not index_path.exists() or not mapping_path.exists():
            return []

        # THIS FUNCTION RUNS IN A SEPARATE THREAD
        def _faiss_work():
            # Load FAISS index + mapping
            index = faiss.read_index(str(index_path))
            chunk_id_mapping = np.load(str(mapping_path))

            # Run search
            vectors = query_vector.reshape(1, -1)
            scores, indices = index.search(vectors, top_k)

            results = []
            for idx, score in zip(indices[0], scores[0]):
                if idx != -1 and idx < len(chunk_id_mapping):
                    results.append((int(chunk_id_mapping[idx]), float(score)))

            return results

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _faiss_work)

    
    async def fetch_chunks(
        self,
        session: AsyncSession,
        chunk_ids: List[int]
    ) -> List[Chunk]:
        """
        Fetch chunk records from database.
        
        Args:
            session: AsyncSession from FastAPI dependency
            chunk_ids: List of chunk IDs to fetch
            
        Returns:
            List of Chunk ORM objects
        """
        if not chunk_ids:
            return []
        
        # Query chunks by IDs
        stmt = select(Chunk).where(Chunk.id.in_(chunk_ids))
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        
        # Preserve order from chunk_ids
        chunk_dict = {chunk.id: chunk for chunk in chunks}
        ordered_chunks = [chunk_dict[cid] for cid in chunk_ids if cid in chunk_dict]
        
        return ordered_chunks
    
    async def retrieve(
        self,
        session: AsyncSession,
        project_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Tuple[Chunk, float]]:
        """
        Complete retrieval pipeline: embed query, search, fetch chunks.
        
        Args:
            session: AsyncSession from FastAPI dependency
            project_id: Project ID to search within
            query: User's question
            top_k: Number of results to return
            
        Returns:
            List of (Chunk, score) tuples ordered by relevance
        """
        # Step 1: Embed the query
        query_vector = self.embed_query(query)
        
        # Step 2: Search FAISS index
        search_results = await self.search_faiss(project_id, query_vector, top_k)
        
        if not search_results:
            return []
        
        # Step 3: Fetch chunks from database
        chunk_ids = [chunk_id for chunk_id, _ in search_results]
        chunks = await self.fetch_chunks(session, chunk_ids)
        
        # Step 4: Combine chunks with scores
        chunk_dict = {chunk.id: chunk for chunk in chunks}
        results = [
            (chunk_dict[chunk_id], score)
            for chunk_id, score in search_results
            if chunk_id in chunk_dict
        ]
        
        return results

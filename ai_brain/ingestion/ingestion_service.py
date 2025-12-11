from pathlib import Path
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np
import logging

from db.repositories.project_repository import ProjectRepository
from db.repositories.document_repository import DocumentRepository
from db.repositories.chunk_repository import ChunkRepository
from db.repositories.embedding_metadata_repository import EmbeddingMetadataRepository
from ingestion.pdf_extractor import PDFExtractor
from ingestion.chunking import TextChunker
from services.embedding_service import StubEmbeddingService
from services.faiss_service import FAISSService

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Service for handling document ingestion pipeline.
    
    This service controls ALL transactions. Repositories do NOT commit/rollback.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        chunk_size: int = 1000,
        overlap: int = 200,
        use_stub_embeddings: bool = True
    ):
        """
        Initialize ingestion service.
        
        Args:
            session: Database session (transaction will be controlled here)
            chunk_size: Characters per chunk
            overlap: Overlap between chunks
            use_stub_embeddings: If True, use stub embeddings instead of real model
        """
        self.session = session
        self.project_repo = ProjectRepository(session)
        self.document_repo = DocumentRepository(session)
        self.chunk_repo = ChunkRepository(session)
        self.embedding_repo = EmbeddingMetadataRepository(session)
        
        self.pdf_extractor = PDFExtractor()
        self.text_chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        
        # Use stub embeddings by default (can switch to real later)
        self.embedding_service = StubEmbeddingService()
        self.faiss_service = FAISSService()
    
    async def ingest_document(
        self,
        project_id: int,
        file_path: Path,
        filename: str,
        validation_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Complete ingestion pipeline with async-safe transaction control.
        
        This method controls the transaction using async with session.begin().
        All repository methods are called within this transaction context.
        
        Args:
            project_id: ID of the project
            file_path: Path to uploaded PDF file
            filename: Original filename
        
        Returns:
            Dict with ingestion results
        """
        document_id = None
        
        logger.info(f"Starting document ingestion - Project: {project_id}, File: {filename}")
        
        try:
            # Start async transaction - THIS is where transaction control happens
            async with self.session.begin():
                # Step 1: Verify project exists
                logger.debug(f"Verifying project {project_id} exists")
                project = await self.project_repo.get_by_id(project_id)
                if not project:
                    logger.error(f"Project {project_id} not found")
                    raise ValueError(f"Project {project_id} not found")
                
                # Step 2: Extract text + metadata + content hash
                logger.info(f"Extracting text from PDF: {filename}")
                extraction = self.pdf_extractor.extract(file_path)
                
                if extraction["error"]:
                    logger.error(f"PDF extraction failed for {filename}: {extraction['error']}")
                    raise Exception(f"PDF extraction failed: {extraction['error']}")
                
                content_hash = extraction["content_hash"]
                full_text = extraction["text"]
                page_count = extraction["page_count"]
                
                logger.info(f"Extracted {len(full_text)} chars from {page_count} pages")
                
                # Step 3: Check for duplicate (by content hash)
                logger.debug(f"Checking for duplicate document (hash: {content_hash[:16]}...)")
                existing_doc = await self.document_repo.get_by_content_hash(content_hash)
                if existing_doc:
                    logger.warning(f"Duplicate document detected: {existing_doc.id}")
                    return {
                        "status": "duplicate",
                        "document_id": existing_doc.id,
                        "message": f"Document already exists (ID: {existing_doc.id})",
                        "chunks_created": 0,
                        "embeddings_created": 0
                    }
                
                # Step 4: Create Document record with status='processing'
                logger.info(f"Creating document record in database")
                
                # Merge validation metadata with extraction metadata
                doc_metadata = validation_metadata if validation_metadata else {}
                if extraction.get("extraction_metadata"):
                    doc_metadata["extraction"] = extraction["extraction_metadata"]
                doc_metadata["pdf_metadata"] = extraction.get("metadata", {})
                
                document = await self.document_repo.create(
                    project_id=project_id,
                    filename=filename,
                    file_path=str(file_path),
                    file_size=file_path.stat().st_size,
                    content_hash=content_hash,
                    page_count=page_count,
                    extracted_text_length=len(full_text),
                    metadata=doc_metadata
                )
                document_id = document.id
                logger.info(f"Document created with ID: {document_id}")
                
                await self.document_repo.update_status(document_id, "processing")
                
                # Step 5: Chunk text
                logger.info(f"Chunking text ({len(full_text)} characters)")
                chunks_data = self.text_chunker.chunk_text(full_text)
                
                if not chunks_data:
                    logger.error("No chunks generated from document")
                    raise Exception("No chunks generated from document")
                
                logger.info(f"Generated {len(chunks_data)} chunks")
                
                # Step 6: Create Chunk records
                logger.debug(f"Saving chunks to database")
                chunks = await self.chunk_repo.create_many(document_id, chunks_data)
                logger.info(f"Saved {len(chunks)} chunks to database")
                
                # Step 7: Generate embeddings
                logger.info(f"Generating embeddings for {len(chunks)} chunks")
                chunk_texts = [chunk.text for chunk in chunks]
                embeddings_array = self.embedding_service.embed_texts(chunk_texts)
                logger.info(f"Generated {len(embeddings_array)} embeddings (dimension: {embeddings_array.shape[1] if len(embeddings_array) > 0 else 0})")
                
                # Step 8: Get or create FAISS index for project
                logger.debug(f"Loading FAISS index for project {project_id}")
                vector_dim = self.embedding_service.vector_dimension
                faiss_index = self.faiss_service.get_or_create_index(
                    project_id=project_id,
                    dimension=vector_dim
                )
                
                # Step 9: Add embeddings to FAISS index
                faiss_ids = self.faiss_service.add_vectors(faiss_index, embeddings_array)
                
                # Step 10: Save FAISS index and chunk mapping
                self.faiss_service.save_index(faiss_index, project_id)
                
                # Save chunk ID mapping for retrieval
                chunk_ids = np.array([chunk.id for chunk in chunks], dtype=np.int64)
                self.faiss_service.save_chunk_mapping(project_id, chunk_ids)
                
                # Step 11: Create EmbeddingMetadata records
                embeddings_metadata = []
                for i, chunk in enumerate(chunks):
                    embeddings_metadata.append({
                        "chunk_id": chunk.id,
                        "model_name": self.embedding_service.model_name,
                        "vector_dimension": vector_dim,
                        "faiss_index_id": faiss_ids[i]
                    })
                
                await self.embedding_repo.create_many(embeddings_metadata)
                
                # Step 12: Update document status to 'completed'
                await self.document_repo.update_status(document_id, "completed")
                
                # Transaction commits here automatically when exiting async with block
            
            return {
                "status": "success",
                "document_id": document_id,
                "message": "Document ingested successfully",
                "chunks_created": len(chunks),
                "embeddings_created": len(embeddings_metadata),
                "page_count": page_count
            }
        
        except Exception as e:
            # If document was created, mark as failed
            if document_id:
                try:
                    async with self.session.begin():
                        await self.document_repo.update_status(
                            document_id,
                            "failed",
                            error_message=str(e)
                        )
                except Exception:
                    pass  # Best effort
            
            return {
                "status": "error",
                "document_id": document_id,
                "message": str(e),
                "chunks_created": 0,
                "embeddings_created": 0
            }
    
    async def get_ingestion_status(self, project_id: int) -> Dict:
        """
        Get ingestion status for all documents in a project.
        
        Args:
            project_id: Project ID
        
        Returns:
            Dict with status information
        """
        async with self.session.begin():
            documents = await self.document_repo.get_by_project(project_id)
            
            status_summary = {
                "total_documents": len(documents),
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "documents": []
            }
            
            for doc in documents:
                status_summary[doc.status] += 1
                
                chunk_count = await self.chunk_repo.count_by_document(doc.id)
                
                status_summary["documents"].append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "status": doc.status,
                    "page_count": doc.page_count,
                    "chunk_count": chunk_count,
                    "error_message": doc.error_message,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at
                })
            
            return status_summary

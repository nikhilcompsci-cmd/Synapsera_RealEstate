from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, func, Index, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Project(Base):
    """Project model - represents a real estate analysis project."""
    
    __tablename__ = "projects"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    failed_documents: Mapped[List["FailedDocument"]] = relationship(
        "FailedDocument",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}')>"


class Document(Base):
    """Document model - represents an uploaded PDF document."""
    
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # SHA256
    
    # Metadata
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extracted_text_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    validation_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Validation & extraction metadata
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending"
    )  # pending, processing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="documents")
    chunks: Mapped[List["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class Chunk(Base):
    """Chunk model - represents a text chunk from a document."""
    
    __tablename__ = "chunks"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-based index
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Metadata
    start_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    embedding_metadata: Mapped[Optional["EmbeddingMetadata"]] = relationship(
        "EmbeddingMetadata",
        back_populates="chunk",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_document_chunk", "document_id", "chunk_index"),
    )
    
    def __repr__(self) -> str:
        return f"<Chunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"


class EmbeddingMetadata(Base):
    """EmbeddingMetadata model - tracks embeddings for chunks."""
    
    __tablename__ = "embedding_metadata"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    
    # Embedding info
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    vector_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # FAISS metadata
    faiss_index_id: Mapped[int] = mapped_column(Integer, nullable=False)  # Position in FAISS index
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    chunk: Mapped["Chunk"] = relationship("Chunk", back_populates="embedding_metadata")
    
    __table_args__ = (
        Index("idx_chunk_embedding", "chunk_id"),
    )
    
    def __repr__(self) -> str:
        return f"<EmbeddingMetadata(id={self.id}, chunk_id={self.chunk_id}, model='{self.model_name}')>"

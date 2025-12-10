import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service.
        
        Args:
            model_name: HuggingFace model name for sentence-transformers
        """
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    @property
    def vector_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        # all-MiniLM-L6-v2 produces 384-dimensional vectors
        return self.model.get_sentence_embedding_dimension()
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            numpy array of shape (len(texts), vector_dimension)
        """
        if not texts:
            return np.array([])
        
        # Generate embeddings
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 10
        )
        
        return embeddings
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
        
        Returns:
            numpy array of shape (vector_dimension,)
        """
        embedding = self.model.encode(
            text,
            convert_to_numpy=True
        )
        
        return embedding


class StubEmbeddingService:
    """Stub embedding service for testing without loading models."""
    
    def __init__(self, model_name: str = "stub-model", vector_dim: int = 384):
        """
        Initialize stub embedding service.
        
        Args:
            model_name: Model name (for metadata only)
            vector_dim: Dimension of stub vectors
        """
        self.model_name = model_name
        self._vector_dim = vector_dim
    
    @property
    def vector_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        return self._vector_dim
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate stub embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            numpy array of shape (len(texts), vector_dimension) with random values
        """
        if not texts:
            return np.array([])
        
        # Generate random embeddings (normalized)
        embeddings = np.random.randn(len(texts), self._vector_dim).astype(np.float32)
        
        # Normalize to unit length (common for embeddings)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / (norms + 1e-8)
        
        return embeddings
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate stub embedding for a single text.
        
        Args:
            text: Text string to embed
        
        Returns:
            numpy array of shape (vector_dimension,) with random values
        """
        return self.embed_texts([text])[0]

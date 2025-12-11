import numpy as np
import faiss
from pathlib import Path
from typing import Optional, List, Tuple
import pickle


class FAISSService:
    """Service for managing FAISS vector indexes."""
    
    def __init__(self, index_directory: Path = Path("data/faiss_indexes")):
        """
        Initialize FAISS service.
        
        Args:
            index_directory: Directory to store FAISS index files
        """
        self.index_directory = index_directory
        self.index_directory.mkdir(parents=True, exist_ok=True)
    
    def create_index(self, dimension: int, use_gpu: bool = False) -> faiss.Index:
        """
        Create a new FAISS index.
        
        Args:
            dimension: Vector dimension
            use_gpu: Whether to use GPU (if available)
        
        Returns:
            FAISS index
        """
        # Use Inner Product for cosine similarity with normalized embeddings
        # IndexFlatIP is optimal for sentence-transformers normalized vectors
        index = faiss.IndexFlatIP(dimension)
        
        # Optionally move to GPU
        if use_gpu and faiss.get_num_gpus() > 0:
            index = faiss.index_cpu_to_gpu(faiss.StandardGpuResources(), 0, index)
        
        return index
    
    def add_vectors(
        self,
        index: faiss.Index,
        vectors: np.ndarray
    ) -> List[int]:
        """
        Add vectors to FAISS index.
        
        Args:
            index: FAISS index
            vectors: numpy array of shape (n, dimension)
        
        Returns:
            List of FAISS index IDs (0-based positions)
        """
        if vectors.shape[0] == 0:
            return []
        
        # Ensure vectors are float32 (FAISS requirement)
        vectors = vectors.astype(np.float32)
        
        # Get starting index ID
        start_id = index.ntotal
        
        # Add to index
        index.add(vectors)
        
        # Return list of IDs
        return list(range(start_id, index.ntotal))
    
    def search(
        self,
        index: faiss.Index,
        query_vector: np.ndarray,
        k: int = 5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for nearest neighbors.
        
        Args:
            index: FAISS index
            query_vector: Query vector of shape (dimension,) or (1, dimension)
            k: Number of nearest neighbors to return
        
        Returns:
            Tuple of (distances, indices) arrays
        """
        # Ensure query is 2D
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # Ensure float32
        query_vector = query_vector.astype(np.float32)
        
        # Search
        distances, indices = index.search(query_vector, k)
        
        return distances[0], indices[0]
    
    def save_index(self, index: faiss.Index, project_id: int) -> Path:
        """
        Save FAISS index to disk.
        
        Args:
            index: FAISS index to save
            project_id: Project ID
        
        Returns:
            Path to saved index file
        """
        # Move index to CPU if it's on GPU
        if hasattr(index, 'index'):
            index = faiss.index_gpu_to_cpu(index)
        
        index_path = self.index_directory / f"project_{project_id}.faiss"
        faiss.write_index(index, str(index_path))
        
        return index_path
    
    def load_index(self, project_id: int) -> Optional[faiss.Index]:
        """
        Load FAISS index from disk.
        
        Args:
            project_id: Project ID
        
        Returns:
            FAISS index or None if not found
        """
        index_path = self.index_directory / f"project_{project_id}.faiss"
        
        if not index_path.exists():
            return None
        
        index = faiss.read_index(str(index_path))
        return index
    
    def get_or_create_index(
        self,
        project_id: int,
        dimension: int
    ) -> faiss.Index:
        """
        Get existing index or create new one.
        
        Args:
            project_id: Project ID
            dimension: Vector dimension
        
        Returns:
            FAISS index
        """
        index = self.load_index(project_id)
        
        if index is None:
            index = self.create_index(dimension)
        
        return index
    
    def save_chunk_mapping(self, project_id: int, chunk_ids: np.ndarray) -> Path:
        """
        Save chunk ID mapping for FAISS index.
        
        Args:
            project_id: Project ID
            chunk_ids: Array of chunk IDs corresponding to FAISS index positions
        
        Returns:
            Path to saved mapping file
        """
        mapping_path = self.index_directory / f"project_{project_id}_mapping.npy"
        np.save(str(mapping_path), chunk_ids)
        return mapping_path
    
    def load_chunk_mapping(self, project_id: int) -> Optional[np.ndarray]:
        """
        Load chunk ID mapping for FAISS index.
        
        Args:
            project_id: Project ID
        
        Returns:
            Array of chunk IDs or None if not found
        """
        mapping_path = self.index_directory / f"project_{project_id}_mapping.npy"
        
        if not mapping_path.exists():
            return None
        
        return np.load(str(mapping_path))
    
    def delete_index(self, project_id: int) -> bool:
        """
        Delete FAISS index file and mapping.
        
        Args:
            project_id: Project ID
        
        Returns:
            True if deleted, False if not found
        """
        index_path = self.index_directory / f"project_{project_id}.faiss"
        mapping_path = self.index_directory / f"project_{project_id}_mapping.npy"
        
        deleted = False
        if index_path.exists():
            index_path.unlink()
            deleted = True
        
        if mapping_path.exists():
            mapping_path.unlink()
            deleted = True
        
        return deleted
    
    def get_index_stats(self, project_id: int) -> dict:
        """
        Get statistics about an index.
        
        Args:
            project_id: Project ID
        
        Returns:
            Dict with stats (ntotal, dimension, etc.)
        """
        index = self.load_index(project_id)
        
        if index is None:
            return {
                "exists": False,
                "ntotal": 0,
                "dimension": 0
            }
        
        return {
            "exists": True,
            "ntotal": index.ntotal,
            "dimension": index.d,
            "is_trained": index.is_trained
        }

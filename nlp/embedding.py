"""
Embedding and vector similarity utilities
"""

from typing import List, Optional, Tuple
import numpy as np
import logging
from pathlib import Path


class EmbeddingManager:
    """Manage text embeddings and similarity search"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 device: str = "cpu"):
        """
        Initialize embedding manager
        
        Args:
            model_name: Name of the sentence transformer model
            device: Device to use (cpu or cuda)
        """
        self.model_name = model_name
        self.device = device
        self.logger = logging.getLogger("nlp.EmbeddingManager")
        
        self.model = None
        self.index = None
        self.texts = []
        
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            
            self.logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.logger.info("Model loaded successfully")
            
        except ImportError:
            self.logger.error("sentence-transformers not installed")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise
    
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Encode texts to embeddings
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            
        Returns:
            Array of embeddings (n_texts, embedding_dim)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True
        )
        
        return embeddings
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        embeddings = self.encode([text1, text2])
        
        # Cosine similarity
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        
        return float(similarity)
    
    def build_index(self, texts: List[str], index_type: str = "flat"):
        """
        Build FAISS index for similarity search
        
        Args:
            texts: List of texts to index
            index_type: Type of index (flat, ivf, hnsw)
        """
        try:
            import faiss
            
            self.logger.info(f"Building FAISS index for {len(texts)} texts")
            self.texts = texts
            
            # Encode texts
            embeddings = self.encode(texts)
            
            # Create index
            dimension = embeddings.shape[1]
            
            if index_type == "flat":
                self.index = faiss.IndexFlatL2(dimension)
            elif index_type == "ivf":
                nlist = min(100, len(texts) // 10)  # number of clusters
                quantizer = faiss.IndexFlatL2(dimension)
                self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
                self.index.train(embeddings)
            else:
                self.index = faiss.IndexFlatL2(dimension)
            
            # Add vectors to index
            self.index.add(embeddings.astype('float32'))
            
            self.logger.info(f"Index built with {self.index.ntotal} vectors")
            
        except ImportError:
            self.logger.error("faiss not installed")
            raise
    
    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        """
        Search for similar texts
        
        Args:
            query: Query text
            k: Number of results to return
            
        Returns:
            List of (text, distance) tuples
        """
        if self.index is None:
            raise RuntimeError("Index not built. Call build_index() first")
        
        # Encode query
        query_embedding = self.encode([query])
        
        # Search
        distances, indices = self.index.search(
            query_embedding.astype('float32'), k
        )
        
        # Get results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(self.texts):
                results.append((self.texts[idx], float(dist)))
        
        return results
    
    def save_index(self, index_path: str):
        """Save FAISS index to disk"""
        if self.index is None:
            raise RuntimeError("No index to save")
        
        try:
            import faiss
            import pickle
            
            index_path = Path(index_path)
            index_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, str(index_path / "index.faiss"))
            
            # Save texts
            with open(index_path / "texts.pkl", 'wb') as f:
                pickle.dump(self.texts, f)
            
            self.logger.info(f"Index saved to {index_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save index: {e}")
            raise
    
    def load_index(self, index_path: str):
        """Load FAISS index from disk"""
        try:
            import faiss
            import pickle
            
            index_path = Path(index_path)
            
            # Load FAISS index
            self.index = faiss.read_index(str(index_path / "index.faiss"))
            
            # Load texts
            with open(index_path / "texts.pkl", 'rb') as f:
                self.texts = pickle.load(f)
            
            self.logger.info(f"Index loaded from {index_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load index: {e}")
            raise


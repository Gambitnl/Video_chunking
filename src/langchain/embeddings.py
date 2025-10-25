"""
Embedding service for generating text embeddings.
"""
from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger("DDSessionProcessor.embeddings")


class EmbeddingService:
    """Generate embeddings for text using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformer model to use
                       Options:
                       - 'all-MiniLM-L6-v2' (384 dim, fast, good quality) - DEFAULT
                       - 'all-mpnet-base-v2' (768 dim, slower, better quality)
        """
        self.model_name = model_name

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            logger.info(f"Successfully loaded {model_name}")

        except ImportError as e:
            logger.error(f"sentence-transformers not installed: {e}")
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            ) from e

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector as list of floats
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()

        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            raise

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Batch size for encoding (default: 32)

        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,
                convert_to_numpy=True
            )
            return embeddings.tolist()

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}", exc_info=True)
            raise

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        return self.model.get_sentence_embedding_dimension()

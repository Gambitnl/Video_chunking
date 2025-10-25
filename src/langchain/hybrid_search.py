"""
Hybrid search combining keyword and semantic search.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Tuple

logger = logging.getLogger("DDSessionProcessor.hybrid_search")


class HybridSearcher:
    """Combine keyword and semantic search for optimal results."""

    def __init__(self, vector_store, keyword_retriever):
        """
        Initialize hybrid searcher.

        Args:
            vector_store: CampaignVectorStore for semantic search
            keyword_retriever: CampaignRetriever for keyword search
        """
        self.vector_store = vector_store
        self.keyword_retriever = keyword_retriever

    def search(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.7
    ) -> List[Dict]:
        """
        Hybrid search with weighted ranking.

        Args:
            query: Search query
            top_k: Number of results to return
            semantic_weight: Weight for semantic results (0-1)
                           keyword_weight = 1 - semantic_weight

        Returns:
            List of search results
        """
        try:
            # Get semantic results
            semantic_results = self.vector_store.search(query, top_k=top_k * 2)

            # Get keyword results
            keyword_results_docs = self.keyword_retriever.retrieve(query, top_k=top_k * 2)

            # Convert keyword results to dict format
            keyword_results = [
                {
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "distance": 0.5  # Placeholder distance for keyword results
                }
                for doc in keyword_results_docs
            ]

            # Merge and re-rank using Reciprocal Rank Fusion
            merged = self._reciprocal_rank_fusion(
                semantic_results,
                keyword_results,
                weights=(semantic_weight, 1 - semantic_weight)
            )

            return merged[:top_k]

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}", exc_info=True)
            # Fallback to semantic search only
            return self.vector_store.search(query, top_k=top_k)

    def _reciprocal_rank_fusion(
        self,
        results_a: List[Dict],
        results_b: List[Dict],
        weights: Tuple[float, float] = (0.5, 0.5),
        k: int = 60
    ) -> List[Dict]:
        """
        Merge results using Reciprocal Rank Fusion (RRF) algorithm.

        Args:
            results_a: First list of results (semantic)
            results_b: Second list of results (keyword)
            weights: Tuple of (weight_a, weight_b)
            k: RRF constant (default: 60)

        Returns:
            Merged and ranked results
        """
        # Create a dict to accumulate scores for each unique document
        doc_scores = {}
        doc_info = {}

        # Process first result set
        for rank, result in enumerate(results_a, start=1):
            doc_id = self._get_doc_id(result)
            score = weights[0] / (k + rank)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0
                doc_info[doc_id] = result

            doc_scores[doc_id] += score

        # Process second result set
        for rank, result in enumerate(results_b, start=1):
            doc_id = self._get_doc_id(result)
            score = weights[1] / (k + rank)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0
                doc_info[doc_id] = result

            doc_scores[doc_id] += score

        # Sort by combined score
        ranked_doc_ids = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)

        # Return documents in ranked order
        return [doc_info[doc_id] for doc_id in ranked_doc_ids]

    def _get_doc_id(self, result: Dict) -> str:
        """Generate a unique ID for a document based on its content and metadata."""
        # Use a combination of text and key metadata fields
        text = result.get("text", "")[:100]  # First 100 chars
        metadata = result.get("metadata", {})

        # Try to create a unique ID
        session_id = metadata.get("session_id", "")
        speaker = metadata.get("speaker", "")
        start = metadata.get("start", "")

        if session_id and start:
            return f"{session_id}_{start}"
        else:
            # Fallback to text hash
            return str(hash(text))

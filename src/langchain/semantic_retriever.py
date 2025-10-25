"""
Semantic retriever using vector store for campaign data.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from src.langchain.retriever import Document

logger = logging.getLogger("DDSessionProcessor.semantic_retriever")


class SemanticCampaignRetriever:
    """Retrieve campaign data using semantic search."""

    def __init__(self, vector_store):
        """
        Initialize the semantic retriever.

        Args:
            vector_store: CampaignVectorStore instance
        """
        self.vector_store = vector_store

        logger.info("Initialized SemanticCampaignRetriever")

    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """
        Retrieve top-k relevant documents using semantic search.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of Document objects
        """
        try:
            results = self.vector_store.search(query, top_k=top_k)

            return [
                Document(
                    content=result["text"],
                    metadata=result["metadata"]
                )
                for result in results
            ]

        except Exception as e:
            logger.error(f"Error during semantic retrieval: {e}", exc_info=True)
            return []

    def retrieve_from_session(self, query: str, session_id: str, top_k: int = 5) -> List[Document]:
        """
        Retrieve documents from a specific session.

        Args:
            query: Search query
            session_id: Session to search within
            top_k: Number of results to return

        Returns:
            List of Document objects
        """
        try:
            # Search only transcripts
            all_results = self.vector_store.search(
                query,
                top_k=top_k * 3,  # Get more to filter
                collection="transcripts"
            )

            # Filter by session_id
            session_results = [
                r for r in all_results
                if r["metadata"].get("session_id") == session_id
            ]

            return [
                Document(
                    content=result["text"],
                    metadata=result["metadata"]
                )
                for result in session_results[:top_k]
            ]

        except Exception as e:
            logger.error(f"Error retrieving from session {session_id}: {e}", exc_info=True)
            return []

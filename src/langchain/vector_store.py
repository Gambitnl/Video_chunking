"""
Vector database for semantic search using ChromaDB.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger("DDSessionProcessor.vector_store")

# Batch size for embedding generation to prevent OOM
EMBEDDING_BATCH_SIZE = 100


class CampaignVectorStore:
    """Vector database for semantic search of campaign data."""

    def __init__(self, persist_dir: Path, embedding_service):
        """
        Initialize the vector store.

        Args:
            persist_dir: Directory to persist the vector database
            embedding_service: EmbeddingService instance for generating embeddings
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.embedding = embedding_service

        try:
            import chromadb
            from chromadb.config import Settings

            logger.info(f"Initializing ChromaDB at {persist_dir}")

            self.client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )

            # Collections for different data types
            self.transcript_collection = self.client.get_or_create_collection(
                name="transcripts",
                metadata={"description": "Session transcripts"}
            )

            self.knowledge_collection = self.client.get_or_create_collection(
                name="knowledge",
                metadata={"description": "NPCs, quests, locations"}
            )

            logger.info("ChromaDB initialized successfully")

        except ImportError as e:
            logger.error(f"chromadb not installed: {e}")
            raise RuntimeError(
                "chromadb not installed. Run: pip install chromadb"
            ) from e

    def add_transcript_segments(
        self,
        session_id: str,
        segments: List[Dict]
    ):
        """
        Add transcript segments to vector store.

        Args:
            session_id: Session identifier
            segments: List of segment dicts with keys: text, speaker, start, end
        """
        if not segments:
            logger.warning(f"No segments to add for session {session_id}")
            return

        try:
            total_segments = len(segments)
            logger.info(f"Adding {total_segments} segments from session {session_id}")

            # Process in batches to prevent OOM on large datasets
            for batch_start in range(0, total_segments, EMBEDDING_BATCH_SIZE):
                batch_end = min(batch_start + EMBEDDING_BATCH_SIZE, total_segments)
                batch_segments = segments[batch_start:batch_end]

                texts = [seg["text"] for seg in batch_segments]
                embeddings = self.embedding.embed_batch(texts, batch_size=32)
                ids = [f"{session_id}_seg_{batch_start + i}" for i in range(len(batch_segments))]

                metadatas = [
                    {
                        "session_id": session_id,
                        "speaker": seg.get("speaker", "Unknown"),
                        "start": float(seg.get("start", 0)),
                        "end": float(seg.get("end", 0)),
                        "type": "transcript"
                    }
                    for seg in batch_segments
                ]

                self.transcript_collection.add(
                    documents=texts,
                    embeddings=embeddings,
                    ids=ids,
                    metadatas=metadatas
                )

                logger.debug(f"Added batch {batch_start}-{batch_end} ({len(batch_segments)} segments)")

            logger.info(f"Successfully added all {total_segments} segments from session {session_id}")

        except Exception as e:
            logger.error(f"Error adding transcript segments: {e}", exc_info=True)
            raise

    def add_knowledge_documents(self, documents: List[Dict]):
        """
        Add knowledge base documents to vector store.

        Args:
            documents: List of document dicts with keys: text, metadata
        """
        if not documents:
            logger.warning("No knowledge documents to add")
            return

        try:
            total_docs = len(documents)
            logger.info(f"Adding {total_docs} knowledge documents")

            # Process in batches to prevent OOM on large datasets
            for batch_start in range(0, total_docs, EMBEDDING_BATCH_SIZE):
                batch_end = min(batch_start + EMBEDDING_BATCH_SIZE, total_docs)
                batch_docs = documents[batch_start:batch_end]

                texts = [doc["text"] for doc in batch_docs]
                embeddings = self.embedding.embed_batch(texts, batch_size=32)

                # Generate IDs based on document type and name
                ids = []
                metadatas = []
                for i, doc in enumerate(batch_docs):
                    metadata = doc.get("metadata", {})
                    doc_type = metadata.get("type", "unknown")
                    name = metadata.get("name", f"doc_{batch_start + i}")

                    # Sanitize name for ID
                    safe_name = name.replace(" ", "_").replace("/", "_")
                    ids.append(f"{doc_type}_{safe_name}_{batch_start + i}")
                    metadatas.append(metadata)

                self.knowledge_collection.add(
                    documents=texts,
                    embeddings=embeddings,
                    ids=ids,
                    metadatas=metadatas
                )

                logger.debug(f"Added batch {batch_start}-{batch_end} ({len(batch_docs)} documents)")

            logger.info(f"Successfully added all {total_docs} knowledge documents")

        except Exception as e:
            logger.error(f"Error adding knowledge documents: {e}", exc_info=True)
            raise

    def search(
        self,
        query: str,
        top_k: int = 5,
        collection: Optional[str] = None
    ) -> List[Dict]:
        """
        Semantic search across collections.

        Args:
            query: Search query
            top_k: Number of results to return
            collection: Specific collection to search ('transcripts' or 'knowledge'),
                       or None to search both

        Returns:
            List of result dicts with keys: text, metadata, distance
        """
        try:
            query_embedding = self.embedding.embed(query)

            results = []

            # Search transcripts
            if collection is None or collection == "transcripts":
                try:
                    transcript_results = self.transcript_collection.query(
                        query_embeddings=[query_embedding],
                        n_results=top_k
                    )
                    results.extend(self._format_results(transcript_results))
                except Exception as e:
                    logger.warning(f"Error searching transcripts: {e}")

            # Search knowledge base
            if collection is None or collection == "knowledge":
                try:
                    knowledge_results = self.knowledge_collection.query(
                        query_embeddings=[query_embedding],
                        n_results=top_k
                    )
                    results.extend(self._format_results(knowledge_results))
                except Exception as e:
                    logger.warning(f"Error searching knowledge base: {e}")

            # Sort by distance and take top_k
            results.sort(key=lambda x: x["distance"])
            return results[:top_k]

        except Exception as e:
            logger.error(f"Error during semantic search: {e}", exc_info=True)
            return []

    def _format_results(self, raw_results: Dict) -> List[Dict]:
        """Format raw ChromaDB results into consistent format."""
        if not raw_results or not raw_results.get("documents"):
            return []

        formatted = []

        documents = raw_results["documents"][0] if raw_results["documents"] else []
        metadatas = raw_results["metadatas"][0] if raw_results["metadatas"] else []
        distances = raw_results["distances"][0] if raw_results["distances"] else []

        for doc, meta, dist in zip(documents, metadatas, distances):
            formatted.append({
                "text": doc,
                "metadata": meta or {},
                "distance": dist
            })

        return formatted

    def delete_session(self, session_id: str):
        """Delete all segments for a session."""
        try:
            # Query to get all IDs for this session
            results = self.transcript_collection.get(
                where={"session_id": session_id}
            )

            if results and results.get("ids"):
                self.transcript_collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} segments for session {session_id}")
            else:
                logger.warning(f"No segments found for session {session_id}")

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
            raise

    def clear_all(self):
        """Clear all collections (WARNING: destructive operation)."""
        try:
            # Delete and recreate collections
            self.client.delete_collection("transcripts")
            self.client.delete_collection("knowledge")

            self.transcript_collection = self.client.create_collection(
                name="transcripts",
                metadata={"description": "Session transcripts"}
            )

            self.knowledge_collection = self.client.create_collection(
                name="knowledge",
                metadata={"description": "NPCs, quests, locations"}
            )

            logger.info("Cleared all vector store collections")

        except Exception as e:
            logger.error(f"Error clearing collections: {e}", exc_info=True)
            raise

    def get_stats(self) -> Dict:
        """Get statistics about the vector store."""
        try:
            transcript_count = self.transcript_collection.count()
            knowledge_count = self.knowledge_collection.count()

            return {
                "transcript_segments": transcript_count,
                "knowledge_documents": knowledge_count,
                "total_documents": transcript_count + knowledge_count,
                "persist_dir": str(self.persist_dir)
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {
                "transcript_segments": 0,
                "knowledge_documents": 0,
                "total_documents": 0,
                "persist_dir": str(self.persist_dir)
            }

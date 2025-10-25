"""
Knowledge base retriever for campaign data.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger("DDSessionProcessor.retriever")


class Document:
    """Simple document class for retrieval results."""

    def __init__(self, content: str, metadata: Dict = None):
        self.page_content = content
        self.metadata = metadata or {}

    def __str__(self):
        return self.page_content

    def __repr__(self):
        return f"Document(content={self.page_content[:50]}..., metadata={self.metadata})"


class CampaignRetriever:
    """Retrieve relevant campaign data for conversational queries."""

    def __init__(self, knowledge_base_dir: Path, transcript_dir: Path):
        """
        Initialize the retriever.

        Args:
            knowledge_base_dir: Directory containing knowledge base JSON files
            transcript_dir: Directory containing session transcripts
        """
        self.kb_dir = Path(knowledge_base_dir)
        self.transcript_dir = Path(transcript_dir)

        logger.info(
            f"Initialized CampaignRetriever with KB dir: {self.kb_dir}, "
            f"Transcript dir: {self.transcript_dir}"
        )

    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """
        Retrieve top-k relevant documents for query.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of Document objects
        """
        try:
            # Search knowledge bases (NPCs, quests, locations)
            kb_results = self._search_knowledge_bases(query, top_k=3)

            # Search session transcripts
            transcript_results = self._search_transcripts(query, top_k=2)

            # Combine and rank by relevance
            all_results = kb_results + transcript_results

            # Sort by relevance score (simple keyword matching for now)
            ranked_results = self._rank_results(all_results, query)

            return ranked_results[:top_k]

        except Exception as e:
            logger.error(f"Error during retrieval: {e}", exc_info=True)
            return []

    def _search_knowledge_bases(self, query: str, top_k: int) -> List[Document]:
        """Search structured knowledge bases."""
        results = []
        query_lower = query.lower()

        try:
            # Load all knowledge bases
            if not self.kb_dir.exists():
                logger.warning(f"Knowledge base directory not found: {self.kb_dir}")
                return results

            for kb_file in self.kb_dir.glob("*_knowledge.json"):
                try:
                    kb = self._load_knowledge_base(kb_file)

                    # Search NPCs
                    for npc in kb.get("npcs", []):
                        if self._matches_query(
                            query_lower,
                            npc.get("name", "").lower(),
                            npc.get("description", "").lower()
                        ):
                            results.append(Document(
                                content=f"NPC: {npc['name']} - {npc.get('description', 'No description')}",
                                metadata={
                                    "type": "npc",
                                    "source": kb_file.name,
                                    "name": npc["name"]
                                }
                            ))

                    # Search quests
                    for quest in kb.get("quests", []):
                        if self._matches_query(
                            query_lower,
                            quest.get("name", "").lower(),
                            quest.get("description", "").lower()
                        ):
                            results.append(Document(
                                content=f"Quest: {quest['name']} - {quest.get('description', 'No description')}",
                                metadata={
                                    "type": "quest",
                                    "source": kb_file.name,
                                    "name": quest["name"]
                                }
                            ))

                    # Search locations
                    for location in kb.get("locations", []):
                        if self._matches_query(
                            query_lower,
                            location.get("name", "").lower(),
                            location.get("description", "").lower()
                        ):
                            results.append(Document(
                                content=f"Location: {location['name']} - {location.get('description', 'No description')}",
                                metadata={
                                    "type": "location",
                                    "source": kb_file.name,
                                    "name": location["name"]
                                }
                            ))

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Error loading knowledge base {kb_file}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error searching knowledge bases: {e}", exc_info=True)

        return results[:top_k]

    def _search_transcripts(self, query: str, top_k: int) -> List[Document]:
        """Search session transcripts using simple keyword matching."""
        results = []
        query_lower = query.lower()

        try:
            if not self.transcript_dir.exists():
                logger.warning(f"Transcript directory not found: {self.transcript_dir}")
                return results

            # Search through session directories
            for session_dir in self.transcript_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                # Look for diarized transcript
                transcript_file = session_dir / "diarized_transcript.json"
                if not transcript_file.exists():
                    continue

                try:
                    with open(transcript_file, "r", encoding="utf-8") as f:
                        transcript_data = json.load(f)

                    segments = transcript_data.get("segments", [])

                    # Search through segments
                    for segment in segments:
                        text = segment.get("text", "")
                        if query_lower in text.lower():
                            speaker = segment.get("speaker", "Unknown")
                            start = segment.get("start", 0)
                            end = segment.get("end", 0)

                            # Format timestamp as HH:MM:SS
                            timestamp = self._format_timestamp(start)

                            results.append(Document(
                                content=f'[{speaker}, {timestamp}]: "{text}"',
                                metadata={
                                    "type": "transcript",
                                    "session_id": session_dir.name,
                                    "speaker": speaker,
                                    "start": start,
                                    "end": end,
                                    "timestamp": timestamp
                                }
                            ))

                            # Limit results per session
                            if len(results) >= top_k * 3:
                                break

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Error loading transcript {transcript_file}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error searching transcripts: {e}", exc_info=True)

        return results[:top_k]

    def _load_knowledge_base(self, kb_file: Path) -> Dict:
        """Load a knowledge base JSON file."""
        with open(kb_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _matches_query(self, query: str, *fields: str) -> bool:
        """Check if query matches any of the fields."""
        query_words = query.split()
        return any(
            all(word in field for word in query_words)
            for field in fields
        )

    def _rank_results(self, results: List[Document], query: str) -> List[Document]:
        """Rank results by relevance to query (simple keyword matching)."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        def relevance_score(doc: Document) -> int:
            content_lower = doc.page_content.lower()
            # Count query words in content
            matches = sum(1 for word in query_words if word in content_lower)
            # Boost NPCs and quests slightly
            boost = 1 if doc.metadata.get("type") in ["npc", "quest"] else 0
            return matches + boost

        # Sort by relevance score descending
        return sorted(results, key=relevance_score, reverse=True)

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

"""
Data ingestion pipeline for vector store.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger("DDSessionProcessor.data_ingestion")


class DataIngestor:
    """Ingest campaign data into vector store."""

    def __init__(self, vector_store):
        """
        Initialize the data ingestor.

        Args:
            vector_store: CampaignVectorStore instance
        """
        self.vector_store = vector_store

    def ingest_session(self, session_dir: Path) -> Dict:
        """
        Ingest a single session's transcript data.

        Args:
            session_dir: Path to session directory

        Returns:
            Dict with ingestion stats
        """
        session_dir = Path(session_dir)

        if not session_dir.exists() or not session_dir.is_dir():
            logger.warning(f"Session directory not found: {session_dir}")
            return {"success": False, "error": "Directory not found"}

        try:
            # Load diarized transcript
            transcript_file = session_dir / "diarized_transcript.json"

            if not transcript_file.exists():
                logger.warning(f"No diarized transcript found in {session_dir}")
                return {"success": False, "error": "No transcript found"}

            with open(transcript_file, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)

            # Extract segments
            segments = self._prepare_segments(transcript_data)

            if not segments:
                logger.warning(f"No segments found in {transcript_file}")
                return {"success": False, "error": "No segments in transcript"}

            # Add to vector store
            session_id = session_dir.name
            self.vector_store.add_transcript_segments(session_id, segments)

            logger.info(f"Successfully ingested {len(segments)} segments from {session_id}")

            return {
                "success": True,
                "session_id": session_id,
                "segments_count": len(segments)
            }

        except Exception as e:
            logger.error(f"Error ingesting session {session_dir}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def ingest_knowledge_base(self, kb_file: Path) -> Dict:
        """
        Ingest knowledge base (NPCs, quests, locations).

        Args:
            kb_file: Path to knowledge base JSON file

        Returns:
            Dict with ingestion stats
        """
        kb_file = Path(kb_file)

        if not kb_file.exists():
            logger.warning(f"Knowledge base file not found: {kb_file}")
            return {"success": False, "error": "File not found"}

        try:
            kb = self._load_knowledge_base(kb_file)

            # Convert each NPC/quest/location to document
            documents = []

            # Process NPCs
            for npc in kb.get("npcs", []):
                documents.append({
                    "text": f"{npc.get('name', 'Unknown')}: {npc.get('description', 'No description')}",
                    "metadata": {
                        "type": "npc",
                        "name": npc.get("name", "Unknown"),
                        "source": kb_file.name
                    }
                })

            # Process quests
            for quest in kb.get("quests", []):
                documents.append({
                    "text": f"{quest.get('name', 'Unknown')}: {quest.get('description', 'No description')}",
                    "metadata": {
                        "type": "quest",
                        "name": quest.get("name", "Unknown"),
                        "source": kb_file.name,
                        "status": quest.get("status", "unknown")
                    }
                })

            # Process locations
            for location in kb.get("locations", []):
                documents.append({
                    "text": f"{location.get('name', 'Unknown')}: {location.get('description', 'No description')}",
                    "metadata": {
                        "type": "location",
                        "name": location.get("name", "Unknown"),
                        "source": kb_file.name
                    }
                })

            if not documents:
                logger.warning(f"No documents extracted from {kb_file}")
                return {"success": False, "error": "No documents found"}

            # Add to vector store
            self.vector_store.add_knowledge_documents(documents)

            logger.info(f"Successfully ingested {len(documents)} documents from {kb_file.name}")

            return {
                "success": True,
                "source": kb_file.name,
                "documents_count": len(documents)
            }

        except Exception as e:
            logger.error(f"Error ingesting knowledge base {kb_file}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def ingest_all(
        self,
        output_dir: Path,
        knowledge_dir: Path,
        clear_existing: bool = False
    ) -> Dict:
        """
        Ingest all sessions and knowledge bases.

        Args:
            output_dir: Directory containing session outputs
            knowledge_dir: Directory containing knowledge base files
            clear_existing: Whether to clear existing data first

        Returns:
            Dict with overall ingestion stats
        """
        output_dir = Path(output_dir)
        knowledge_dir = Path(knowledge_dir)

        stats = {
            "sessions_ingested": 0,
            "sessions_failed": 0,
            "knowledge_bases_ingested": 0,
            "knowledge_bases_failed": 0,
            "total_segments": 0,
            "total_documents": 0
        }

        try:
            # Clear existing data if requested
            if clear_existing:
                logger.info("Clearing existing vector store data")
                self.vector_store.clear_all()

            # Ingest all sessions
            logger.info(f"Scanning for sessions in {output_dir}")

            if output_dir.exists():
                for session_dir in output_dir.iterdir():
                    if not session_dir.is_dir():
                        continue

                    result = self.ingest_session(session_dir)

                    if result.get("success"):
                        stats["sessions_ingested"] += 1
                        stats["total_segments"] += result.get("segments_count", 0)
                    else:
                        stats["sessions_failed"] += 1
            else:
                logger.warning(f"Output directory not found: {output_dir}")

            # Ingest all knowledge bases
            logger.info(f"Scanning for knowledge bases in {knowledge_dir}")

            if knowledge_dir.exists():
                for kb_file in knowledge_dir.glob("*_knowledge.json"):
                    result = self.ingest_knowledge_base(kb_file)

                    if result.get("success"):
                        stats["knowledge_bases_ingested"] += 1
                        stats["total_documents"] += result.get("documents_count", 0)
                    else:
                        stats["knowledge_bases_failed"] += 1
            else:
                logger.warning(f"Knowledge directory not found: {knowledge_dir}")

            logger.info(f"Ingestion complete: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Error during bulk ingestion: {e}", exc_info=True)
            return stats

    def _prepare_segments(self, transcript_data: Dict) -> List[Dict]:
        """Extract and prepare segments from transcript data."""
        segments = []

        for seg in transcript_data.get("segments", []):
            # Only include segments with actual text
            text = seg.get("text", "").strip()
            if not text:
                continue

            segments.append({
                "text": text,
                "speaker": seg.get("speaker", "Unknown"),
                "start": seg.get("start", 0),
                "end": seg.get("end", 0)
            })

        return segments

    def _load_knowledge_base(self, kb_file: Path) -> Dict:
        """Load a knowledge base JSON file."""
        with open(kb_file, "r", encoding="utf-8") as f:
            return json.load(f)

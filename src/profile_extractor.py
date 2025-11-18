from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .character_profile import ProfileUpdate, ProfileUpdateBatch
from .config import Config
from .exceptions import OllamaConnectionError

LOGGER = logging.getLogger(__name__)


class ProfileExtractor:
    """Generate structured character profile updates from session transcripts."""

    def __init__(
        self,
        *,
        config: Optional[Config] = None,
        llm_client: Optional[Any] = None,
    ) -> None:
        # Config is a module-level singleton; allow callers to supply a stub for testing.
        self.config = config or Config
        self.llm_client = llm_client

        # Load prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "profile_extraction.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            LOGGER.warning("Prompt template not found at %s, extraction will fail", prompt_path)
            self.prompt_template = ""

        # Initialize Ollama client if not provided
        if self.llm_client is None:
            try:
                import ollama
                self.llm_client = ollama.Client(host=Config.OLLAMA_BASE_URL)
                # Test connection
                self.llm_client.list()
                LOGGER.info("Connected to Ollama at %s", Config.OLLAMA_BASE_URL)
            except Exception as e:
                LOGGER.error("Could not initialize Ollama client: %s.", e)
                raise OllamaConnectionError(
                    "Failed to connect to Ollama. Please check that Ollama is running and accessible."
                ) from e

    def extract_profile_updates(
        self,
        *,
        session_id: str,
        transcript_segments: Sequence[Dict[str, Any]],
        character_names: Optional[List[str]] = None,
        campaign_id: Optional[str] = None,
        campaign_context: Optional[str] = None,
        generated_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 50,
    ) -> ProfileUpdateBatch:
        """Return a `ProfileUpdateBatch` for the supplied transcript segments.

        Args:
            session_id: Unique identifier for the session
            transcript_segments: List of transcript segments with text, speaker, timestamps
            character_names: List of known PC names (helps LLM focus extraction)
            campaign_id: Optional campaign identifier
            campaign_context: Optional campaign background/context
            generated_at: Optional ISO timestamp
            metadata: Optional metadata to include in batch
            chunk_size: Number of segments to process per LLM call (default 50)

        Returns:
            ProfileUpdateBatch with extracted character moments
        """
        if not session_id:
            raise ValueError("session_id is required")

        normalized_segments = list(self._normalize_segments(transcript_segments))
        if not normalized_segments:
            LOGGER.debug("No transcript segments provided for session %s", session_id)

        batch_generated_at = generated_at or datetime.utcnow().isoformat(timespec="seconds") + "Z"
        batch = ProfileUpdateBatch(
            session_id=session_id,
            campaign_id=campaign_id,
            generated_at=batch_generated_at,
            source={
                "component": "ProfileExtractor",
                "version": "0.2",
            },
            updates=[],
        )

        if metadata:
            batch.source = {**batch.source, **metadata}

        # If no LLM client available, return empty batch
        if self.llm_client is None:
            LOGGER.warning("No LLM client available, returning empty batch")
            return batch

        # Extract updates using LLM in chunks
        all_updates = []
        for i in range(0, len(normalized_segments), chunk_size):
            chunk = normalized_segments[i:i + chunk_size]
            try:
                updates = self._extract_from_chunk(
                    chunk,
                    character_names or [],
                    campaign_context or "Unknown campaign"
                )
                all_updates.extend(updates)
            except Exception as e:
                LOGGER.error("Error extracting from chunk %d-%d: %s", i, i+chunk_size, e)
                continue

        for update in all_updates:
            if not update.session_id:
                update.session_id = session_id

        batch.updates = all_updates
        LOGGER.info(
            "Extracted %d profile updates from %d segments for session %s",
            len(all_updates),
            len(normalized_segments),
            session_id
        )

        return batch

    def _extract_from_chunk(
        self,
        segments: List[Dict[str, Any]],
        character_names: List[str],
        campaign_context: str
    ) -> List[ProfileUpdate]:
        """Extract profile updates from a chunk of transcript segments using LLM."""
        # Format transcript excerpt for the prompt
        transcript_lines = []
        for seg in segments:
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "")
            start = seg.get("start", 0.0)
            timestamp = self._format_timestamp(start)
            transcript_lines.append(f"[{timestamp}] {speaker}: {text}")

        transcript_excerpt = "\n".join(transcript_lines)

        # Build prompt
        prompt = self.prompt_template.replace("{{character_names}}", ", ".join(character_names) if character_names else "Unknown")
        prompt = prompt.replace("{{campaign_context}}", campaign_context)
        prompt = prompt.replace("{{transcript_excerpt}}", transcript_excerpt)

        # Call LLM
        try:
            response = self.llm_client.chat(
                model=Config.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": "You are a D&D session analyst. Return only valid JSON, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                format="json",  # Request JSON output
                options={
                    "temperature": 0.7,
                }
            )

            # Parse response
            response_text = response.get("message", {}).get("content", "{}")
            data = json.loads(response_text)

            # Convert to ProfileUpdate objects
            updates = []
            for item in data.get("updates", []):
                try:
                    update = ProfileUpdate.from_dict(item)
                    updates.append(update)
                except (ValueError, KeyError) as e:
                    LOGGER.warning("Skipping invalid update: %s (error: %s)", item, e)
                    continue

            return updates

        except json.JSONDecodeError as e:
            LOGGER.error("Failed to parse LLM response as JSON: %s", e)
            return []
        except Exception as e:
            LOGGER.error("LLM call failed: %s", e)
            return []

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to MM:SS or HH:MM:SS format."""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def _normalize_segments(self, transcript_segments: Sequence[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        """Yield cleaned transcript segments with the keys expected by the extractor."""
        for segment in transcript_segments:
            if not isinstance(segment, dict):
                LOGGER.debug("Skipping non-dict transcript segment: %r", segment)
                continue
            text = segment.get("text")
            if not text:
                continue
            yield {
                "text": text,
                "speaker": segment.get("speaker"),
                "start": segment.get("start"),
                "end": segment.get("end"),
                "confidence": segment.get("confidence"),
            }

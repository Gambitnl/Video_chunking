from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Sequence

from .character_profile import ProfileUpdateBatch
from .config import Config

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

    def extract_profile_updates(
        self,
        *,
        session_id: str,
        transcript_segments: Sequence[Dict[str, Any]],
        campaign_id: Optional[str] = None,
        generated_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProfileUpdateBatch:
        """Return a `ProfileUpdateBatch` for the supplied transcript segments.

        The initial implementation returns an empty batch with metadata only. Future
        iterations will call an LLM to populate the `updates` collection.
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
                "version": "0.1",
            },
            updates=[],
        )

        if metadata:
            batch.source = {**batch.source, **metadata}

        return batch

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

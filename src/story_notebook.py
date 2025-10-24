from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .config import Config
from .formatter import sanitize_filename
from .story_generator import StoryGenerator


@dataclass
class StorySessionData:
    """Container for processed session metadata and transcript segments."""

    session_id: str
    json_path: Path
    metadata: Dict
    segments: List[Dict]

    @property
    def character_names(self) -> List[str]:
        names = self.metadata.get("character_names") or []
        return [name for name in names if isinstance(name, str) and name.strip()]


class StoryNotebookManager:
    """Service that loads processed sessions and generates story narratives."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = Path(output_dir or Config.OUTPUT_DIR)
        self._generator = StoryGenerator()

    def list_sessions(self, limit: Optional[int] = 25) -> List[str]:
        """Return recent session IDs based on available *_data.json outputs."""
        if not self.output_dir.exists():
            return []

        session_ids: List[str] = []
        seen: set[str] = set()
        candidates = sorted(
            self.output_dir.glob("**/*_data.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            session_id = self._extract_session_id(candidate)
            if session_id and session_id not in seen:
                seen.add(session_id)
                session_ids.append(session_id)
            if limit is not None and len(session_ids) >= limit:
                break
        return session_ids

    def load_session(self, session_id: str) -> StorySessionData:
        """Load the latest processed data file for the requested session."""
        json_path = self._find_session_json(session_id)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        metadata = data.get("metadata") or {}
        segments = data.get("segments") or []
        return StorySessionData(
            session_id=session_id,
            json_path=json_path,
            metadata=metadata,
            segments=segments,
        )

    def build_session_info(self, session: StorySessionData) -> str:
        """Return bullet list details summarizing the selected session."""
        metadata = session.metadata
        stats = metadata.get("statistics") or {}
        total_segments = len(session.segments)
        ic_segments = stats.get("ic_segments", 0)
        ooc_segments = stats.get("ooc_segments", 0)
        duration = (
            stats.get("total_duration_formatted")
            or f"{stats.get('total_duration_seconds', 0)}s"
        )
        ic_share = stats.get("ic_percentage")

        details = [
            f"- **Session ID**: `{session.session_id}`",
            f"- **Segments**: {total_segments} total ({ic_segments} IC / {ooc_segments} OOC)",
            f"- **Duration**: {duration}",
            f"- **Source JSON**: `{session.json_path}`",
        ]

        if isinstance(ic_share, (int, float)):
            details.insert(
                3,  # place IC share before duration
                f"- **IC Share**: {ic_share:.1f}%",
            )

        if session.character_names:
            details.append(
                f"- **Characters**: {', '.join(session.character_names)}"
            )

        return "\n".join(details)

    def generate_narrator(
        self,
        session: StorySessionData,
        notebook_context: str = "",
        temperature: float = 0.5,
        save: bool = True,
    ) -> Tuple[str, Optional[Path]]:
        """Generate a narrator summary; optionally persist it."""
        story = self._generator.generate_narrator_summary(
            segments=session.segments,
            character_names=session.character_names,
            notebook_context=notebook_context,
            temperature=temperature,
        )
        saved_path = self.save_narrative(
            session, "narrator", story
        ) if save else None
        return story, saved_path

    def generate_character(
        self,
        session: StorySessionData,
        character_name: str,
        notebook_context: str = "",
        temperature: float = 0.5,
        save: bool = True,
    ) -> Tuple[str, Optional[Path]]:
        """Generate a character POV narrative; optionally persist it."""
        story = self._generator.generate_character_pov(
            segments=session.segments,
            character_name=character_name,
            character_names=session.character_names,
            notebook_context=notebook_context,
            temperature=temperature,
        )
        saved_path = self.save_narrative(
            session, character_name, story
        ) if save else None
        return story, saved_path

    def generate_batch(
        self,
        session_ids: Iterable[str],
        include_narrator: bool = True,
        characters: Optional[Iterable[str]] = None,
        notebook_context: str = "",
        temperature: float = 0.5,
    ) -> Dict[str, Dict[str, Path]]:
        """
        Generate narratives for multiple sessions.

        Returns mapping of session_id -> {perspective: saved_path}.
        """
        results: Dict[str, Dict[str, Path]] = {}
        for session_id in session_ids:
            session = self.load_session(session_id)
            session_results: Dict[str, Path] = {}

            if include_narrator:
                _, path = self.generate_narrator(
                    session,
                    notebook_context=notebook_context,
                    temperature=temperature,
                )
                if path:
                    session_results["narrator"] = path

            desired_characters = (
                list(characters)
                if characters is not None
                else session.character_names
            )
            for character in desired_characters:
                if not character:
                    continue
                _, path = self.generate_character(
                    session,
                    character,
                    notebook_context=notebook_context,
                    temperature=temperature,
                )
                if path:
                    session_results[character] = path

            results[session_id] = session_results
        return results

    def save_narrative(
        self,
        session: StorySessionData,
        perspective: str,
        story: str,
    ) -> Path:
        """Persist generated narrative markdown alongside session artifacts."""
        if not story.strip():
            raise ValueError("Narrative content is empty.")

        base_dir = session.json_path.parent
        if base_dir == self.output_dir:
            base_dir = base_dir / session.session_id

        narratives_dir = base_dir / "narratives"
        narratives_dir.mkdir(parents=True, exist_ok=True)

        safe_perspective = sanitize_filename(perspective or "narrative") or "narrative"
        narrative_path = narratives_dir / f"{session.session_id}_{safe_perspective.lower()}.md"
        narrative_path.write_text(story, encoding="utf-8")
        return narrative_path

    @staticmethod
    def format_notebook_status(notebook_context: str) -> str:
        """Return a concise description of the loaded notebook context."""
        if notebook_context:
            sample = notebook_context[:200].replace("\n", " ").replace("\r", " ")
            return (
                f"Notebook context loaded ({len(notebook_context)} chars). "
                f"Sample: {sample}..."
            )
        return (
            "No notebook context loaded yet. Use the Document Viewer tab to "
            "import campaign notes."
        )

    def _find_session_json(self, session_id: str) -> Path:
        session_prefix = session_id.replace(" ", "_")
        candidates = list(self.output_dir.glob(f"**/{session_prefix}*_data.json"))
        if not candidates:
            raise FileNotFoundError(f"No session data found for session_id={session_id}")
        return max(candidates, key=lambda path: path.stat().st_mtime)

    @staticmethod
    def _extract_session_id(candidate: Path) -> Optional[str]:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            metadata = data.get("metadata") or {}
            session_id = metadata.get("session_id")
            if session_id:
                return str(session_id)
        except Exception:
            pass
        return candidate.stem.replace("_data", "")


def load_notebook_context_file(path: Optional[Path]) -> str:
    """Helper to load optional notebook context from a text file."""
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")

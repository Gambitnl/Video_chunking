"""Audio segment export utilities"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from pydub import AudioSegment
from .config import Config
from .logger import get_logger


class AudioSnipper:
    """Export per-segment audio clips aligned with transcription segments."""

    def __init__(self):
        # Reuse pydub for convenience; additional options can be added later.
        self.logger = get_logger('snipper')
        self.clean_stale_clips = Config.CLEAN_STALE_CLIPS

    def _clear_session_directory(self, session_dir: Path) -> int:
        """Remove existing snippet artifacts for a session."""
        if not session_dir.exists():
            return 0

        removed = 0

        for wav_file in session_dir.glob("*.wav"):
            try:
                wav_file.unlink()
                removed += 1
            except OSError as exc:
                self.logger.warning("Failed to remove stale clip %s: %s", wav_file, exc)

        manifest_file = session_dir / "manifest.json"
        if manifest_file.exists():
            try:
                manifest_file.unlink()
            except OSError as exc:
                self.logger.warning("Failed to remove stale manifest %s: %s", manifest_file, exc)

        if removed:
            self.logger.info("Cleared %d stale clips from %s", removed, session_dir)
        else:
            self.logger.debug("No stale clips found in %s", session_dir)

        return removed

    def export_segments(
        self,
        audio_path: Path,
        segments: List[Dict],
        base_output_dir: Path,
        session_id: str,
        classifications: Optional[List] = None
    ) -> Dict[str, Optional[Path]]:
        """
        Export aligned audio snippets for each transcription segment.

        Args:
            audio_path: Path to full session WAV file.
            segments: Transcription segments enriched with speaker labels.
            base_output_dir: Directory where segment folders should live.
            session_id: Session identifier for folder naming.
            classifications: Optional classification results aligned with segments.

        Returns:
            Dict with paths to the created directory and manifest file.
        """
        if not segments:
            self.logger.warning("No transcription segments provided; skipping snippet export")
            return {"segments_dir": None, "manifest": None}

        base_output_dir = Path(base_output_dir)
        session_dir = base_output_dir / session_id
        self.logger.info(
            "Exporting %d audio snippets to %s (audio=%s)",
            len(segments),
            session_dir,
            audio_path
        )

        # Ensure base directory exists before manipulating session folder
        base_output_dir.mkdir(parents=True, exist_ok=True)

        if self.clean_stale_clips:
            self._clear_session_directory(session_dir)
        else:
            self.logger.debug(
                "Skipping stale clip cleanup for %s (CLEAN_STALE_CLIPS disabled)",
                session_dir
            )

        session_dir.mkdir(parents=True, exist_ok=True)

        audio = AudioSegment.from_file(str(audio_path))
        manifest = []

        for index, segment in enumerate(segments, start=1):
            start_time = max(float(segment.get('start_time', 0.0)), 0.0)
            end_time = max(float(segment.get('end_time', start_time)), start_time)

            # Ensure non-zero duration
            if end_time - start_time < 0.01:
                end_time = start_time + 0.01

            start_ms = int(start_time * 1000)
            end_ms = int(end_time * 1000)

            clip = audio[start_ms:end_ms]

            speaker = segment.get('speaker') or "UNKNOWN"
            safe_speaker = re.sub(r'[^A-Za-z0-9_-]+', '_', speaker).strip("_") or "UNKNOWN"

            filename = f"segment_{index:04}_{safe_speaker}.wav"
            clip_path = session_dir / filename
            clip.export(str(clip_path), format="wav")

            classification_entry = None
            if classifications and len(classifications) >= index:
                cls_obj = classifications[index - 1]
                classification_entry = {
                    "label": getattr(cls_obj, 'classification', None) if not isinstance(cls_obj, dict) else cls_obj.get('classification'),
                    "confidence": getattr(cls_obj, 'confidence', None) if not isinstance(cls_obj, dict) else cls_obj.get('confidence'),
                    "reasoning": getattr(cls_obj, 'reasoning', None) if not isinstance(cls_obj, dict) else cls_obj.get('reasoning'),
                    "character": getattr(cls_obj, 'character', None) if not isinstance(cls_obj, dict) else cls_obj.get('character')
                }

            manifest.append({
                "index": index,
                "speaker": speaker,
                "start_time": start_time,
                "end_time": end_time,
                "file": clip_path.name,
                "text": segment.get('text', ""),
                "classification": classification_entry
            })

        manifest_path = session_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger.info(
            "Snippet export complete: %d clips, manifest=%s",
            len(manifest),
            manifest_path
        )

        return {
            "segments_dir": session_dir,
            "manifest": manifest_path
        }

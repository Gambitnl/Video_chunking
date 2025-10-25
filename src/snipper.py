"""Audio segment export utilities"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from pydub import AudioSegment
from .config import Config
from .logger import get_logger


import threading

class AudioSnipper:
    """Export per-segment audio clips aligned with transcription segments."""

    def __init__(self):
        self.logger = get_logger('snipper')
        self.clean_stale_clips = Config.CLEAN_STALE_CLIPS
        self._manifest_lock = threading.Lock()

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

    def initialize_manifest(self, session_dir: Path) -> Path:
        session_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = session_dir / "manifest.json"
        with self._manifest_lock:
            if self.clean_stale_clips:
                self._clear_session_directory(session_dir)
            manifest = {
                "session_id": session_dir.name,
                "status": "in_progress",
                "total_clips": 0,
                "clips": []
            }
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest_path

    def export_incremental(self, audio_path: Path, segment: Dict, index: int, session_dir: Path, manifest_path: Path, classification: Optional[Dict] = None):
        audio = AudioSegment.from_file(str(audio_path))
        start_time = max(float(segment.get('start_time', 0.0)), 0.0)
        end_time = max(float(segment.get('end_time', start_time)), start_time)

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

        clip_manifest = {
            "id": index,
            "file": clip_path.name,
            "speaker": speaker,
            "start": start_time,
            "end": end_time,
            "status": "ready",
            "text": segment.get('text', ""),
            "classification": classification
        }

        with self._manifest_lock:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_data["clips"].append(clip_manifest)
            manifest_data["total_clips"] = len(manifest_data["clips"])
            manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def export_segments(
        self,
        audio_path: Path,
        segments: List[Dict],
        base_output_dir: Path,
        session_id: str,
        classifications: Optional[List] = None
    ) -> Dict[str, Optional[Path]]:
        base_output_dir = Path(base_output_dir)
        session_dir = base_output_dir / session_id
        manifest_path = self.initialize_manifest(session_dir)

        if not segments:
            self.logger.warning("No transcription segments provided; generating placeholder manifest")
            with self._manifest_lock:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest_data["status"] = "complete"
                manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"segments_dir": session_dir, "manifest": manifest_path}

        self.logger.info(
            "Exporting %d audio snippets to %s (audio=%s)",
            len(segments),
            session_dir,
            audio_path
        )

        for index, segment in enumerate(segments, start=1):
            classification_entry = None
            if classifications and len(classifications) >= index:
                cls_obj = classifications[index - 1]
                classification_entry = {
                    "label": getattr(cls_obj, 'classification', None) if not isinstance(cls_obj, dict) else cls_obj.get('classification'),
                    "confidence": getattr(cls_obj, 'confidence', None) if not isinstance(cls_obj, dict) else cls_obj.get('confidence'),
                    "reasoning": getattr(cls_obj, 'reasoning', None) if not isinstance(cls_obj, dict) else cls_obj.get('reasoning'),
                    "character": getattr(cls_obj, 'character', None) if not isinstance(cls_obj, dict) else cls_obj.get('character')
                }
            self.export_incremental(audio_path, segment, index, session_dir, manifest_path, classification_entry)

        with self._manifest_lock:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_data["status"] = "complete"
            manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

        self.logger.info(
            "Snippet export complete: %d clips, manifest=%s",
            len(segments),
            manifest_path
        )

        return {
            "segments_dir": session_dir,
            "manifest": manifest_path
        }

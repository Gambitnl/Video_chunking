"""Audio segment export utilities"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from pydub import AudioSegment


class AudioSnipper:
    """Export per-segment audio clips aligned with transcription segments."""

    def __init__(self):
        # Reuse pydub for convenience; additional options can be added later.
        pass

    def export_segments(
        self,
        audio_path: Path,
        segments: List[Dict],
        base_output_dir: Path,
        session_id: str
    ) -> Dict[str, Optional[Path]]:
        """
        Export aligned audio snippets for each transcription segment.

        Args:
            audio_path: Path to full session WAV file.
            segments: Transcription segments enriched with speaker labels.
            base_output_dir: Directory where segment folders should live.
            session_id: Session identifier for folder naming.

        Returns:
            Dict with paths to the created directory and manifest file.
        """
        if not segments:
            return {"segments_dir": None, "manifest": None}

        base_output_dir = Path(base_output_dir)
        session_dir = base_output_dir / session_id
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

            manifest.append({
                "index": index,
                "speaker": speaker,
                "start_time": start_time,
                "end_time": end_time,
                "file": clip_path.name
            })

        manifest_path = session_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return {
            "segments_dir": session_dir,
            "manifest": manifest_path
        }

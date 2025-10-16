"""SRT subtitle export functionality for D&D sessions"""
from pathlib import Path
from typing import List, Dict
import logging


class SRTExporter:
    """Export transcripts as SRT subtitle files"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def export_srt(self, segments: List[Dict], output_path: Path, include_speaker: bool = True):
        """
        Export transcript segments as SRT subtitle file.

        Args:
            segments: List of segment dictionaries with 'start_time', 'end_time', 'text', and optionally 'speaker'
            output_path: Path to save the SRT file
            include_speaker: Whether to include speaker labels in subtitles

        SRT Format:
        1
        00:00:15,230 --> 00:00:18,450
        [Speaker Name] Dialog text

        2
        00:00:18,451 --> 00:00:22,100
        [Speaker Name] More dialog
        """
        try:
            self.logger.info(f"Exporting {len(segments)} segments to SRT: {output_path}")

            with open(output_path, 'w', encoding='utf-8') as f:
                for i, seg in enumerate(segments, 1):
                    # SRT index
                    f.write(f"{i}\n")

                    # Timestamps
                    start_time = self._format_srt_time(seg.get('start_time', 0))
                    end_time = self._format_srt_time(seg.get('end_time', 0))
                    f.write(f"{start_time} --> {end_time}\n")

                    # Text content
                    text = seg.get('text', '').strip()

                    if include_speaker and 'speaker' in seg:
                        speaker = seg['speaker']
                        f.write(f"[{speaker}] {text}\n")
                    else:
                        f.write(f"{text}\n")

                    # Blank line between subtitles
                    f.write("\n")

            self.logger.info(f"Successfully exported SRT file: {output_path}")

        except Exception as e:
            self.logger.error(f"Failed to export SRT: {e}", exc_info=True)
            raise

    def _format_srt_time(self, seconds: float) -> str:
        """
        Convert seconds to SRT time format (HH:MM:SS,mmm).

        Args:
            seconds: Time in seconds (float)

        Returns:
            Formatted time string (e.g., "00:15:23,450")
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def export_from_json(self, json_path: Path, output_path: Path, include_speaker: bool = True):
        """
        Export SRT from a JSON transcript file.

        Args:
            json_path: Path to JSON file containing transcript
            output_path: Path to save the SRT file
            include_speaker: Whether to include speaker labels
        """
        import json

        self.logger.info(f"Loading transcript from JSON: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract segments from JSON
        segments = data.get('segments', [])

        if not segments:
            raise ValueError(f"No segments found in JSON file: {json_path}")

        self.export_srt(segments, output_path, include_speaker)

    def export_ic_only_srt(self, json_path: Path, output_path: Path, include_speaker: bool = True):
        """
        Export SRT with only in-character segments.

        Args:
            json_path: Path to JSON file containing transcript
            output_path: Path to save the SRT file
            include_speaker: Whether to include speaker labels
        """
        import json

        self.logger.info(f"Loading IC-only transcript from JSON: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        segments = data.get('segments', [])

        # Filter for IC segments only
        ic_segments = [
            seg for seg in segments
            if seg.get('classification', '').upper() == 'IC'
        ]

        if not ic_segments:
            raise ValueError(f"No IC segments found in JSON file: {json_path}")

        self.logger.info(f"Found {len(ic_segments)} IC segments out of {len(segments)} total")
        self.export_srt(ic_segments, output_path, include_speaker)

    def export_ooc_only_srt(self, json_path: Path, output_path: Path, include_speaker: bool = True):
        """
        Export SRT with only out-of-character segments.

        Args:
            json_path: Path to JSON file containing transcript
            output_path: Path to save the SRT file
            include_speaker: Whether to include speaker labels
        """
        import json

        self.logger.info(f"Loading OOC-only transcript from JSON: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        segments = data.get('segments', [])

        # Filter for OOC segments only
        ooc_segments = [
            seg for seg in segments
            if seg.get('classification', '').upper() == 'OOC'
        ]

        if not ooc_segments:
            raise ValueError(f"No OOC segments found in JSON file: {json_path}")

        self.logger.info(f"Found {len(ooc_segments)} OOC segments out of {len(segments)} total")
        self.export_srt(ooc_segments, output_path, include_speaker)

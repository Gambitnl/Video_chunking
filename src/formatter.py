"""Output formatters for different transcript formats"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import timedelta
from .classifier import ClassificationResult
from .logger import get_logger
from .constants import Classification, OutputFormat


logger = get_logger(__name__)

def sanitize_filename(name: str) -> str:
    """Remove characters that are invalid for file paths."""
    # Replace spaces and common separators with underscores
    name = re.sub(r'[\s/:]', '_', name)
    # Remove any character that is not a letter, number, underscore, or hyphen
    name = re.sub(r'[^\w\-]', '', name)
    return name

class TranscriptFormatter:
    """
    Formats transcription results into various output formats.

    Supports:
    1. Plain text with speaker labels and timestamps
    2. IC-only text (game narrative only)
    3. OOC-only text (banter and meta-discussion)
    4. Full JSON with all metadata
    5. SRT subtitle format (future enhancement)
    """

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """Format seconds as HH:MM:SS"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def format_full_transcript(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Format complete transcript with all information.

        Format:
        [HH:MM:SS] Speaker (IC/OOC): Text
        [HH:MM:SS] Speaker as Character (IC): Text
        """
        lines = []
        lines.append("=" * 80)
        lines.append("D&D SESSION TRANSCRIPT - FULL VERSION")
        lines.append("=" * 80)
        lines.append("")

        for seg, classif in zip(segments, classifications):
            timestamp = self.format_timestamp(seg['start_time'])
            speaker = seg.get('speaker', 'UNKNOWN')

            # Map to person name if available
            if speaker_profiles and speaker in speaker_profiles:
                speaker = speaker_profiles[speaker]

            # Build speaker label
            speaker_label = speaker

            if classif.character and classif.classification == Classification.IN_CHARACTER:
                speaker_label = f"{speaker} as {classif.character}"

            # Add classification marker
            marker = classif.classification

            # Format line
            line = f"[{timestamp}] {speaker_label} ({marker}): {seg['text']}"
            lines.append(line)

        return "\n".join(lines)

    def format_ic_only(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Format IC-only transcript (game narrative only).

        Format shows characters and DM narration, removes OOC banter.
        """
        lines = []
        lines.append("=" * 80)
        lines.append("D&D SESSION TRANSCRIPT - IN-CHARACTER ONLY")
        lines.append("=" * 80)
        lines.append("")

        for seg, classif in zip(segments, classifications):
            # Skip OOC content
            if classif.classification == Classification.OUT_OF_CHARACTER:
                continue

            timestamp = self.format_timestamp(seg['start_time'])
            speaker = seg.get('speaker', 'UNKNOWN')

            # Map to person name if available
            if speaker_profiles and speaker in speaker_profiles:
                speaker = speaker_profiles[speaker]

            # Use character name if available, otherwise speaker
            display_name = classif.character or speaker

            line = f"[{timestamp}] {display_name}: {seg['text']}"
            lines.append(line)

        return "\n".join(lines)

    def format_ooc_only(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Format OOC-only transcript (banter and meta-discussion).

        Useful for remembering jokes or strategy discussions.
        """
        lines = []
        lines.append("=" * 80)
        lines.append("D&D SESSION TRANSCRIPT - OUT-OF-CHARACTER ONLY")
        lines.append("=" * 80)
        lines.append("")

        for seg, classif in zip(segments, classifications):
            # Skip IC content
            if classif.classification == Classification.IN_CHARACTER:
                continue

            timestamp = self.format_timestamp(seg['start_time'])
            speaker = seg.get('speaker', 'UNKNOWN')

            # Map to person name if available
            if speaker_profiles and speaker in speaker_profiles:
                speaker = speaker_profiles[speaker]

            line = f"[{timestamp}] {speaker}: {seg['text']}"
            lines.append(line)

        return "\n".join(lines)

    def format_json(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Format as JSON with complete metadata.

        Useful for:
        - Further processing
        - Building custom UIs
        - Analysis and statistics
        """
        output = {
            "metadata": metadata or {},
            "segments": []
        }

        for seg, classif in zip(segments, classifications):
            speaker = seg.get('speaker', 'UNKNOWN')
            person_name = None

            if speaker_profiles and speaker in speaker_profiles:
                person_name = speaker_profiles[speaker]

            segment_data = {
                "start_time": seg['start_time'],
                "end_time": seg['end_time'],
                "duration": seg['end_time'] - seg['start_time'],
                "text": seg['text'],
                "speaker_id": speaker,
                "speaker_name": person_name,
                "classification": classif.classification,
                "classification_confidence": classif.confidence,
                "classification_reasoning": classif.reasoning,
                "character": classif.character,
                "words": seg.get('words', [])
            }

            output["segments"].append(segment_data)

        return json.dumps(output, indent=2, ensure_ascii=False)

    def save_all_formats(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        output_dir: Path,
        session_name: str,
        speaker_profiles: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Save transcript in all formats.

        Args:
            segments: Transcribed and diarized segments
            classifications: IC/OOC classifications
            output_dir: Directory to save outputs
            session_name: Base name for output files
            speaker_profiles: Optional speaker ID to name mapping
            metadata: Optional metadata to include in JSON
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)

        # Full transcript
        full_text = self.format_full_transcript(
            segments, classifications, speaker_profiles
        )
        (output_dir / f"{session_name}_full.txt").write_text(
            full_text, encoding='utf-8'
        )

        # IC-only transcript
        ic_text = self.format_ic_only(
            segments, classifications, speaker_profiles
        )
        (output_dir / f"{session_name}_ic_only.txt").write_text(
            ic_text, encoding='utf-8'
        )

        # OOC-only transcript
        ooc_text = self.format_ooc_only(
            segments, classifications, speaker_profiles
        )
        (output_dir / f"{session_name}_ooc_only.txt").write_text(
            ooc_text, encoding='utf-8'
        )

        # JSON format
        json_text = self.format_json(
            segments, classifications, speaker_profiles, metadata
        )
        json_path = output_dir / f"{session_name}_data.json"
        json_path.write_text(json_text, encoding='utf-8')

        # SRT subtitle exports
        try:
            from .srt_exporter import SRTExporter
            srt_exporter = SRTExporter()

            # Full SRT
            srt_exporter.export_from_json(
                json_path,
                output_dir / f"{session_name}_full.srt",
                include_speaker=True
            )

            # IC-only SRT
            srt_exporter.export_ic_only_srt(
                json_path,
                output_dir / f"{session_name}_ic_only.srt",
                include_speaker=True
            )

            # OOC-only SRT
            srt_exporter.export_ooc_only_srt(
                json_path,
                output_dir / f"{session_name}_ooc_only.srt",
                include_speaker=True
            )
        except Exception as e:
            logger.warning(f"SRT export failed: {e}")

        return {
            OutputFormat.FULL: output_dir / f"{session_name}_full.txt",
            OutputFormat.IC_ONLY: output_dir / f"{session_name}_ic_only.txt",
            OutputFormat.OOC_ONLY: output_dir / f"{session_name}_ooc_only.txt",
            OutputFormat.JSON: json_path,
            OutputFormat.SRT_FULL: output_dir / f"{session_name}_full.srt",
            OutputFormat.SRT_IC: output_dir / f"{session_name}_ic_only.srt",
            OutputFormat.SRT_OOC: output_dir / f"{session_name}_ooc_only.srt"
        }


class StatisticsGenerator:
    """Generate statistics about a D&D session"""

    @staticmethod
    def generate_stats(
        segments: List[Dict],
        classifications: List[ClassificationResult]
    ) -> Dict:
        """
        Generate interesting statistics about the session.

        Returns:
            Dictionary of statistics
        """
        total_segments = len(segments)
        ic_segments = sum(1 for c in classifications if c.classification == Classification.IN_CHARACTER)
        ooc_segments = sum(1 for c in classifications if c.classification == Classification.OUT_OF_CHARACTER)
        mixed_segments = sum(1 for c in classifications if c.classification == Classification.MIXED)

        # Duration
        total_duration = segments[-1]['end_time'] if segments else 0
        ic_duration = sum(
            seg['end_time'] - seg['start_time']
            for seg, c in zip(segments, classifications)
            if c.classification == Classification.IN_CHARACTER
        )

        # Speaker distribution
        speaker_counts = {}
        for seg in segments:
            speaker = seg.get('speaker', 'UNKNOWN')
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

        # Character appearances
        character_counts = {}
        for c in classifications:
            if c.character:
                character_counts[c.character] = character_counts.get(c.character, 0) + 1

        return {
            'total_duration_seconds': total_duration,
            'total_duration_formatted': TranscriptFormatter.format_timestamp(total_duration),
            'total_segments': total_segments,
            'ic_segments': ic_segments,
            'ooc_segments': ooc_segments,
            'mixed_segments': mixed_segments,
            'ic_percentage': (ic_segments / total_segments * 100) if total_segments > 0 else 0,
            'ic_duration_seconds': ic_duration,
            'ic_duration_formatted': TranscriptFormatter.format_timestamp(ic_duration),
            'speaker_distribution': speaker_counts,
            'character_appearances': character_counts
        }

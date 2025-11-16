"""
Intermediate Output Manager

Handles saving and loading intermediate stage outputs for the processing pipeline.
This enables manual execution of individual pipeline stages using outputs from
previous stages.

Supported stages:
- Stage 4: Merged Transcript (TranscriptionSegment list)
- Stage 5: Diarization (Speaker-labeled segments)
- Stage 6: IC/OOC Classification (Classification results)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.transcriber import TranscriptionSegment

logger = logging.getLogger("DDSessionProcessor.intermediate_output")


class IntermediateOutputManager:
    """Manages intermediate output files for pipeline stages."""

    STAGE_NAMES = {
        4: "merged_transcript",
        5: "diarization",
        6: "classification",
    }

    def __init__(self, session_output_dir: Path):
        """
        Initialize the manager.

        Args:
            session_output_dir: Path to the session's output directory
        """
        self.session_output_dir = Path(session_output_dir)
        self.intermediates_dir = self.session_output_dir / "intermediates"
        self.session_id = session_output_dir.name

    def ensure_intermediates_dir(self) -> Path:
        """
        Ensure the intermediates directory exists.

        Returns:
            Path to the intermediates directory
        """
        self.intermediates_dir.mkdir(parents=True, exist_ok=True)
        return self.intermediates_dir

    def get_stage_filename(self, stage_number: int) -> str:
        """
        Get the filename for a stage's output.

        Args:
            stage_number: The stage number (4, 5, or 6)

        Returns:
            Filename for the stage's output file
        """
        stage_name = self.STAGE_NAMES.get(stage_number)
        if not stage_name:
            raise ValueError(f"Invalid stage number: {stage_number}")
        return f"stage_{stage_number}_{stage_name}.json"

    def get_stage_path(self, stage_number: int) -> Path:
        """
        Get the full path for a stage's output file.

        Args:
            stage_number: The stage number (4, 5, or 6)

        Returns:
            Path to the stage's output file
        """
        return self.intermediates_dir / self.get_stage_filename(stage_number)

    def save_stage_output(
        self,
        stage_number: int,
        segments: List[Dict[str, Any]],
        statistics: Optional[Dict[str, Any]] = None,
        input_file: Optional[str] = None,
    ) -> Path:
        """
        Save a stage's output to JSON.

        Args:
            stage_number: The stage number (4, 5, or 6)
            segments: List of segment dictionaries
            statistics: Optional statistics about the stage output
            input_file: Optional path to the input file that was processed

        Returns:
            Path to the saved file

        Raises:
            ValueError: If stage_number is invalid
        """
        self.ensure_intermediates_dir()

        stage_name = self.STAGE_NAMES.get(stage_number)
        if not stage_name:
            raise ValueError(f"Invalid stage number: {stage_number}")

        output_data = {
            "metadata": {
                "session_id": self.session_id,
                "stage": stage_name,
                "stage_number": stage_number,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
            },
            "segments": segments,
        }

        if input_file:
            output_data["metadata"]["input_file"] = str(input_file)

        if statistics:
            output_data["statistics"] = statistics

        output_path = self.get_stage_path(stage_number)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(
            "Saved stage %d (%s) output to %s (%d segments)",
            stage_number,
            stage_name,
            output_path,
            len(segments),
        )

        return output_path

    def load_stage_output(
        self, stage_number: int
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Load a stage's output from JSON.

        Args:
            stage_number: The stage number (4, 5, or 6)

        Returns:
            Tuple of (segments, metadata)

        Raises:
            FileNotFoundError: If the stage output file doesn't exist
            ValueError: If the file format is invalid
        """
        output_path = self.get_stage_path(stage_number)

        if not output_path.exists():
            raise FileNotFoundError(
                f"Stage {stage_number} output not found at {output_path}"
            )

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "metadata" not in data or "segments" not in data:
            raise ValueError(
                f"Invalid stage output format in {output_path}: "
                "missing 'metadata' or 'segments'"
            )

        metadata = data["metadata"]
        segments = data["segments"]

        # Validate metadata
        required_metadata = ["session_id", "stage", "stage_number", "timestamp"]
        for field in required_metadata:
            if field not in metadata:
                raise ValueError(
                    f"Invalid stage output format in {output_path}: "
                    f"missing metadata field '{field}'"
                )

        logger.info(
            "Loaded stage %d (%s) output from %s (%d segments)",
            stage_number,
            metadata["stage"],
            output_path,
            len(segments),
        )

        return segments, metadata

    def stage_output_exists(self, stage_number: int) -> bool:
        """
        Check if a stage's output file exists.

        Args:
            stage_number: The stage number (4, 5, or 6)

        Returns:
            True if the file exists, False otherwise
        """
        return self.get_stage_path(stage_number).exists()

    # Stage-specific save methods

    def save_merged_transcript(
        self,
        segments: List[TranscriptionSegment],
        input_file: Optional[str] = None,
    ) -> Path:
        """
        Save Stage 4 (merged transcript) output.

        Args:
            segments: List of TranscriptionSegment objects
            input_file: Optional path to the input file

        Returns:
            Path to the saved file
        """
        # Convert TranscriptionSegment objects to dictionaries
        segment_dicts = []
        total_duration = 0.0

        for seg in segments:
            seg_dict = {
                "text": seg.text,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
            }
            if seg.confidence is not None:
                seg_dict["confidence"] = seg.confidence
            if seg.words:
                seg_dict["words"] = seg.words

            segment_dicts.append(seg_dict)

            if seg.end_time and seg.end_time > total_duration:
                total_duration = seg.end_time

        statistics = {
            "total_segments": len(segments),
            "total_duration": total_duration,
        }

        return self.save_stage_output(
            stage_number=4,
            segments=segment_dicts,
            statistics=statistics,
            input_file=input_file,
        )

    def save_diarization(
        self,
        segments: List[Dict[str, Any]],
        input_file: Optional[str] = None,
    ) -> Path:
        """
        Save Stage 5 (diarization) output.

        Args:
            segments: List of speaker-labeled segment dictionaries
            input_file: Optional path to the input file

        Returns:
            Path to the saved file
        """
        # Calculate statistics
        speaker_time: Dict[str, float] = {}
        unique_speakers = set()

        for seg in segments:
            speaker = seg.get("speaker", "UNKNOWN")
            unique_speakers.add(speaker)

            duration = seg.get("end_time", 0.0) - seg.get("start_time", 0.0)
            speaker_time[speaker] = speaker_time.get(speaker, 0.0) + duration

        statistics = {
            "unique_speakers": len(unique_speakers),
            "speaker_time": speaker_time,
            "total_segments": len(segments),
        }

        return self.save_stage_output(
            stage_number=5,
            segments=segments,
            statistics=statistics,
            input_file=input_file,
        )

    def save_classification(
        self,
        segments: List[Dict[str, Any]],
        classifications: List[Dict[str, Any]],
        input_file: Optional[str] = None,
    ) -> Path:
        """
        Save Stage 6 (IC/OOC classification) output.

        Args:
            segments: List of speaker-labeled segment dictionaries
            classifications: List of classification result dictionaries
            input_file: Optional path to the input file

        Returns:
            Path to the saved file
        """
        # Merge segments with classifications
        merged_segments = []
        ic_count = 0
        ooc_count = 0
        mixed_count = 0

        for index, (seg, classif) in enumerate(zip(segments, classifications)):
            merged_seg = {
                "segment_index": classif.get("segment_index", index),
                "text": seg.get("text", ""),
                "start_time": seg.get("start_time", 0.0),
                "end_time": seg.get("end_time", 0.0),
                "speaker": seg.get("speaker", "UNKNOWN"),
                "classification": classif.get("classification", "IC"),
                "confidence": classif.get("confidence", 0.0),
            }

            if "reasoning" in classif:
                merged_seg["reasoning"] = classif["reasoning"]
            if "character" in classif:
                merged_seg["character"] = classif["character"]

            merged_segments.append(merged_seg)

            # Count classifications
            classification = classif.get("classification", "IC")
            if classification == "IC":
                ic_count += 1
            elif classification == "OOC":
                ooc_count += 1
            elif classification == "MIXED":
                mixed_count += 1

        total = len(merged_segments)
        ic_percentage = (ic_count / total * 100) if total > 0 else 0.0

        statistics = {
            "total_segments": total,
            "ic_count": ic_count,
            "ooc_count": ooc_count,
            "mixed_count": mixed_count,
            "ic_percentage": ic_percentage,
        }

        return self.save_stage_output(
            stage_number=6,
            segments=merged_segments,
            statistics=statistics,
            input_file=input_file,
        )

    # Stage-specific load methods

    def load_merged_transcript(self) -> List[TranscriptionSegment]:
        """
        Load Stage 4 (merged transcript) output.

        Returns:
            List of TranscriptionSegment objects

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        segments_data, metadata = self.load_stage_output(4)

        segments = []
        for seg_data in segments_data:
            seg = TranscriptionSegment(
                text=seg_data["text"],
                start_time=seg_data["start_time"],
                end_time=seg_data["end_time"],
                confidence=seg_data.get("confidence"),
                words=seg_data.get("words"),
            )
            segments.append(seg)

        return segments

    def load_diarization(self) -> List[Dict[str, Any]]:
        """
        Load Stage 5 (diarization) output.

        Returns:
            List of speaker-labeled segment dictionaries

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        segments, metadata = self.load_stage_output(5)
        return segments

    def load_classification(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Load Stage 6 (IC/OOC classification) output.

        Returns:
            Tuple of (segments, classifications) where classifications
            are extracted from the merged segment data

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        merged_data, metadata = self.load_stage_output(6)

        segments = []
        classifications = []

        for index, item in enumerate(merged_data):
            # Extract segment data
            segment = {
                "segment_index": item.get("segment_index", index),
                "text": item["text"],
                "start_time": item["start_time"],
                "end_time": item["end_time"],
                "speaker": item.get("speaker", "UNKNOWN"),
            }
            if "words" in item:
                segment["words"] = item["words"]
            if "confidence" in item:
                segment["confidence"] = item["confidence"]

            # Extract classification data
            classification = {
                "segment_index": item.get("segment_index", index),
                "classification": item.get("classification", "IC"),
                "confidence": item.get("confidence", 0.0),
            }
            if "reasoning" in item:
                classification["reasoning"] = item["reasoning"]
            if "character" in item:
                classification["character"] = item["character"]

            segments.append(segment)
            classifications.append(classification)

        return segments, classifications

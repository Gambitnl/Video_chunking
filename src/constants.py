"""
Constants and enums for type-safe value usage throughout the codebase.

This module provides enums and constant classes to replace magic strings and numbers,
improving type safety, enabling IDE autocomplete, and making the codebase more maintainable.
"""
from enum import Enum
from typing import Tuple


class Classification(str, Enum):
    """Segment classification types (IC/OOC/MIXED)"""
    IN_CHARACTER = "IC"
    OUT_OF_CHARACTER = "OOC"
    MIXED = "MIXED"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Get human-readable display name"""
        names = {
            Classification.IN_CHARACTER: "In-Character",
            Classification.OUT_OF_CHARACTER: "Out-of-Character",
            Classification.MIXED: "Mixed",
        }
        return names[self]


class ProcessingStatus(str, Enum):
    """Status of a processing stage or session"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        return self.value

    def is_terminal(self) -> bool:
        """Check if this is a terminal status"""
        return self in (
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.SKIPPED
        )


class PipelineStage(str, Enum):
    """Pipeline processing stages"""
    AUDIO_CONVERTED = "audio_converted"
    AUDIO_CHUNKED = "audio_chunked"
    AUDIO_TRANSCRIBED = "audio_transcribed"
    TRANSCRIPTION_MERGED = "transcription_merged"
    SPEAKER_DIARIZED = "speaker_diarized"
    SEGMENTS_CLASSIFIED = "segments_classified"
    OUTPUTS_GENERATED = "outputs_generated"
    AUDIO_SEGMENTS_EXPORTED = "audio_segments_exported"
    KNOWLEDGE_EXTRACTED = "knowledge_extracted"

    def __str__(self) -> str:
        return self.value

    @property
    def number(self) -> int:
        """Get stage number (1-9)"""
        stages = list(PipelineStage)
        return stages.index(self) + 1

    @property
    def display_name(self) -> str:
        """Get human-readable stage name"""
        names = {
            PipelineStage.AUDIO_CONVERTED: "Audio Conversion",
            PipelineStage.AUDIO_CHUNKED: "Audio Chunking",
            PipelineStage.AUDIO_TRANSCRIBED: "Transcription",
            PipelineStage.TRANSCRIPTION_MERGED: "Transcript Merging",
            PipelineStage.SPEAKER_DIARIZED: "Speaker Diarization",
            PipelineStage.SEGMENTS_CLASSIFIED: "IC/OOC Classification",
            PipelineStage.OUTPUTS_GENERATED: "Output Generation",
            PipelineStage.AUDIO_SEGMENTS_EXPORTED: "Audio Segment Export",
            PipelineStage.KNOWLEDGE_EXTRACTED: "Knowledge Extraction",
        }
        return names[self]


class OutputFormat(str, Enum):
    """Output file format types"""
    FULL = "full"
    IC_ONLY = "ic_only"
    OOC_ONLY = "ooc_only"
    JSON = "json"
    SRT_FULL = "srt_full"
    SRT_IC = "srt_ic"
    SRT_OOC = "srt_ooc"

    def __str__(self) -> str:
        return self.value

    def get_file_extension(self) -> str:
        """Get file extension for this format"""
        if self in (OutputFormat.JSON,):
            return "json"
        elif self.value.startswith("srt_"):
            return "srt"
        else:
            return "txt"


class SpeakerLabel:
    """Constants for speaker labels"""
    UNKNOWN = "UNKNOWN"
    DEFAULT_PREFIX = "SPEAKER_"

    @staticmethod
    def is_generic_label(speaker_id: str) -> bool:
        """Check if speaker ID is a generic label"""
        return speaker_id == SpeakerLabel.UNKNOWN or \
               speaker_id.startswith(SpeakerLabel.DEFAULT_PREFIX)

    @staticmethod
    def format_speaker_number(num: int) -> str:
        """Format speaker number as SPEAKER_XX"""
        return f"{SpeakerLabel.DEFAULT_PREFIX}{num:02d}"


class ConfidenceDefaults:
    """Default confidence values"""
    DEFAULT = 0.5
    HIGH = 0.9
    LOW = 0.3
    MINIMUM = 0.0
    MAXIMUM = 1.0

    @staticmethod
    def clamp(value: float) -> float:
        """Clamp confidence value to valid range"""
        return max(
            ConfidenceDefaults.MINIMUM,
            min(ConfidenceDefaults.MAXIMUM, value)
        )


class TimeConstants:
    """Time-related constants"""
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    MILLISECONDS_PER_SECOND = 1000

    @staticmethod
    def seconds_to_hms(seconds: float) -> Tuple[int, int, int]:
        """Convert seconds to (hours, minutes, seconds)"""
        hours = int(seconds // TimeConstants.SECONDS_PER_HOUR)
        remaining = seconds % TimeConstants.SECONDS_PER_HOUR
        minutes = int(remaining // TimeConstants.SECONDS_PER_MINUTE)
        secs = int(remaining % TimeConstants.SECONDS_PER_MINUTE)
        return hours, minutes, secs

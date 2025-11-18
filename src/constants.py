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


class ClassificationType(str, Enum):
    """Granular classification detail for narrative processing."""
    CHARACTER = "CHARACTER"
    DM_NARRATION = "DM_NARRATION"
    NPC_DIALOGUE = "NPC_DIALOGUE"
    OOC_OTHER = "OOC_OTHER"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        return self.value


class TranscriptFilter(str, Enum):
    """Filter options for transcript formatting."""
    ALL = "all"
    IN_CHARACTER_ONLY = "ic_only"
    OUT_OF_CHARACTER_ONLY = "ooc_only"
    MIXED_ONLY = "mixed_only"

    def __str__(self) -> str:
        """Return the string value for backward compatibility."""
        return self.value

    def get_title(self) -> str:
        """
        Get human-readable title for this filter type.

        Returns:
            Formatted header text for transcripts

        Example:
            >>> TranscriptFilter.IN_CHARACTER_ONLY.get_title()
            'D&D SESSION TRANSCRIPT - IN-CHARACTER ONLY'
        """
        titles = {
            TranscriptFilter.ALL: "D&D SESSION TRANSCRIPT - FILTERED VERSION",
            TranscriptFilter.IN_CHARACTER_ONLY: "D&D SESSION TRANSCRIPT - IN-CHARACTER ONLY",
            TranscriptFilter.OUT_OF_CHARACTER_ONLY: "D&D SESSION TRANSCRIPT - OUT-OF-CHARACTER ONLY",
            TranscriptFilter.MIXED_ONLY: "D&D SESSION TRANSCRIPT - MIXED CONTENT ONLY",
        }
        return titles[self]

    def should_include(self, classification: Classification) -> bool:
        """
        Determine if a segment should be included based on its classification.

        Args:
            classification: The segment's classification (IC/OOC/MIXED)

        Returns:
            True if the segment should be included in this filter type

        Note:
            For backward compatibility:
            - IN_CHARACTER_ONLY excludes only OOC (includes IC and MIXED)
            - OUT_OF_CHARACTER_ONLY excludes only IC (includes OOC and MIXED)
            - MIXED_ONLY includes only MIXED segments
            - ALL includes everything

        Example:
            >>> filter_type = TranscriptFilter.IN_CHARACTER_ONLY
            >>> filter_type.should_include(Classification.IN_CHARACTER)
            True
            >>> filter_type.should_include(Classification.OUT_OF_CHARACTER)
            False
        """
        if self == TranscriptFilter.ALL:
            return True
        elif self == TranscriptFilter.IN_CHARACTER_ONLY:
            # Exclude only OOC, include IC and MIXED (backward compatibility)
            return classification != Classification.OUT_OF_CHARACTER
        elif self == TranscriptFilter.OUT_OF_CHARACTER_ONLY:
            # Exclude only IC, include OOC and MIXED (backward compatibility)
            return classification != Classification.IN_CHARACTER
        elif self == TranscriptFilter.MIXED_ONLY:
            # Only include MIXED segments
            return classification == Classification.MIXED
        raise NotImplementedError(f"Filtering logic for {self} is not implemented.")


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

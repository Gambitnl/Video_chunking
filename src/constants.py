"""Shared constants and enums for the video chunking project."""

from enum import Enum


class Classification(str, Enum):
    """
    Segment classification types for IC/OOC detection.

    Using str enum allows direct string comparison while providing type safety.
    """
    IN_CHARACTER = "IC"
    OUT_OF_CHARACTER = "OOC"
    MIXED = "MIXED"

    def __str__(self) -> str:
        """Return the string value for backward compatibility."""
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

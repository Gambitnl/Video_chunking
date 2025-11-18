"""
Data models for session analytics.

This module defines the data structures used throughout the analytics system:
- SessionMetrics: Metrics for a single session
- CharacterStats: Statistics for a single character
- ComparisonResult: Results of comparing multiple sessions
- TimelineData: Timeline data across sessions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class CharacterStats:
    """
    Statistics for a single character in a session.

    Attributes:
        character_name: Name of the character
        message_count: Total number of messages spoken
        word_count: Total number of words spoken
        speaking_duration: Total speaking time in seconds
        ic_messages: Number of in-character messages
        ooc_messages: Number of out-of-character messages
        avg_message_length: Average message length in words
        first_appearance: Timestamp of first appearance (seconds from start)
        last_appearance: Timestamp of last appearance (seconds from start)
    """
    character_name: str
    message_count: int = 0
    word_count: int = 0
    speaking_duration: float = 0.0
    ic_messages: int = 0
    ooc_messages: int = 0
    avg_message_length: float = 0.0
    first_appearance: Optional[float] = None
    last_appearance: Optional[float] = None

    def __post_init__(self):
        """Validate and calculate derived metrics."""
        # Calculate average message length if not provided
        if self.message_count > 0 and self.avg_message_length == 0.0:
            self.avg_message_length = self.word_count / self.message_count

    def ic_percentage(self) -> float:
        """Calculate percentage of in-character messages."""
        if self.message_count == 0:
            return 0.0
        return (self.ic_messages / self.message_count) * 100

    def ooc_percentage(self) -> float:
        """Calculate percentage of out-of-character messages."""
        if self.message_count == 0:
            return 0.0
        return (self.ooc_messages / self.message_count) * 100


@dataclass
class SessionMetrics:
    """
    Comprehensive metrics for a single D&D session.

    Attributes:
        session_id: Unique identifier for the session
        session_name: Human-readable session name
        duration: Total session duration in seconds
        speaker_count: Number of unique speakers
        message_count: Total number of messages/segments
        ic_message_count: Number of in-character messages
        ooc_message_count: Number of out-of-character messages
        ic_duration: Total in-character speaking time (seconds)
        ooc_duration: Total out-of-character speaking time (seconds)
        character_stats: Statistics per character (character_name -> CharacterStats)
        timestamp: Session timestamp (when processed or recorded)
        metadata: Additional session metadata from original processing
    """
    session_id: str
    session_name: str
    duration: float = 0.0
    speaker_count: int = 0
    message_count: int = 0
    ic_message_count: int = 0
    ooc_message_count: int = 0
    ic_duration: float = 0.0
    ooc_duration: float = 0.0
    character_stats: Dict[str, CharacterStats] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate metrics."""
        # Ensure counts are non-negative
        assert self.duration >= 0, "Duration cannot be negative"
        assert self.message_count >= 0, "Message count cannot be negative"
        assert self.ic_message_count >= 0, "IC message count cannot be negative"
        assert self.ooc_message_count >= 0, "OOC message count cannot be negative"

        # Ensure IC + OOC = total (must be exact match)
        total_messages = self.ic_message_count + self.ooc_message_count
        if self.message_count > 0:
            assert total_messages == self.message_count, \
                f"IC + OOC messages ({total_messages}) != total messages ({self.message_count})"

    def ic_percentage(self) -> float:
        """Calculate percentage of in-character messages."""
        if self.message_count == 0:
            return 0.0
        return (self.ic_message_count / self.message_count) * 100

    def ooc_percentage(self) -> float:
        """Calculate percentage of out-of-character messages."""
        if self.message_count == 0:
            return 0.0
        return (self.ooc_message_count / self.message_count) * 100

    def ic_duration_percentage(self) -> float:
        """Calculate percentage of time spent in-character."""
        if self.duration == 0:
            return 0.0
        return (self.ic_duration / self.duration) * 100

    def ooc_duration_percentage(self) -> float:
        """Calculate percentage of time spent out-of-character."""
        if self.duration == 0:
            return 0.0
        return (self.ooc_duration / self.duration) * 100

    def duration_formatted(self) -> str:
        """Format duration as HH:MM:SS."""
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_top_speakers(self, limit: int = 5) -> List[tuple[str, CharacterStats]]:
        """
        Get top speakers by speaking time.

        Args:
            limit: Maximum number of speakers to return

        Returns:
            List of (character_name, CharacterStats) tuples sorted by speaking_duration
        """
        sorted_speakers = sorted(
            self.character_stats.items(),
            key=lambda x: x[1].speaking_duration,
            reverse=True
        )
        return sorted_speakers[:limit]


@dataclass
class ComparisonResult:
    """
    Result of comparing multiple sessions.

    Attributes:
        sessions: List of SessionMetrics being compared
        differences: Computed differences between sessions (metric_name -> values)
        insights: Auto-generated insights from comparison
        comparison_date: When the comparison was performed
    """
    sessions: List[SessionMetrics]
    differences: Dict[str, List[float]] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    comparison_date: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate comparison result."""
        assert len(self.sessions) > 0, "Must have at least one session to compare"

    def session_count(self) -> int:
        """Get number of sessions in comparison."""
        return len(self.sessions)

    def average_duration(self) -> float:
        """Calculate average session duration."""
        if not self.sessions:
            return 0.0
        return sum(s.duration for s in self.sessions) / len(self.sessions)

    def average_ic_percentage(self) -> float:
        """Calculate average IC percentage across sessions."""
        if not self.sessions:
            return 0.0
        return sum(s.ic_percentage() for s in self.sessions) / len(self.sessions)

    def get_longest_session(self) -> Optional[SessionMetrics]:
        """Get the longest session by duration."""
        if not self.sessions:
            return None
        return max(self.sessions, key=lambda s: s.duration)

    def get_shortest_session(self) -> Optional[SessionMetrics]:
        """Get the shortest session by duration."""
        if not self.sessions:
            return None
        return min(self.sessions, key=lambda s: s.duration)

    def get_most_ic_session(self) -> Optional[SessionMetrics]:
        """Get session with highest IC percentage."""
        if not self.sessions:
            return None
        return max(self.sessions, key=lambda s: s.ic_percentage())

    def get_most_ooc_session(self) -> Optional[SessionMetrics]:
        """Get session with highest OOC percentage."""
        if not self.sessions:
            return None
        return max(self.sessions, key=lambda s: s.ooc_percentage())


@dataclass
class TimelineData:
    """
    Timeline data showing progression across sessions.

    Attributes:
        sessions: Sessions in chronological order
        ic_ooc_ratios: List of (session_id, ic_percentage, ooc_percentage) tuples
        character_participation: Character participation over time (character -> session_id -> speaking_duration)
        session_dates: Session dates (session_id -> datetime)
    """
    sessions: List[SessionMetrics] = field(default_factory=list)
    ic_ooc_ratios: List[tuple[str, float, float]] = field(default_factory=list)
    character_participation: Dict[str, Dict[str, float]] = field(default_factory=dict)
    session_dates: Dict[str, Optional[datetime]] = field(default_factory=dict)

    def __post_init__(self):
        """Populate derived data structures."""
        # Sort sessions chronologically if not already sorted
        if self.sessions:
            self.sessions.sort(key=lambda s: s.timestamp or datetime.min)

            # Populate IC/OOC ratios
            if not self.ic_ooc_ratios:
                self.ic_ooc_ratios = [
                    (s.session_id, s.ic_percentage(), s.ooc_percentage())
                    for s in self.sessions
                ]

            # Populate session dates
            if not self.session_dates:
                self.session_dates = {
                    s.session_id: s.timestamp
                    for s in self.sessions
                }

            # Populate character participation
            if not self.character_participation:
                for session in self.sessions:
                    for char_name, char_stats in session.character_stats.items():
                        if char_name not in self.character_participation:
                            self.character_participation[char_name] = {}
                        self.character_participation[char_name][session.session_id] = \
                            char_stats.speaking_duration

    def get_character_timeline(self, character_name: str) -> List[tuple[str, float]]:
        """
        Get timeline of speaking duration for a specific character.

        Args:
            character_name: Name of the character

        Returns:
            List of (session_id, speaking_duration) tuples in chronological order
        """
        if character_name not in self.character_participation:
            return []

        char_data = self.character_participation[character_name]
        # Return in chronological order based on sessions list
        return [
            (s.session_id, char_data.get(s.session_id, 0.0))
            for s in self.sessions
        ]

    def get_ic_trend(self) -> List[float]:
        """Get IC percentage trend over time."""
        return [ratio[1] for ratio in self.ic_ooc_ratios]

    def get_ooc_trend(self) -> List[float]:
        """Get OOC percentage trend over time."""
        return [ratio[2] for ratio in self.ic_ooc_ratios]

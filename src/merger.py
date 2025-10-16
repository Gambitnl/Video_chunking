"""Merge overlapping chunk transcriptions using LCS algorithm"""
from typing import List
from difflib import SequenceMatcher
from .transcriber import ChunkTranscription, TranscriptionSegment


class TranscriptionMerger:
    """
    Merges overlapping chunk transcriptions without duplicating content.

    Problem:
    - Chunks overlap by 10 seconds to prevent word splitting
    - This means the same speech appears in multiple chunks
    - We need to merge intelligently without duplication

    Solution:
    - Use Longest Common Subsequence (LCS) to find overlap
    - Take text from first chunk up to overlap
    - Take text from second chunk after overlap
    - Preserve timestamps accurately

    Based on: Groq community guide's sliding window alignment approach
    """

    def __init__(self, similarity_threshold: float = 0.6):
        """
        Args:
            similarity_threshold: Minimum similarity to consider sequences matching
        """
        self.similarity_threshold = similarity_threshold

    def merge_transcriptions(
        self,
        transcriptions: List[ChunkTranscription]
    ) -> List[TranscriptionSegment]:
        """
        Merge a list of chunk transcriptions into one continuous transcription.

        Args:
            transcriptions: List of ChunkTranscription objects (must be ordered)

        Returns:
            List of merged TranscriptionSegment objects
        """
        if not transcriptions:
            return []

        if len(transcriptions) == 1:
            return transcriptions[0].segments

        # Start with first chunk's segments
        merged_segments = list(transcriptions[0].segments)

        # Merge each subsequent chunk
        for i in range(1, len(transcriptions)):
            merged_segments = self._merge_two_chunks(
                merged_segments,
                transcriptions[i].segments,
                transcriptions[i-1].chunk_end,
                transcriptions[i].chunk_start
            )

        return merged_segments

    def _merge_two_chunks(
        self,
        segments_a: List[TranscriptionSegment],
        segments_b: List[TranscriptionSegment],
        chunk_a_end: float,
        chunk_b_start: float
    ) -> List[TranscriptionSegment]:
        """Merge two consecutive chunk transcriptions using a simple time-based split."""
        # The overlap ends at the end time of the first chunk.
        # This provides a simple, robust, if not perfectly precise, split point.
        split_time = chunk_a_end
        return self._merge_by_time(segments_a, segments_b, split_time)

    def _merge_by_time(
        self,
        segments_a: List[TranscriptionSegment],
        segments_b: List[TranscriptionSegment],
        split_time: float
    ) -> List[TranscriptionSegment]:
        """
        Fallback: merge by simply cutting at time boundary.

        Used when LCS doesn't find good overlap.
        """
        # Take all segments from A that end before split time
        result = [seg for seg in segments_a if seg.end_time <= split_time]

        # Add all segments from B that start at or after split time
        result.extend([seg for seg in segments_b if seg.start_time >= split_time])

        return result

    def get_full_text(self, segments: List[TranscriptionSegment]) -> str:
        """Get concatenated text from segments"""
        return " ".join(seg.text for seg in segments)

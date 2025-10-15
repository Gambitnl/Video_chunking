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
        """
        Merge two consecutive chunk transcriptions.

        Strategy:
        1. Find overlap region (where chunks overlap in time)
        2. Extract text from overlap regions
        3. Find longest common subsequence
        4. Split at the match point
        5. Take non-overlapping part from A + all of B after overlap

        Args:
            segments_a: Segments from first chunk
            segments_b: Segments from second chunk
            chunk_a_end: End time of first chunk
            chunk_b_start: Start time of second chunk (with overlap)

        Returns:
            Merged segments
        """
        # Calculate overlap region
        overlap_start = chunk_b_start
        overlap_end = chunk_a_end

        # Find segments in overlap region
        overlap_segments_a = [
            seg for seg in segments_a
            if seg.end_time > overlap_start
        ]
        overlap_segments_b = [
            seg for seg in segments_b
            if seg.start_time < overlap_end
        ]

        if not overlap_segments_a or not overlap_segments_b:
            # No overlap detected, just concatenate
            return segments_a + segments_b

        # Get text from overlap regions
        text_a = " ".join(seg.text for seg in overlap_segments_a)
        text_b = " ".join(seg.text for seg in overlap_segments_b)

        # Find longest common substring using SequenceMatcher
        matcher = SequenceMatcher(None, text_a, text_b)
        match = matcher.find_longest_match(0, len(text_a), 0, len(text_b))

        if match.size == 0 or (match.size / max(len(text_a), len(text_b))) < self.similarity_threshold:
            # No significant overlap found, use time-based splitting
            return self._merge_by_time(segments_a, segments_b, overlap_end)

        # We found a good match - use the match point to split
        # Take all of A up to the match, then all of B from the match onward
        overlap_text = text_a[match.a:match.a + match.size]

        # Find where this match ends in segments_a
        char_count = 0
        split_index_a = len(segments_a)

        for i, seg in enumerate(segments_a):
            char_count += len(seg.text) + 1  # +1 for space
            if char_count >= match.a + match.size:
                split_index_a = i + 1
                break

        # Find where this match starts in segments_b
        char_count = 0
        split_index_b = 0

        for i, seg in enumerate(segments_b):
            if char_count >= match.b:
                split_index_b = i
                break
            char_count += len(seg.text) + 1

        # Merge: A up to split point + B from split point onward
        result = segments_a[:split_index_a] + segments_b[split_index_b:]

        return result

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

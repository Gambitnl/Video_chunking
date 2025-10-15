import pytest
from src.merger import TranscriptionMerger
from src.transcriber import ChunkTranscription, TranscriptionSegment

def test_merge_simple_overlap():
    """Test that two simple overlapping segments are merged correctly."""
    # Arrange
    merger = TranscriptionMerger()

    # Chunk 1: "Hello world this is a test"
    chunk1_segments = [
        TranscriptionSegment(text="Hello world", start_time=0.0, end_time=1.0),
        TranscriptionSegment(text="this is a test", start_time=1.0, end_time=2.0),
    ]
    transcription1 = ChunkTranscription(
        chunk_index=0, chunk_start=0.0, chunk_end=10.0, segments=chunk1_segments, language="en"
    )

    # Chunk 2: "a test of the merger"
    # Overlaps with "a test"
    chunk2_segments = [
        TranscriptionSegment(text="a test of the merger", start_time=8.0, end_time=10.0),
    ]
    transcription2 = ChunkTranscription(
        chunk_index=1, chunk_start=8.0, chunk_end=18.0, segments=chunk2_segments, language="en"
    )

    # Act
    merged = merger.merge_transcriptions([transcription1, transcription2])

    # Assert
    full_text = " ".join(seg.text for seg in merged)

    # The merged text should not contain the duplicated "a test"
    assert full_text == "Hello world this is a test of the merger"

import sys
import types
from dataclasses import dataclass
from typing import List, Optional

fake_torch = types.ModuleType("torch")
fake_torch.hub = types.SimpleNamespace(load=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("torch hub not available")))
sys.modules.setdefault("torch", fake_torch)

from src.merger import TranscriptionMerger


@dataclass
class TranscriptionSegment:
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None
    words: Optional[List] = None


@dataclass
class ChunkTranscription:
    chunk_index: int
    chunk_start: float
    chunk_end: float
    segments: List[TranscriptionSegment]
    language: str


def build_segment(text: str, start: float, end: float) -> TranscriptionSegment:
    return TranscriptionSegment(
        text=text,
        start_time=start,
        end_time=end,
        confidence=0.9,
        words=None
    )


def test_merge_transcriptions_removes_overlap():
    merger = TranscriptionMerger()

    chunk_a = ChunkTranscription(
        chunk_index=0,
        chunk_start=0.0,
        chunk_end=5.0,
        segments=[
            build_segment("Hallo avonturier", 0.0, 2.5),
            build_segment("Welkom in de herberg", 2.5, 5.0)
        ],
        language="nl"
    )

    chunk_b = ChunkTranscription(
        chunk_index=1,
        chunk_start=4.0,
        chunk_end=8.0,
        segments=[
            build_segment("Welkom in de herberg", 4.0, 5.5),
            build_segment("Wat wil je drinken?", 5.5, 7.0)
        ],
        language="nl"
    )

    merged = merger.merge_transcriptions([chunk_a, chunk_b])
    merged_text = " ".join(seg.text for seg in merged)

    assert len(merged) == 3
    assert "Hallo avonturier" in merged_text
    assert merged_text.count("Welkom in de herberg") == 1
    assert merged[-1].text == "Wat wil je drinken?"

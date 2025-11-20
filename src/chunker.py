"""Audio chunking with VAD and overlap strategy"""
import torch
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from .config import Config
from .audio_processor import AudioProcessor
from .logger import get_logger


@dataclass
class AudioChunk:
    """Represents a chunk of audio with metadata"""
    audio: np.ndarray
    start_time: float  # seconds
    end_time: float
    sample_rate: int
    chunk_index: int

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> dict:
        """Converts the AudioChunk metadata to a dictionary for serialization."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "sample_rate": self.sample_rate,
            "chunk_index": self.chunk_index,
        }

    @classmethod
    def from_dict(cls, data: dict, audio_data: Optional[np.ndarray] = None) -> "AudioChunk":
        """Creates an AudioChunk from a dictionary, optionally including audio data."""
        return cls(
            audio=audio_data if audio_data is not None else np.array([]), # Placeholder if audio not provided
            start_time=data["start_time"],
            end_time=data["end_time"],
            sample_rate=data["sample_rate"],
            chunk_index=data["chunk_index"],
        )


class HybridChunker:
    """
    Hybrid chunking strategy combining VAD and fixed-length chunking.

    Design Philosophy:
    - Primary: Use Voice Activity Detection to find natural pauses
    - Fallback: If no pause found, chunk at max_length
    - Overlap: Always overlap chunks to prevent word splitting
    - Context preservation: Longer chunks = better transcription context

    Based on research showing:
    - 10-min chunks with 10s overlap = only 1.67% overhead
    - Whisper handles long chunks better than we thought
    - Natural pauses create better semantic boundaries
    """

    def __init__(
        self,
        max_chunk_length: int = None,
        overlap_length: int = None,
        vad_threshold: float = 0.5
    ):
        self.max_chunk_length = max_chunk_length or Config.CHUNK_LENGTH_SECONDS
        self.overlap_length = overlap_length or Config.CHUNK_OVERLAP_SECONDS
        self.vad_threshold = vad_threshold
        self.audio_processor = AudioProcessor()
        self.logger = get_logger("chunker")

        # Load Silero VAD model
        self.vad_model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
        self.get_speech_timestamps = utils[0]

    def chunk_audio(self, audio_path: Path, progress_callback: Optional[Callable[[AudioChunk, float], None]] = None) -> List[AudioChunk]:
        """
        Chunk audio file into overlapping segments.

        Args:
            audio_path: Path to WAV file (must be 16kHz mono)

        Returns:
            List of AudioChunk objects

        Algorithm:
        1. Load entire audio file
        2. Detect speech segments with VAD
        3. Create chunks at natural pauses when possible
        4. Fall back to fixed-length if no pause found
        5. Add overlap between all chunks
        """
        # Load audio
        audio, sr = self.audio_processor.load_audio(audio_path)
        self.logger.info("Chunking audio %s (duration~%.1f sec, sample_rate=%d)", audio_path, len(audio) / sr, sr)

        # Normalize for better VAD performance
        audio = self.audio_processor.normalize_audio(audio)

        # Get speech timestamps from VAD
        speech_timestamps = self.get_speech_timestamps(
            torch.from_numpy(audio),
            self.vad_model,
            sampling_rate=sr,
            threshold=self.vad_threshold,
            min_speech_duration_ms=250,
            min_silence_duration_ms=500
        )

        # Convert to seconds
        speech_segments = [
            (ts['start'] / sr, ts['end'] / sr)
            for ts in speech_timestamps
        ]
        self.logger.debug("Detected %d speech regions via VAD", len(speech_segments))

        # Create chunks
        chunks = self._create_chunks_with_pauses(
            audio, sr, speech_segments, progress_callback=progress_callback
        )
        self.logger.info("Created %d audio chunks", len(chunks))

        return chunks

    def _create_chunks_with_pauses(
        self,
        audio: np.ndarray,
        sr: int,
        speech_segments: List[Tuple[float, float]],
        progress_callback: Optional[Callable[[AudioChunk, float], None]] = None
    ) -> List[AudioChunk]:
        """
        Create chunks using speech pauses as boundaries.

        Strategy:
        - Try to chunk at silence between speech segments
        - Don't exceed max_chunk_length
        - Always include overlap_length from previous chunk
        """
        chunks = []
        total_duration = len(audio) / sr

        chunk_start = 0.0
        chunk_index = 0

        while chunk_start < total_duration:
            # Calculate ideal end time (without overlap consideration)
            ideal_end = chunk_start + self.max_chunk_length

            if ideal_end >= total_duration:
                # Last chunk - take everything remaining
                chunk_end = total_duration
            else:
                # Find the best pause near the ideal end point
                chunk_end = self._find_best_pause(
                    speech_segments,
                    ideal_end,
                    chunk_start
                )

            # Extract audio for this chunk
            start_sample = int(chunk_start * sr)
            end_sample = int(chunk_end * sr)
            chunk_audio = audio[start_sample:end_sample]

            chunks.append(AudioChunk(
                audio=chunk_audio,
                start_time=chunk_start,
                end_time=chunk_end,
                sample_rate=sr,
                chunk_index=chunk_index
            ))
            self.logger.debug(
                "Chunk %d | start=%.2fs end=%.2fs duration=%.2fs",
                chunk_index, chunk_start, chunk_end, chunk_end - chunk_start
            )

            if progress_callback:
                try:
                    progress_callback(chunks[-1], total_duration)
                except Exception as exc:
                    self.logger.warning("Chunk progress callback failed: %s", exc)

            # Move to next chunk with overlap
            # If this is the last chunk, we're done
            if chunk_end >= total_duration:
                break

            # Next chunk starts at (current_end - overlap)
            chunk_start = chunk_end - self.overlap_length
            chunk_index += 1

        return chunks

    def _find_best_pause(
        self,
        speech_segments: List[Tuple[float, float]],
        ideal_end: float,
        chunk_start: float
    ) -> float:
        """
        Find the best silence gap near the ideal end time.

        Logic:
        - Look for gaps between speech segments
        - Prefer gaps close to ideal_end
        - If no good gap found within tolerance, just use ideal_end
        """
        # Search window: ±60 seconds from ideal end to consider nearby pauses
        search_window = 60.0
        best_gap_end = ideal_end
        best_gap_score = float('inf')

        # Find gaps (silences) between speech segments
        for i in range(len(speech_segments) - 1):
            gap_start = speech_segments[i][1]  # End of current segment
            gap_end = speech_segments[i + 1][0]  # Start of next segment

            # Gap must be after chunk_start and within search window
            if gap_start < chunk_start:
                continue

            if abs(gap_end - ideal_end) > search_window:
                continue

            # Score: prefer gaps closer to ideal_end and wider gaps
            distance_score = abs(gap_end - ideal_end)
            gap_width = gap_end - gap_start
            score = distance_score - (gap_width * 2)  # Reward wider gaps

            if score < best_gap_score:
                best_gap_score = score
                best_gap_end = gap_end

        return best_gap_end

    def save_chunk(self, chunk: AudioChunk, output_path: Path):
        """Save a chunk to disk"""
        self.audio_processor.save_audio(
            chunk.audio,
            output_path,
            chunk.sample_rate
        )

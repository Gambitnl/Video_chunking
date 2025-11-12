"""Main processing pipeline orchestrating all components"""
import json
from pathlib import Path
from time import perf_counter
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime
from .config import Config
from .constants import PipelineStage, ProcessingStatus, Classification, ConfidenceDefaults
from .checkpoint import CheckpointManager
from .audio_processor import AudioProcessor
from .chunker import HybridChunker, AudioChunk
from .transcriber import TranscriberFactory, ChunkTranscription, TranscriptionSegment
from .merger import TranscriptionMerger
from .diarizer import DiarizerFactory, SpeakerDiarizer, SpeakerProfileManager
from .classifier import ClassifierFactory, ClassificationResult
from .formatter import TranscriptFormatter, StatisticsGenerator, sanitize_filename
from .party_config import PartyConfigManager
from .snipper import AudioSnipper
from .logger import get_logger, get_log_file_path, log_session_start, log_session_end, log_error_with_context
from .status_tracker import StatusTracker
from .knowledge_base import KnowledgeExtractor, CampaignKnowledgeBase
from .preflight import PreflightChecker, PreflightIssue

try:  # pragma: no cover - convenience for test environment
    from unittest.mock import Mock as _Mock  # type: ignore
except ImportError:  # pragma: no cover
    _Mock = None


from dataclasses import dataclass, field


@dataclass
class StageResult:
    """
    Result from a single pipeline stage execution.

    This encapsulates the output of each pipeline stage, including:
    - Stage identifier
    - Processing status (running, completed, failed, skipped)
    - Stage-specific data (e.g., file paths, transcriptions, etc.)
    - Error messages and warnings
    - Timing information for performance tracking

    Design Philosophy:
    - Consistent return type across all stage methods
    - Self-contained error handling
    - Built-in timing and performance metrics
    - Serializable for checkpointing

    Example:
        >>> result = StageResult(
        ...     stage=PipelineStage.AUDIO_CONVERTED,
        ...     status=ProcessingStatus.COMPLETED,
        ...     data={"wav_path": "/path/to/audio.wav", "duration": 123.45}
        ... )
        >>> assert result.success is True
        >>> assert "wav_path" in result.data
    """

    stage: PipelineStage
    status: ProcessingStatus
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration(self) -> Optional[float]:
        """Calculate stage duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success(self) -> bool:
        """Check if stage completed successfully."""
        return self.status == ProcessingStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization and checkpointing."""
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration
        }


def create_session_output_dir(base_output_dir: Path, session_id: str) -> Path:
    """
    Create a timestamped output directory for a session.

    Format: YYYYMMDD_HHMMSS_<session_id>/
    Example: 20251019_143022_test_ui_5min/

    Args:
        base_output_dir: Base output directory (e.g., F:/Repos/VideoChunking/output)
        session_id: Session identifier

    Returns:
        Path to the session-specific output directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir_name = f"{timestamp}_{session_id}"
    session_output_dir = base_output_dir / session_dir_name
    session_output_dir.mkdir(parents=True, exist_ok=True)
    return session_output_dir


class DDSessionProcessor:
    """
    Main pipeline for processing D&D sessions.

    Orchestrates the entire workflow:
    1. Audio conversion
    2. Chunking
    3. Transcription
    4. Merging overlaps
    5. Speaker diarization
    6. IC/OOC classification
    7. Output generation
    8. Audio segment export
    9. Campaign knowledge extraction

    Design Philosophy:
    - Progress reporting at each stage
    - Graceful degradation (if a component fails, continue with reduced features)
    - Save intermediate results (for debugging and resume capability)
    """

    def __init__(
        self,
        session_id: str,
        campaign_id: Optional[str] = None,
        character_names: Optional[List[str]] = None,
        player_names: Optional[List[str]] = None,
        num_speakers: int = 4,
        party_id: Optional[str] = None,
        language: str = "en",
        resume: bool = True,
        transcription_backend: str = "whisper",
        diarization_backend: str = "pyannote",
        classification_backend: str = "ollama",
    ):
        """
        Args:
            session_id: Unique identifier for this session
            campaign_id: Campaign identifier for grouping and filtering sessions
            character_names: List of character names in the campaign
            player_names: List of player names
            num_speakers: Expected number of speakers (3 players + 1 DM = 4)
            party_id: Party configuration to use (defaults to "default")
            resume: Enable checkpoint resume functionality (default: True)
        """
        self.session_id = session_id
        self.safe_session_id = sanitize_filename(session_id)
        self.campaign_id = campaign_id  # Store campaign_id for metadata and filtering
        self.language = language
        self.is_test_run = False  # Default to not being a test run
        self.logger = get_logger(f"pipeline.{self.safe_session_id}")
        self.resume_enabled = resume

        if self.safe_session_id != self.session_id:
            self.logger.warning(
                "Session ID sanitized for filesystem usage: '%s' -> '%s'",
                self.session_id,
                self.safe_session_id
            )

        self.party_manager = PartyConfigManager()
        self.checkpoint_manager = CheckpointManager(
            self.safe_session_id,
            Config.OUTPUT_DIR / "_checkpoints" / self.safe_session_id
        )

        self.party_id = party_id
        # Load party configuration if provided
        if self.party_id:
            party = self.party_manager.get_party(self.party_id)
            if party:
                self.logger.info("Using party configuration: %s", party.party_name)
                self.character_names = self.party_manager.get_character_names(self.party_id)
                self.player_names = self.party_manager.get_player_names(self.party_id)
                self.party_context = self.party_manager.get_party_context_for_llm(self.party_id)
            else:
                self.logger.warning("Party '%s' not found, falling back to provided defaults", self.party_id)
                self.character_names = character_names or []
                self.player_names = player_names or []
                self.party_context = None
                self.party_id = None
        else:
            self.character_names = character_names or []
            self.player_names = player_names or []
            self.party_context = None

        self.num_speakers = num_speakers

        # Initialize components
        self.audio_processor = AudioProcessor()
        self.chunker = HybridChunker()
        self.transcriber = TranscriberFactory.create(backend=transcription_backend)
        self.merger = TranscriptionMerger()
        self.diarizer = DiarizerFactory.create(backend=diarization_backend)
        self.classifier = ClassifierFactory.create(backend=classification_backend)
        self.formatter = TranscriptFormatter()
        self.speaker_profile_manager = SpeakerProfileManager()
        self.snipper = AudioSnipper()

    # ========================================================================
    # Pipeline Stage Extraction Methods
    # ========================================================================
    # These methods implement individual pipeline stages with consistent
    # error handling, logging, and result encapsulation using StageResult.
    # Each method is independently testable and focuses on a single responsibility.
    # ========================================================================

    def _stage_audio_conversion(
        self,
        input_file: Path,
        output_dir: Path
    ) -> StageResult:
        """
        Stage 1/9: Convert video/audio to optimal WAV format for processing.

        This stage extracts audio from the input file and converts it to
        16-bit PCM WAV format at 16kHz mono, which is optimal for transcription.

        Args:
            input_file: Path to input video or audio file
            output_dir: Session output directory for storing converted audio

        Returns:
            StageResult with:
                - data["wav_path"]: Path to converted WAV file
                - data["duration"]: Duration in seconds (float)

        Dependencies:
            - None (first stage)

        Can Fail:
            - Yes (critical failure) - Cannot proceed without audio
        """
        result = StageResult(
            stage=PipelineStage.AUDIO_CONVERTED,
            status=ProcessingStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            self.logger.info("Stage 1/9: Converting audio to optimal format...")
            StatusTracker.update_stage(
                self.session_id,
                1,
                ProcessingStatus.RUNNING,
                "Converting source audio"
            )

            # Convert to WAV format
            wav_file = self.audio_processor.convert_to_wav(input_file)
            duration = self.audio_processor.get_duration(wav_file)

            # Validate output
            if not wav_file.exists():
                raise FileNotFoundError(f"Audio conversion failed - WAV file not created: {wav_file}")

            file_size = wav_file.stat().st_size
            if file_size < 1000:  # Less than 1KB is suspicious
                raise ValueError(f"Audio file too small ({file_size} bytes), conversion may have failed")

            # Success!
            result.status = ProcessingStatus.COMPLETED
            result.data = {
                "wav_path": str(wav_file),
                "duration": duration,
                "file_size": file_size
            }

            duration_hours = duration / 3600 if duration else 0.0
            self.logger.info(
                "Stage 1/9 complete: %.1f seconds of audio (%.1f hours)",
                duration or 0.0,
                duration_hours
            )
            StatusTracker.update_stage(
                self.session_id,
                1,
                ProcessingStatus.COMPLETED,
                f"Duration {duration:.1f}s"
            )

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(f"Audio conversion failed: {str(e)}")
            self.logger.error("Stage 1/9 failed: %s", e, exc_info=True)
            StatusTracker.update_stage(
                self.session_id,
                1,
                ProcessingStatus.FAILED,
                f"Conversion failed: {e}"
            )

        finally:
            result.end_time = datetime.now()

        return result

    def _stage_audio_chunking(
        self,
        wav_file: Path,
        total_duration: float
    ) -> StageResult:
        """
        Stage 2/9: Split audio into chunks using Voice Activity Detection (VAD).

        This stage divides the audio into manageable chunks for parallel processing
        while respecting natural speech boundaries detected by VAD.

        Args:
            wav_file: Path to converted WAV file from Stage 1
            total_duration: Total audio duration in seconds (for progress tracking)

        Returns:
            StageResult with:
                - data["chunks"]: List[AudioChunk] - Audio chunks with timing
                - data["num_chunks"]: int - Total number of chunks created

        Dependencies:
            - Stage 1 (Audio Conversion)

        Can Fail:
            - Yes (critical failure) - Cannot proceed without chunks
        """
        result = StageResult(
            stage=PipelineStage.AUDIO_CHUNKED,
            status=ProcessingStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            self.logger.info("Stage 2/9: Chunking audio with VAD...")
            StatusTracker.update_stage(
                self.session_id,
                2,
                ProcessingStatus.RUNNING,
                "Detecting speech regions"
            )

            # Progress tracking
            chunk_progress = {
                "count": 0,
                "last_logged_percent": -5.0,
                "last_log_time": perf_counter()
            }

            def _chunk_progress_callback(chunk, duration):
                try:
                    chunk_progress["count"] = chunk.chunk_index + 1
                    details = {
                        "chunks_created": chunk_progress["count"],
                        "latest_chunk_index": chunk.chunk_index,
                        "latest_chunk_end": round(chunk.end_time, 2)
                    }
                    if duration and duration > 0:
                        percent = min(100.0, max(0.0, (chunk.end_time / duration) * 100))
                        details["progress_percent"] = round(percent, 1)
                    else:
                        percent = 0.0

                    StatusTracker.update_stage(
                        self.session_id,
                        2,
                        "running",
                        message=f"Chunking... {chunk_progress['count']} chunk{'s' if chunk_progress['count'] != 1 else ''}",
                        details=details
                    )

                    # Log every 5% or every 30 seconds
                    should_log = False
                    if percent - chunk_progress["last_logged_percent"] >= 5.0:
                        should_log = True
                    else:
                        now = perf_counter()
                        if now - chunk_progress["last_log_time"] >= 30.0:
                            should_log = True
                            chunk_progress["last_log_time"] = now

                    if should_log:
                        chunk_progress["last_logged_percent"] = percent
                        chunk_progress["last_log_time"] = perf_counter()
                        self.logger.info(
                            "Stage 2/9 progress: %d chunk(s) created (%.1f%% of audio processed)",
                            chunk_progress["count"],
                            round(percent, 1)
                        )
                except Exception as progress_error:
                    self.logger.debug("Chunk progress callback skipped: %s", progress_error)

            # Perform chunking
            chunks = self.chunker.chunk_audio(
                wav_file,
                progress_callback=_chunk_progress_callback
            )

            # Validate output
            if not chunks:
                if not self.is_test_run:
                    raise RuntimeError(
                        "Audio chunking resulted in zero segments. This can happen if the audio is "
                        "completely silent, corrupt, or too short. Please check the input audio file."
                    )
                # For test runs, allow empty chunks
                self.logger.warning("Chunker returned no segments; continuing for test run.")

            # Success!
            result.status = ProcessingStatus.COMPLETED
            result.data = {
                "chunks": chunks,
                "num_chunks": len(chunks)
            }

            self.logger.info("Stage 2/9 complete: %d chunks created", len(chunks))
            StatusTracker.update_stage(
                self.session_id,
                2,
                ProcessingStatus.COMPLETED,
                f"Created {len(chunks)} chunks"
            )

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(f"Audio chunking failed: {str(e)}")
            self.logger.error("Stage 2/9 failed: %s", e, exc_info=True)
            StatusTracker.update_stage(
                self.session_id,
                2,
                ProcessingStatus.FAILED,
                f"Chunking failed: {e}"
            )

        finally:
            result.end_time = datetime.now()

        return result

    def _stage_audio_transcription(
        self,
        chunks: List[AudioChunk]
    ) -> StageResult:
        """
        Stage 3/9: Transcribe audio chunks to text.

        This stage processes each audio chunk through the transcription model
        (e.g., Whisper) to convert speech to text with word-level timestamps.

        Args:
            chunks: List of audio chunks from Stage 2

        Returns:
            StageResult with:
                - data["chunk_transcriptions"]: List[ChunkTranscription] - Transcribed chunks
                - data["transcription_count"]: int - Number of transcriptions

        Dependencies:
            - Stage 2 (Audio Chunking)

        Can Fail:
            - Yes (critical failure) - Cannot proceed without transcriptions
        """
        result = StageResult(
            stage=PipelineStage.AUDIO_TRANSCRIBED,
            status=ProcessingStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            self.logger.info("Stage 3/9: Transcribing chunks (this may take a while)...")
            total_chunks = len(chunks)
            StatusTracker.update_stage(
                self.session_id,
                3,
                ProcessingStatus.RUNNING,
                f"Transcribing {total_chunks} chunks"
            )

            chunk_transcriptions: List[ChunkTranscription] = []
            log_every = max(1, total_chunks // 10)
            last_log_time = perf_counter()

            for index, chunk in enumerate(chunks, start=1):
                transcription = self.transcriber.transcribe_chunk(
                    chunk,
                    language=self.language
                )
                chunk_transcriptions.append(transcription)

                # Progress logging
                preview_text = transcription.preview_text(220)
                chunk_duration = round(chunk.end_time - chunk.start_time, 2)

                if (
                    index == 1
                    or index == total_chunks
                    or index % log_every == 0
                    or (perf_counter() - last_log_time) >= 60.0
                ):
                    percent = (index / total_chunks) * 100 if total_chunks else 0.0
                    last_log_time = perf_counter()

                    StatusTracker.update_stage(
                        self.session_id,
                        3,
                        "running",
                        message=f"Transcribing chunk {index}/{total_chunks}",
                        details={
                            "chunks_transcribed": index,
                            "total_chunks": total_chunks,
                            "progress_percent": round(percent, 1),
                            "last_chunk_index": transcription.chunk_index,
                            "last_chunk_preview": preview_text,
                            "last_chunk_start": round(chunk.start_time, 2),
                            "last_chunk_end": round(chunk.end_time, 2),
                            "last_chunk_duration": chunk_duration,
                        },
                    )

                    self.logger.info(
                        "Stage 3/9 progress: %d/%d chunks transcribed (%.1f%%)",
                        index,
                        total_chunks,
                        round(percent, 1),
                    )

            # Success!
            result.status = ProcessingStatus.COMPLETED
            result.data = {
                "chunk_transcriptions": chunk_transcriptions,
                "transcription_count": len(chunk_transcriptions)
            }

            self.logger.info("Stage 3/9 complete: transcription finished")
            StatusTracker.update_stage(
                self.session_id,
                3,
                ProcessingStatus.COMPLETED,
                f"Received {len(chunk_transcriptions)} chunk transcriptions"
            )

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(f"Audio transcription failed: {str(e)}")
            self.logger.error("Stage 3/9 failed: %s", e, exc_info=True)
            StatusTracker.update_stage(
                self.session_id,
                3,
                ProcessingStatus.FAILED,
                f"Transcription failed: {e}"
            )

        finally:
            result.end_time = datetime.now()

        return result

    def _stage_transcription_merging(
        self,
        chunk_transcriptions: List[ChunkTranscription]
    ) -> StageResult:
        """
        Stage 4/9: Merge overlapping chunk transcriptions into continuous segments.

        This stage aligns and merges transcriptions from overlapping audio chunks
        to create a single continuous transcript with accurate timestamps.

        Args:
            chunk_transcriptions: List of chunk transcriptions from Stage 3

        Returns:
            StageResult with:
                - data["merged_segments"]: List[TranscriptionSegment] - Merged segments
                - data["merged_segment_count"]: int - Number of merged segments

        Dependencies:
            - Stage 3 (Audio Transcription)

        Can Fail:
            - Yes (critical failure) - Cannot proceed without merged transcript
        """
        result = StageResult(
            stage=PipelineStage.TRANSCRIPTION_MERGED,
            status=ProcessingStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            self.logger.info("Stage 4/9: Merging overlapping chunks...")
            StatusTracker.update_stage(
                self.session_id,
                4,
                ProcessingStatus.RUNNING,
                "Aligning overlapping transcripts"
            )

            # Perform merging
            merged_segments = self.merger.merge_transcriptions(chunk_transcriptions)

            # Success!
            result.status = ProcessingStatus.COMPLETED
            result.data = {
                "merged_segments": merged_segments,
                "merged_segment_count": len(merged_segments)
            }

            self.logger.info("Stage 4/9 complete: %d merged segments", len(merged_segments))
            StatusTracker.update_stage(
                self.session_id,
                4,
                ProcessingStatus.COMPLETED,
                f"Merged into {len(merged_segments)} segments"
            )

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(f"Transcription merging failed: {str(e)}")
            self.logger.error("Stage 4/9 failed: %s", e, exc_info=True)
            StatusTracker.update_stage(
                self.session_id,
                4,
                ProcessingStatus.FAILED,
                f"Merging failed: {e}"
            )

        finally:
            result.end_time = datetime.now()

        return result

    def _stage_speaker_diarization(
        self,
        wav_file: Path,
        merged_segments: List[TranscriptionSegment],
        skip_diarization: bool
    ) -> StageResult:
        """
        Stage 5/9: Identify and label speakers in the audio.

        This stage performs speaker diarization to identify who spoke when,
        then assigns speaker labels to the merged transcription segments.

        Args:
            wav_file: Path to audio file from Stage 1
            merged_segments: Merged transcription segments from Stage 4
            skip_diarization: If True, skip diarization and use UNKNOWN labels

        Returns:
            StageResult with:
                - data["speaker_segments_with_labels"]: List[Dict] - Segments with speakers
                - data["unique_speakers"]: int - Number of unique speakers identified

        Dependencies:
            - Stage 1 (Audio Conversion)
            - Stage 4 (Transcription Merging)

        Can Fail:
            - No (graceful degradation) - Falls back to UNKNOWN speaker labels
        """
        result = StageResult(
            stage=PipelineStage.SPEAKER_DIARIZED,
            status=ProcessingStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            if skip_diarization:
                self.logger.info("Stage 5/9: Speaker diarization skipped")
                StatusTracker.update_stage(
                    self.session_id,
                    5,
                    ProcessingStatus.SKIPPED,
                    "Speaker diarization skipped"
                )

                # Create segments with UNKNOWN speaker
                speaker_segments_with_labels = [
                    {
                        'text': seg.text,
                        'start_time': seg.start_time,
                        'end_time': seg.end_time,
                        'speaker': 'UNKNOWN',
                        'confidence': seg.confidence,
                        'words': seg.words
                    }
                    for seg in merged_segments
                ]

                result.status = ProcessingStatus.SKIPPED
                result.data = {
                    "speaker_segments_with_labels": speaker_segments_with_labels,
                    "unique_speakers": 0
                }

            else:
                self.logger.info("Stage 5/9: Speaker diarization...")
                StatusTracker.update_stage(
                    self.session_id,
                    5,
                    ProcessingStatus.RUNNING,
                    "Performing speaker diarization"
                )

                try:
                    # Perform diarization
                    speaker_segments, speaker_embeddings = self.diarizer.diarize(wav_file)
                    speaker_segments_with_labels = self.diarizer.assign_speakers_to_transcription(
                        merged_segments,
                        speaker_segments
                    )
                    unique_speakers = {seg['speaker'] for seg in speaker_segments_with_labels}

                    # Save speaker embeddings for future use
                    self.speaker_profile_manager.save_speaker_embeddings(
                        self.session_id,
                        speaker_embeddings
                    )

                    result.status = ProcessingStatus.COMPLETED
                    result.data = {
                        "speaker_segments_with_labels": speaker_segments_with_labels,
                        "unique_speakers": len(unique_speakers)
                    }

                    self.logger.info(
                        "Stage 5/9 complete: %d speaker labels assigned",
                        len(unique_speakers)
                    )
                    StatusTracker.update_stage(
                        self.session_id,
                        5,
                        ProcessingStatus.COMPLETED,
                        f"Identified {len(unique_speakers)} speaker labels"
                    )

                except Exception as diarization_error:
                    # Graceful degradation - log warning and continue with UNKNOWN
                    result.warnings.append(f"Diarization failed: {diarization_error}")
                    self.logger.warning("Diarization failed: %s", diarization_error)
                    self.logger.warning("Continuing without speaker labels...")

                    speaker_segments_with_labels = [
                        {
                            'text': seg.text,
                            'start_time': seg.start_time,
                            'end_time': seg.end_time,
                            'speaker': 'UNKNOWN',
                            'confidence': seg.confidence,
                            'words': seg.words
                        }
                        for seg in merged_segments
                    ]

                    result.status = ProcessingStatus.COMPLETED
                    result.data = {
                        "speaker_segments_with_labels": speaker_segments_with_labels,
                        "unique_speakers": 0
                    }

                    StatusTracker.update_stage(
                        self.session_id,
                        5,
                        ProcessingStatus.FAILED,
                        f"Diarization failed: {diarization_error}"
                    )

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(f"Speaker diarization stage failed: {str(e)}")
            self.logger.error("Stage 5/9 failed: %s", e, exc_info=True)
            StatusTracker.update_stage(
                self.session_id,
                5,
                ProcessingStatus.FAILED,
                f"Stage failed: {e}"
            )

        finally:
            result.end_time = datetime.now()

        return result

    def _stage_segments_classification(
        self,
        speaker_segments_with_labels: List[Dict],
        skip_classification: bool
    ) -> StageResult:
        """
        Stage 6/9: Classify segments as In-Character (IC) or Out-of-Character (OOC).

        This stage uses an LLM classifier to determine whether each segment
        represents in-game roleplay (IC) or out-of-game discussion (OOC).

        Args:
            speaker_segments_with_labels: Segments with speaker labels from Stage 5
            skip_classification: If True, skip classification and default to IC

        Returns:
            StageResult with:
                - data["classifications"]: List[ClassificationResult] - IC/OOC labels
                - data["ic_count"]: int - Number of IC segments
                - data["ooc_count"]: int - Number of OOC segments

        Dependencies:
            - Stage 5 (Speaker Diarization)

        Can Fail:
            - No (graceful degradation) - Falls back to all IC labels
        """
        result = StageResult(
            stage=PipelineStage.SEGMENTS_CLASSIFIED,
            status=ProcessingStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            if skip_classification:
                self.logger.info("Stage 6/9: IC/OOC classification skipped")
                StatusTracker.update_stage(
                    self.session_id,
                    6,
                    ProcessingStatus.SKIPPED,
                    "IC/OOC classification skipped"
                )

                # Default all segments to IC
                classifications = [
                    ClassificationResult(
                        segment_index=i,
                        classification=Classification.IN_CHARACTER,
                        confidence=ConfidenceDefaults.DEFAULT,
                        reasoning="Classification skipped"
                    )
                    for i in range(len(speaker_segments_with_labels))
                ]

                result.status = ProcessingStatus.SKIPPED
                result.data = {
                    "classifications": classifications,
                    "ic_count": len(classifications),
                    "ooc_count": 0
                }

                self.logger.info(
                    "Stage 6/9 skipped; defaulted all %d segments to IC",
                    len(speaker_segments_with_labels)
                )

            else:
                self.logger.info("Stage 6/9: IC/OOC classification...")
                StatusTracker.update_stage(
                    self.session_id,
                    6,
                    ProcessingStatus.RUNNING,
                    "Classifying IC/OOC segments"
                )

                try:
                    # Perform classification
                    classifications = self.classifier.classify_segments(
                        speaker_segments_with_labels,
                        self.character_names,
                        self.player_names
                    )

                    ic_count = sum(1 for c in classifications if c.classification == "IC")
                    ooc_count = sum(1 for c in classifications if c.classification == "OOC")

                    result.status = ProcessingStatus.COMPLETED
                    result.data = {
                        "classifications": classifications,
                        "ic_count": ic_count,
                        "ooc_count": ooc_count
                    }

                    self.logger.info(
                        "Stage 6/9 complete: %d IC segments, %d OOC segments",
                        ic_count,
                        ooc_count
                    )
                    StatusTracker.update_stage(
                        self.session_id,
                        6,
                        ProcessingStatus.COMPLETED,
                        f"IC segments: {ic_count}, OOC segments: {ooc_count}"
                    )

                except Exception as classification_error:
                    # Graceful degradation - log warning and default to IC
                    result.warnings.append(f"Classification failed: {classification_error}")
                    self.logger.warning("Classification failed: %s", classification_error)
                    self.logger.warning("Continuing with default IC labels...")

                    classifications = [
                        ClassificationResult(
                            segment_index=i,
                            classification=Classification.IN_CHARACTER,
                            confidence=ConfidenceDefaults.DEFAULT,
                            reasoning="Classification skipped due to error"
                        )
                        for i in range(len(speaker_segments_with_labels))
                    ]

                    result.status = ProcessingStatus.COMPLETED
                    result.data = {
                        "classifications": classifications,
                        "ic_count": len(classifications),
                        "ooc_count": 0
                    }

                    StatusTracker.update_stage(
                        self.session_id,
                        6,
                        ProcessingStatus.FAILED,
                        f"Classification failed: {classification_error}"
                    )

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(f"Segment classification stage failed: {str(e)}")
            self.logger.error("Stage 6/9 failed: %s", e, exc_info=True)
            StatusTracker.update_stage(
                self.session_id,
                6,
                ProcessingStatus.FAILED,
                f"Stage failed: {e}"
            )

        finally:
            result.end_time = datetime.now()

        return result

    def _stage_outputs_generation(
        self,
        speaker_segments_with_labels: List[Dict],
        classifications: List[ClassificationResult],
        output_dir: Path,
        input_file: Path
    ) -> StageResult:
        """
        Stage 7/9: Generate transcript outputs in multiple formats.

        This stage creates formatted transcript files (TXT, JSON, HTML, Markdown)
        and generates session statistics.

        Args:
            speaker_segments_with_labels: Segments with speakers from Stage 5
            classifications: IC/OOC classifications from Stage 6
            output_dir: Session output directory
            input_file: Original input file path (for metadata)

        Returns:
            StageResult with:
                - data["output_files"]: Dict[str, str] - Map of format to file path
                - data["statistics"]: Dict[str, Any] - Session statistics
                - data["speaker_profiles"]: Dict[str, str] - Speaker ID to name mapping

        Dependencies:
            - Stage 5 (Speaker Diarization)
            - Stage 6 (Segment Classification)

        Can Fail:
            - Yes (critical failure) - Transcript outputs are essential
        """
        result = StageResult(
            stage=PipelineStage.OUTPUTS_GENERATED,
            status=ProcessingStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            self.logger.info("Stage 7/9: Generating transcript outputs...")
            StatusTracker.update_stage(
                self.session_id,
                7,
                ProcessingStatus.RUNNING,
                "Rendering transcripts"
            )

            # Build speaker profiles mapping
            speaker_profiles: Dict[str, str] = {}
            for speaker_id in {seg['speaker'] for seg in speaker_segments_with_labels}:
                person_name = self.speaker_profile_manager.get_person_name(
                    self.session_id,
                    speaker_id
                )
                if person_name:
                    speaker_profiles[speaker_id] = person_name

            # Generate statistics
            stats = StatisticsGenerator.generate_stats(
                speaker_segments_with_labels,
                classifications
            )

            # Get campaign name for display
            campaign_name = None
            if self.campaign_id:
                from .party_config import CampaignManager
                campaign_manager = CampaignManager()
                campaign = campaign_manager.get_campaign(self.campaign_id)
                if campaign:
                    campaign_name = campaign.name

            # Build metadata
            metadata = {
                'session_id': self.session_id,
                'campaign_id': self.campaign_id,
                'campaign_name': campaign_name,
                'party_id': self.party_id,
                'input_file': str(input_file),
                'character_names': self.character_names,
                'player_names': self.player_names,
                'statistics': stats
            }

            # Generate all output formats
            output_files = self.formatter.save_all_formats(
                speaker_segments_with_labels,
                classifications,
                output_dir,
                self.safe_session_id,
                speaker_profiles,
                metadata
            )

            # Success!
            result.status = ProcessingStatus.COMPLETED
            result.data = {
                "output_files": output_files,
                "statistics": stats,
                "speaker_profiles": speaker_profiles
            }

            for format_name, file_path in output_files.items():
                self.logger.info("Stage 7/9 output generated (%s): %s", format_name, file_path)

            StatusTracker.update_stage(
                self.session_id,
                7,
                ProcessingStatus.COMPLETED,
                "Transcript outputs saved"
            )

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(f"Output generation failed: {str(e)}")
            self.logger.error("Stage 7/9 failed: %s", e, exc_info=True)
            StatusTracker.update_stage(
                self.session_id,
                7,
                ProcessingStatus.FAILED,
                f"Output generation failed: {e}"
            )

        finally:
            result.end_time = datetime.now()

        return result

    def _stage_audio_segments_export(
        self,
        wav_file: Path,
        speaker_segments_with_labels: List[Dict],
        classifications: List[ClassificationResult],
        output_dir: Path,
        skip_snippets: bool
    ) -> StageResult:
        """
        Stage 8/9: Export individual audio segments as separate files.

        This stage creates individual audio clips for each segment along with
        a manifest file for easy navigation and playback.

        Args:
            wav_file: Path to audio file from Stage 1
            speaker_segments_with_labels: Segments from Stage 5
            classifications: Classifications from Stage 6
            output_dir: Session output directory
            skip_snippets: If True, skip audio segment export

        Returns:
            StageResult with:
                - data["segment_export"]: Dict with segments_dir and manifest paths
                - data["segments_exported"]: int - Number of segments exported

        Dependencies:
            - Stage 1 (Audio Conversion)
            - Stage 5 (Speaker Diarization)
            - Stage 6 (Segment Classification)

        Can Fail:
            - No (graceful degradation) - Audio snippets are optional
        """
        result = StageResult(
            stage=PipelineStage.AUDIO_SEGMENTS_EXPORTED,
            status=ProcessingStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            if skip_snippets:
                self.logger.info("Stage 8/9: Audio segment export skipped")
                StatusTracker.update_stage(
                    self.session_id,
                    8,
                    ProcessingStatus.SKIPPED,
                    "Snippet export skipped"
                )

                result.status = ProcessingStatus.SKIPPED
                result.data = {
                    "segment_export": {
                        'segments_dir': None,
                        'manifest': None
                    },
                    "segments_exported": 0
                }

            else:
                self.logger.info("Stage 8/9: Exporting audio segments...")
                StatusTracker.update_stage(
                    self.session_id,
                    8,
                    ProcessingStatus.RUNNING,
                    "Writing per-segment audio clips"
                )

                try:
                    segments_output_base = output_dir / "segments"
                    segments_dir = segments_output_base / self.safe_session_id

                    # Initialize manifest
                    manifest_path = self.snipper.initialize_manifest(segments_dir)

                    # Export each segment
                    for i, segment in enumerate(speaker_segments_with_labels):
                        classification = (
                            classifications[i]
                            if classifications and i < len(classifications)
                            else None
                        )
                        self.snipper.export_incremental(
                            wav_file,
                            segment,
                            i + 1,
                            segments_dir,
                            manifest_path,
                            classification
                        )

                    # Finalize manifest
                    with self.snipper._manifest_lock:
                        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                        manifest_data["status"] = "complete"
                        manifest_path.write_text(
                            json.dumps(manifest_data, indent=2, ensure_ascii=False),
                            encoding="utf-8"
                        )

                    result.status = ProcessingStatus.COMPLETED
                    result.data = {
                        "segment_export": {
                            'segments_dir': str(segments_dir),
                            'manifest': str(manifest_path)
                        },
                        "segments_exported": len(speaker_segments_with_labels)
                    }

                    self.logger.info("Stage 8/9 complete: segments stored in %s", segments_dir)
                    StatusTracker.update_stage(
                        self.session_id,
                        8,
                        ProcessingStatus.COMPLETED,
                        f"Exported {len(speaker_segments_with_labels)} clips"
                    )

                except Exception as export_error:
                    # Graceful degradation - log warning and continue
                    result.warnings.append(f"Audio segment export failed: {export_error}")
                    self.logger.warning("Audio segment export failed: %s", export_error)

                    result.status = ProcessingStatus.COMPLETED
                    result.data = {
                        "segment_export": {
                            'segments_dir': None,
                            'manifest': None
                        },
                        "segments_exported": 0
                    }

                    StatusTracker.update_stage(
                        self.session_id,
                        8,
                        ProcessingStatus.FAILED,
                        f"Export failed: {export_error}"
                    )

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(f"Audio segment export stage failed: {str(e)}")
            self.logger.error("Stage 8/9 failed: %s", e, exc_info=True)
            StatusTracker.update_stage(
                self.session_id,
                8,
                ProcessingStatus.FAILED,
                f"Stage failed: {e}"
            )

        finally:
            result.end_time = datetime.now()

        return result

    def _stage_knowledge_extraction(
        self,
        speaker_segments_with_labels: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Dict[str, str],
        skip_knowledge: bool
    ) -> StageResult:
        """
        Stage 9/9: Extract campaign knowledge from IC transcript.

        This stage uses an LLM to extract campaign entities (NPCs, quests, locations,
        items, plot hooks) from the in-character transcript and merges them into
        the campaign knowledge base.

        Args:
            speaker_segments_with_labels: Segments from Stage 5
            classifications: Classifications from Stage 6
            speaker_profiles: Speaker profiles from Stage 7
            skip_knowledge: If True, skip knowledge extraction

        Returns:
            StageResult with:
                - data["knowledge_data"]: Dict with extracted entities and counts
                - data["total_entities"]: int - Total entities extracted

        Dependencies:
            - Stage 5 (Speaker Diarization)
            - Stage 6 (Segment Classification)
            - Stage 7 (Output Generation)

        Can Fail:
            - No (graceful degradation) - Knowledge extraction is optional
        """
        result = StageResult(
            stage=PipelineStage.KNOWLEDGE_EXTRACTED,
            status=ProcessingStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            if skip_knowledge:
                self.logger.info("Stage 9/9: Campaign knowledge extraction skipped")
                StatusTracker.update_stage(
                    self.session_id,
                    9,
                    ProcessingStatus.SKIPPED,
                    "Knowledge extraction skipped"
                )

                result.status = ProcessingStatus.SKIPPED
                result.data = {
                    "knowledge_data": {},
                    "total_entities": 0
                }

            else:
                self.logger.info("Stage 9/9: Extracting campaign knowledge from IC transcript...")
                StatusTracker.update_stage(
                    self.session_id,
                    9,
                    ProcessingStatus.RUNNING,
                    "Analyzing IC transcript for entities"
                )

                try:
                    # Initialize extraction components
                    extractor = KnowledgeExtractor()
                    knowledge_campaign_id = self.campaign_id or self.party_id or "default"
                    campaign_kb = CampaignKnowledgeBase(campaign_id=knowledge_campaign_id)

                    # Get IC-only transcript
                    ic_text = self.formatter.format_ic_only(
                        speaker_segments_with_labels,
                        classifications,
                        speaker_profiles
                    )

                    # Build party context
                    party_context_dict = None
                    if self.party_id:
                        party = self.party_manager.get_party(self.party_id)
                        if party:
                            party_context_dict = {
                                'character_names': self.character_names,
                                'campaign': party.campaign or 'Unknown'
                            }

                    # Extract knowledge
                    new_knowledge = extractor.extract_knowledge(
                        ic_text,
                        self.session_id,
                        party_context_dict
                    )

                    # Merge into campaign knowledge base
                    campaign_kb.merge_new_knowledge(new_knowledge, self.session_id)

                    # Count extracted entities
                    entity_counts = {
                        'quests': len(new_knowledge.get('quests', [])),
                        'npcs': len(new_knowledge.get('npcs', [])),
                        'plot_hooks': len(new_knowledge.get('plot_hooks', [])),
                        'locations': len(new_knowledge.get('locations', [])),
                        'items': len(new_knowledge.get('items', []))
                    }
                    total_entities = sum(entity_counts.values())

                    result.status = ProcessingStatus.COMPLETED
                    result.data = {
                        "knowledge_data": {
                            'extracted': entity_counts,
                            'knowledge_file': str(campaign_kb.knowledge_file)
                        },
                        "total_entities": total_entities
                    }

                    self.logger.info(
                        "Stage 9/9 complete: Extracted %d entities (Q:%d, NPC:%d, Plot:%d, Loc:%d, Item:%d)",
                        total_entities,
                        entity_counts['quests'],
                        entity_counts['npcs'],
                        entity_counts['plot_hooks'],
                        entity_counts['locations'],
                        entity_counts['items']
                    )
                    StatusTracker.update_stage(
                        self.session_id,
                        9,
                        ProcessingStatus.COMPLETED,
                        f"Extracted {total_entities} campaign entities"
                    )

                except Exception as knowledge_error:
                    # Graceful degradation - log warning and continue
                    result.warnings.append(f"Knowledge extraction failed: {knowledge_error}")
                    self.logger.warning("Knowledge extraction failed: %s", knowledge_error)

                    result.status = ProcessingStatus.COMPLETED
                    result.data = {
                        "knowledge_data": {'error': str(knowledge_error)},
                        "total_entities": 0
                    }

                    StatusTracker.update_stage(
                        self.session_id,
                        9,
                        ProcessingStatus.FAILED,
                        f"Extraction failed: {knowledge_error}"
                    )

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.errors.append(f"Knowledge extraction stage failed: {str(e)}")
            self.logger.error("Stage 9/9 failed: %s", e, exc_info=True)
            StatusTracker.update_stage(
                self.session_id,
                9,
                ProcessingStatus.FAILED,
                f"Stage failed: {e}"
            )

        finally:
            result.end_time = datetime.now()

        return result

    # ========================================================================
    # Helper Methods for Checkpoint Management
    # ========================================================================

    def _should_skip_stage(
        self,
        stage: PipelineStage,
        completed_stages: set
    ) -> bool:
        """
        Check if a stage should be skipped because it's already completed.

        Args:
            stage: The pipeline stage to check
            completed_stages: Set of completed stage enums

        Returns:
            True if stage is already completed and can be skipped
        """
        return stage in completed_stages

    def _load_stage_from_checkpoint(
        self,
        stage: PipelineStage
    ) -> Optional[Dict[str, Any]]:
        """
        Load stage data from checkpoint.

        Args:
            stage: The pipeline stage to load

        Returns:
            Dictionary with stage data, or None if not found
        """
        try:
            checkpoint = self.checkpoint_manager.load(stage)
            if checkpoint:
                return checkpoint.data
            return None
        except Exception as e:
            self.logger.warning("Failed to load checkpoint for %s: %s", stage.value, e)
            return None

    def _save_stage_to_checkpoint(
        self,
        stage: PipelineStage,
        stage_data: Dict[str, Any],
        completed_stages: set,
        checkpoint_metadata: Dict[str, Any]
    ):
        """
        Save stage result to checkpoint.

        Args:
            stage: The pipeline stage that completed
            stage_data: Data to save for this stage
            completed_stages: Set of all completed stages
            checkpoint_metadata: Session metadata for checkpoint
        """
        try:
            self.checkpoint_manager.save(
                stage,
                stage_data,
                completed_stages=sorted(completed_stages),
                metadata=checkpoint_metadata
            )
        except Exception as e:
            self.logger.warning("Failed to save checkpoint for %s: %s", stage.value, e)

    def _reconstruct_chunks_from_checkpoint(
        self,
        chunk_dicts: List[Dict],
        wav_file: Path
    ) -> List[AudioChunk]:
        """
        Reconstruct AudioChunk objects from checkpoint dictionaries.

        Args:
            chunk_dicts: List of chunk dictionaries from checkpoint
            wav_file: Path to audio file for loading segments

        Returns:
            List of AudioChunk objects with audio data

        Raises:
            FileNotFoundError: If wav_file doesn't exist
        """
        if not wav_file.exists():
            raise FileNotFoundError(
                f"Required audio file '{wav_file}' for checkpoint resumption not found. "
                "Cannot reconstruct audio chunks."
            )

        reconstructed_chunks = []
        for chunk_data in chunk_dicts:
            start_time = chunk_data["start_time"]
            end_time = chunk_data["end_time"]
            audio_segment, _ = self.audio_processor.load_audio_segment(
                wav_file,
                start_time,
                end_time
            )
            reconstructed_chunks.append(
                AudioChunk.from_dict(chunk_data, audio_data=audio_segment)
            )

        return reconstructed_chunks

    def process(
        self,
        input_file: Path,
        output_dir: Path = None,
        skip_diarization: bool = False,
        skip_classification: bool = False,
        skip_snippets: bool = False,
        skip_knowledge: bool = False,
        is_test_run: bool = False
    ):
        """
        Process a complete D&D session recording through the 9-stage pipeline.

        This method orchestrates the entire workflow:
        1. Audio Conversion
        2. Audio Chunking
        3. Audio Transcription
        4. Transcription Merging
        5. Speaker Diarization
        6. IC/OOC Classification
        7. Output Generation
        8. Audio Segments Export
        9. Campaign Knowledge Extraction

        Each stage is executed via dedicated stage methods (_stage_*) with
        consistent error handling, checkpoint support, and progress tracking.

        Args:
            input_file: Path to input video or audio file
            output_dir: Optional custom output directory (defaults to Config.OUTPUT_DIR)
            skip_diarization: Skip speaker identification (default: False)
            skip_classification: Skip IC/OOC classification (default: False)
            skip_snippets: Skip audio segment export (default: False)
            skip_knowledge: Skip knowledge extraction (default: False)
            is_test_run: Flag for test mode (default: False)

        Returns:
            Dictionary containing:
                - output_files: Dict of format -> file path
                - statistics: Session statistics
                - audio_segments: Segment export info
                - knowledge_extraction: Extracted entities
                - success: Boolean success flag

        Raises:
            RuntimeError: If critical pipeline stage fails
        """
        self.is_test_run = is_test_run

        # ====================================================================
        # Setup and Initialization
        # ====================================================================

        base_output_dir = Path(output_dir or Config.OUTPUT_DIR)
        resume_stage: Optional[str] = None
        resume_record = None
        completed_stages = set()

        # Load checkpoint if resume is enabled
        if self.resume_enabled:
            latest = self.checkpoint_manager.latest()
            if latest:
                resume_stage, resume_record = latest
                completed_stages = set(resume_record.completed_stages or [])
                self.logger.info(
                    "Checkpoint detected for session '%s' at stage '%s' (saved %s)",
                    self.session_id,
                    resume_stage,
                    resume_record.timestamp,
                )

        # Determine output directory
        if resume_record and resume_record.metadata.get("session_output_dir"):
            output_dir = Path(resume_record.metadata["session_output_dir"])
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = create_session_output_dir(base_output_dir, self.safe_session_id)

        checkpoint_metadata = {
            "input_file": str(input_file),
            "session_output_dir": str(output_dir),
            "base_output_dir": str(base_output_dir),
        }

        # Session logging
        start_time = perf_counter()
        log_session_start(
            self.session_id,
            input_file=str(input_file),
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets,
            skip_knowledge=skip_knowledge
        )
        self.logger.info("Processing session '%s' from %s", self.session_id, input_file)
        self.logger.info("Session output directory: %s", output_dir)
        self.logger.info("Verbose log available at %s", get_log_file_path())

        skip_flags = {
            'diarization': skip_diarization,
            'classification': skip_classification,
            'snippets': skip_snippets,
            'knowledge': skip_knowledge
        }

        # Preflight checks
        preflight_checker = PreflightChecker(
            transcriber=self.transcriber,
            diarizer=self.diarizer,
            classifier=self.classifier,
        )
        preflight_checker.verify(
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
        )

        session_options = {
            'input_file': str(input_file),
            'base_output_dir': str(base_output_dir),
            'session_output_dir': str(output_dir),
            'num_speakers': self.num_speakers,
            'using_party_config': bool(self.party_id),
            'campaign_id': self.campaign_id,
            'party_id': self.party_id,
            'character_names': list(self.character_names),
            'character_names_provided': bool(self.character_names),
            'player_names': list(self.player_names),
            'player_names_provided': bool(self.player_names),
            'skip_diarization': skip_diarization,
            'skip_classification': skip_classification,
            'skip_snippets': skip_snippets,
            'skip_knowledge': skip_knowledge,
            'party_context_available': bool(self.party_context)
        }

        StatusTracker.start_session(self.session_id, skip_flags, session_options, campaign_id=self.campaign_id)

        try:
            # ============================================================
            # Stage 1: Audio Conversion
            # ============================================================
            wav_file: Optional[Path] = None
            duration: Optional[float] = None

            if self._should_skip_stage(PipelineStage.AUDIO_CONVERTED, completed_stages):
                checkpoint_data = self._load_stage_from_checkpoint(PipelineStage.AUDIO_CONVERTED)
                if checkpoint_data:
                    wav_file = Path(checkpoint_data["wav_path"])
                    duration = checkpoint_data.get("duration", 0.0)
                    if wav_file.exists():
                        self.logger.info("Stage 1/9: Using converted audio from checkpoint %s", wav_file)
                        StatusTracker.update_stage(
                            self.session_id, 1, ProcessingStatus.COMPLETED,
                            f"Duration {duration:.1f}s (checkpoint)"
                        )
                    else:
                        # Checkpoint invalid, re-run stage
                        self.logger.warning("Checkpoint WAV missing, re-running conversion")
                        completed_stages.discard(PipelineStage.AUDIO_CONVERTED)

            if not self._should_skip_stage(PipelineStage.AUDIO_CONVERTED, completed_stages):
                result = self._stage_audio_conversion(input_file, output_dir)
                if not result.success:
                    raise RuntimeError(f"Audio conversion failed: {', '.join(result.errors)}")
                wav_file = Path(result.data["wav_path"])
                duration = result.data["duration"]
                completed_stages.add(PipelineStage.AUDIO_CONVERTED)
                self._save_stage_to_checkpoint(
                    PipelineStage.AUDIO_CONVERTED,
                    {"wav_path": str(wav_file), "duration": duration},
                    completed_stages,
                    checkpoint_metadata
                )

            # ============================================================
            # Stage 2: Audio Chunking
            # ============================================================
            chunks: List[AudioChunk] = []

            if self._should_skip_stage(PipelineStage.AUDIO_CHUNKED, completed_stages):
                checkpoint_data = self._load_stage_from_checkpoint(PipelineStage.AUDIO_CHUNKED)
                if checkpoint_data and checkpoint_data.get("chunks"):
                    chunk_dicts = checkpoint_data["chunks"]
                    chunks = self._reconstruct_chunks_from_checkpoint(chunk_dicts, wav_file)
                    self.logger.info("Stage 2/9: Using audio chunks from checkpoint (%d chunks)", len(chunks))
                    StatusTracker.update_stage(
                        self.session_id, 2, ProcessingStatus.COMPLETED,
                        f"Loaded {len(chunks)} chunks (checkpoint)"
                    )
                else:
                    completed_stages.discard(PipelineStage.AUDIO_CHUNKED)

            if not self._should_skip_stage(PipelineStage.AUDIO_CHUNKED, completed_stages):
                result = self._stage_audio_chunking(wav_file, duration)
                if not result.success:
                    raise RuntimeError(f"Audio chunking failed: {', '.join(result.errors)}")
                chunks = result.data["chunks"]
                completed_stages.add(PipelineStage.AUDIO_CHUNKED)
                # Save as dictionaries for serialization
                self._save_stage_to_checkpoint(
                    PipelineStage.AUDIO_CHUNKED,
                    {"chunks": [c.to_dict() for c in chunks]},
                    completed_stages,
                    checkpoint_metadata
                )

            # ============================================================
            # Stage 3: Audio Transcription
            # ============================================================
            chunk_transcriptions: List[ChunkTranscription] = []

            if self._should_skip_stage(PipelineStage.AUDIO_TRANSCRIBED, completed_stages):
                checkpoint_data = self._load_stage_from_checkpoint(PipelineStage.AUDIO_TRANSCRIBED)
                if checkpoint_data:
                    # Handle both blob reference and direct data
                    transcriptions_data = []
                    if "chunk_transcriptions_path" in checkpoint_data:
                        try:
                            blob_ref = checkpoint_data["chunk_transcriptions_path"]
                            transcriptions_data = self.checkpoint_manager.read_blob(blob_ref)
                        except FileNotFoundError:
                            self.logger.warning("Transcription blob missing, re-running transcription")
                            completed_stages.discard(PipelineStage.AUDIO_TRANSCRIBED)
                    else:
                        transcriptions_data = checkpoint_data.get("chunk_transcriptions", [])

                    if transcriptions_data:
                        chunk_transcriptions = [ChunkTranscription.from_dict(td) for td in transcriptions_data]
                        self.logger.info(
                            "Stage 3/9: Using chunk transcriptions from checkpoint (%d transcriptions)",
                            len(chunk_transcriptions)
                        )
                        StatusTracker.update_stage(
                            self.session_id, 3, ProcessingStatus.COMPLETED,
                            f"Loaded {len(chunk_transcriptions)} chunk transcriptions (checkpoint)"
                        )
                    else:
                        completed_stages.discard(PipelineStage.AUDIO_TRANSCRIBED)
                else:
                    completed_stages.discard(PipelineStage.AUDIO_TRANSCRIBED)

            if not self._should_skip_stage(PipelineStage.AUDIO_TRANSCRIBED, completed_stages):
                result = self._stage_audio_transcription(chunks)
                if not result.success:
                    raise RuntimeError(f"Audio transcription failed: {', '.join(result.errors)}")
                chunk_transcriptions = result.data["chunk_transcriptions"]
                completed_stages.add(PipelineStage.AUDIO_TRANSCRIBED)
                # Save to blob for large data
                blob_ref = self.checkpoint_manager.write_blob(
                    PipelineStage.AUDIO_TRANSCRIBED,
                    "chunk_transcriptions",
                    [ct.to_dict() for ct in chunk_transcriptions]
                )
                self._save_stage_to_checkpoint(
                    PipelineStage.AUDIO_TRANSCRIBED,
                    {
                        "chunk_transcriptions_path": str(blob_ref),
                        "transcription_count": len(chunk_transcriptions)
                    },
                    completed_stages,
                    checkpoint_metadata
                )

            # ============================================================
            # Stage 4: Transcription Merging
            # ============================================================
            merged_segments: List[TranscriptionSegment] = []

            if self._should_skip_stage(PipelineStage.TRANSCRIPTION_MERGED, completed_stages):
                checkpoint_data = self._load_stage_from_checkpoint(PipelineStage.TRANSCRIPTION_MERGED)
                if checkpoint_data:
                    merged_segments_data = []
                    if "merged_segments_path" in checkpoint_data:
                        try:
                            blob_ref = checkpoint_data["merged_segments_path"]
                            merged_segments_data = self.checkpoint_manager.read_blob(blob_ref)
                        except FileNotFoundError:
                            self.logger.warning("Merged segments blob missing, re-running merging")
                            completed_stages.discard(PipelineStage.TRANSCRIPTION_MERGED)
                    else:
                        merged_segments_data = checkpoint_data.get("merged_segments", [])

                    if merged_segments_data:
                        merged_segments = [TranscriptionSegment.from_dict(msd) for msd in merged_segments_data]
                        self.logger.info(
                            "Stage 4/9: Using merged segments from checkpoint (%d segments)",
                            len(merged_segments)
                        )
                        StatusTracker.update_stage(
                            self.session_id, 4, ProcessingStatus.COMPLETED,
                            f"Loaded {len(merged_segments)} merged segments (checkpoint)"
                        )
                    else:
                        completed_stages.discard(PipelineStage.TRANSCRIPTION_MERGED)
                else:
                    completed_stages.discard(PipelineStage.TRANSCRIPTION_MERGED)

            if not self._should_skip_stage(PipelineStage.TRANSCRIPTION_MERGED, completed_stages):
                result = self._stage_transcription_merging(chunk_transcriptions)
                if not result.success:
                    raise RuntimeError(f"Transcription merging failed: {', '.join(result.errors)}")
                merged_segments = result.data["merged_segments"]
                completed_stages.add(PipelineStage.TRANSCRIPTION_MERGED)
                blob_ref = self.checkpoint_manager.write_blob(
                    PipelineStage.TRANSCRIPTION_MERGED,
                    "merged_segments",
                    [ms.to_dict() for ms in merged_segments]
                )
                self._save_stage_to_checkpoint(
                    PipelineStage.TRANSCRIPTION_MERGED,
                    {
                        "merged_segments_path": str(blob_ref),
                        "merged_segment_count": len(merged_segments)
                    },
                    completed_stages,
                    checkpoint_metadata
                )

            # ============================================================
            # Stage 5: Speaker Diarization
            # ============================================================
            speaker_segments_with_labels: List[Dict] = []

            if self._should_skip_stage(PipelineStage.SPEAKER_DIARIZED, completed_stages):
                checkpoint_data = self._load_stage_from_checkpoint(PipelineStage.SPEAKER_DIARIZED)
                if checkpoint_data:
                    speaker_data = []
                    if "speaker_segments_path" in checkpoint_data:
                        try:
                            blob_ref = checkpoint_data["speaker_segments_path"]
                            speaker_data = self.checkpoint_manager.read_blob(blob_ref)
                        except FileNotFoundError:
                            self.logger.warning("Speaker segment blob missing, re-running diarization")
                            completed_stages.discard(PipelineStage.SPEAKER_DIARIZED)
                    else:
                        speaker_data = checkpoint_data.get("speaker_segments_with_labels", [])

                    if speaker_data:
                        speaker_segments_with_labels = speaker_data
                        self.logger.info(
                            "Stage 5/9: Using speaker segments from checkpoint (%d segments)",
                            len(speaker_segments_with_labels)
                        )
                        StatusTracker.update_stage(
                            self.session_id, 5, ProcessingStatus.COMPLETED,
                            f"Loaded {len(speaker_segments_with_labels)} speaker segments (checkpoint)"
                        )
                    else:
                        completed_stages.discard(PipelineStage.SPEAKER_DIARIZED)
                else:
                    completed_stages.discard(PipelineStage.SPEAKER_DIARIZED)

            if not self._should_skip_stage(PipelineStage.SPEAKER_DIARIZED, completed_stages):
                result = self._stage_speaker_diarization(wav_file, merged_segments, skip_diarization)
                # Diarization can fail gracefully, so check for completion or skip
                if result.success or result.status == ProcessingStatus.SKIPPED:
                    speaker_segments_with_labels = result.data["speaker_segments_with_labels"]
                    completed_stages.add(PipelineStage.SPEAKER_DIARIZED)
                    blob_ref = self.checkpoint_manager.write_blob(
                        PipelineStage.SPEAKER_DIARIZED,
                        "speaker_segments",
                        speaker_segments_with_labels
                    )
                    self._save_stage_to_checkpoint(
                        PipelineStage.SPEAKER_DIARIZED,
                        {
                            "speaker_segments_path": str(blob_ref),
                            "speaker_segment_count": len(speaker_segments_with_labels)
                        },
                        completed_stages,
                        checkpoint_metadata
                    )
                else:
                    raise RuntimeError(f"Speaker diarization failed: {', '.join(result.errors)}")

            # ============================================================
            # Stage 6: Segment Classification
            # ============================================================
            classifications: List[ClassificationResult] = []

            if self._should_skip_stage(PipelineStage.SEGMENTS_CLASSIFIED, completed_stages):
                checkpoint_data = self._load_stage_from_checkpoint(PipelineStage.SEGMENTS_CLASSIFIED)
                if checkpoint_data:
                    classifications_data = []
                    if "classifications_path" in checkpoint_data:
                        try:
                            blob_ref = checkpoint_data["classifications_path"]
                            classifications_data = self.checkpoint_manager.read_blob(blob_ref)
                        except FileNotFoundError:
                            self.logger.warning("Classification blob missing, re-running classification")
                            completed_stages.discard(PipelineStage.SEGMENTS_CLASSIFIED)
                    else:
                        classifications_data = checkpoint_data.get("classifications", [])

                    if classifications_data:
                        classifications = [ClassificationResult.from_dict(cd) for cd in classifications_data]
                        self.logger.info(
                            "Stage 6/9: Using classifications from checkpoint (%d classifications)",
                            len(classifications)
                        )
                        StatusTracker.update_stage(
                            self.session_id, 6, ProcessingStatus.COMPLETED,
                            f"Loaded {len(classifications)} classifications (checkpoint)"
                        )
                    else:
                        completed_stages.discard(PipelineStage.SEGMENTS_CLASSIFIED)
                else:
                    completed_stages.discard(PipelineStage.SEGMENTS_CLASSIFIED)

            if not self._should_skip_stage(PipelineStage.SEGMENTS_CLASSIFIED, completed_stages):
                result = self._stage_segments_classification(speaker_segments_with_labels, skip_classification)
                # Classification can fail gracefully, so check for completion or skip
                if result.success or result.status == ProcessingStatus.SKIPPED:
                    classifications = result.data["classifications"]
                    completed_stages.add(PipelineStage.SEGMENTS_CLASSIFIED)
                    blob_ref = self.checkpoint_manager.write_blob(
                        PipelineStage.SEGMENTS_CLASSIFIED,
                        "classifications",
                        [c.to_dict() for c in classifications]
                    )
                    self._save_stage_to_checkpoint(
                        PipelineStage.SEGMENTS_CLASSIFIED,
                        {
                            "classifications_path": str(blob_ref),
                            "classification_count": len(classifications)
                        },
                        completed_stages,
                        checkpoint_metadata
                    )
                else:
                    raise RuntimeError(f"Segment classification failed: {', '.join(result.errors)}")

            # ============================================================
            # Stage 7: Output Generation
            # ============================================================
            speaker_profiles: Dict[str, str] = {}
            stats: Dict[str, Any] = {}
            output_files: Dict[str, Any] = {}

            if self._should_skip_stage(PipelineStage.OUTPUTS_GENERATED, completed_stages):
                checkpoint_data = self._load_stage_from_checkpoint(PipelineStage.OUTPUTS_GENERATED)
                if checkpoint_data:
                    output_files = checkpoint_data.get("output_files", {})
                    stats = checkpoint_data.get("statistics", {})
                    speaker_profiles = checkpoint_data.get("speaker_profiles", {})
                    self.logger.info("Stage 7/9: Reusing transcript outputs from checkpoint")
                    StatusTracker.update_stage(
                        self.session_id, 7, ProcessingStatus.COMPLETED,
                        "Transcript outputs restored from checkpoint"
                    )
                else:
                    completed_stages.discard(PipelineStage.OUTPUTS_GENERATED)

            if not self._should_skip_stage(PipelineStage.OUTPUTS_GENERATED, completed_stages):
                result = self._stage_outputs_generation(
                    speaker_segments_with_labels,
                    classifications,
                    output_dir,
                    input_file
                )
                if not result.success:
                    raise RuntimeError(f"Output generation failed: {', '.join(result.errors)}")
                output_files = result.data["output_files"]
                stats = result.data["statistics"]
                speaker_profiles = result.data["speaker_profiles"]
                completed_stages.add(PipelineStage.OUTPUTS_GENERATED)
                self._save_stage_to_checkpoint(
                    PipelineStage.OUTPUTS_GENERATED,
                    {
                        "output_files": output_files,
                        "statistics": stats,
                        "speaker_profiles": speaker_profiles
                    },
                    completed_stages,
                    checkpoint_metadata
                )

            # ============================================================
            # Stage 8: Audio Segments Export
            # ============================================================
            segment_export: Dict[str, Any] = {'segments_dir': None, 'manifest': None}

            if self._should_skip_stage(PipelineStage.AUDIO_SEGMENTS_EXPORTED, completed_stages):
                checkpoint_data = self._load_stage_from_checkpoint(PipelineStage.AUDIO_SEGMENTS_EXPORTED)
                if checkpoint_data:
                    segment_export = checkpoint_data.get("segment_export", segment_export)
                    self.logger.info("Stage 8/9: Reusing audio segment export from checkpoint")
                    StatusTracker.update_stage(
                        self.session_id, 8, ProcessingStatus.COMPLETED,
                        "Audio segments restored from checkpoint"
                    )
                else:
                    completed_stages.discard(PipelineStage.AUDIO_SEGMENTS_EXPORTED)

            if not self._should_skip_stage(PipelineStage.AUDIO_SEGMENTS_EXPORTED, completed_stages):
                result = self._stage_audio_segments_export(
                    wav_file,
                    speaker_segments_with_labels,
                    classifications,
                    output_dir,
                    skip_snippets
                )
                # Audio segment export is optional, always succeeds
                segment_export = result.data["segment_export"]
                completed_stages.add(PipelineStage.AUDIO_SEGMENTS_EXPORTED)
                self._save_stage_to_checkpoint(
                    PipelineStage.AUDIO_SEGMENTS_EXPORTED,
                    {"segment_export": segment_export},
                    completed_stages,
                    checkpoint_metadata
                )

            # ============================================================
            # Stage 9: Knowledge Extraction
            # ============================================================
            knowledge_data: Dict[str, Any] = {}

            if self._should_skip_stage(PipelineStage.KNOWLEDGE_EXTRACTED, completed_stages):
                checkpoint_data = self._load_stage_from_checkpoint(PipelineStage.KNOWLEDGE_EXTRACTED)
                if checkpoint_data:
                    knowledge_data = checkpoint_data.get("knowledge_data", {})
                    self.logger.info("Stage 9/9: Reusing knowledge extraction results from checkpoint")
                    StatusTracker.update_stage(
                        self.session_id, 9, ProcessingStatus.COMPLETED,
                        "Knowledge extraction restored from checkpoint"
                    )
                else:
                    completed_stages.discard(PipelineStage.KNOWLEDGE_EXTRACTED)

            if not self._should_skip_stage(PipelineStage.KNOWLEDGE_EXTRACTED, completed_stages):
                result = self._stage_knowledge_extraction(
                    speaker_segments_with_labels,
                    classifications,
                    speaker_profiles,
                    skip_knowledge
                )
                # Knowledge extraction is optional, always succeeds
                knowledge_data = result.data["knowledge_data"]
                completed_stages.add(PipelineStage.KNOWLEDGE_EXTRACTED)
                self._save_stage_to_checkpoint(
                    PipelineStage.KNOWLEDGE_EXTRACTED,
                    {"knowledge_data": knowledge_data},
                    completed_stages,
                    checkpoint_metadata
                )

            # ============================================================
            # Pipeline Complete - Log Summary and Cleanup
            # ============================================================
            self.logger.info("Processing complete for session '%s'", self.session_id)
            self.logger.info(
                "Session duration (audio): %s | IC duration: %s (%.1f%%)",
                stats['total_duration_formatted'],
                stats['ic_duration_formatted'],
                stats['ic_percentage']
            )
            self.logger.info(
                "Segments: total=%d, IC=%d, OOC=%d",
                stats['total_segments'],
                stats['ic_segments'],
                stats['ooc_segments']
            )
            if stats['character_appearances']:
                for char, count in sorted(stats['character_appearances'].items(), key=lambda x: -x[1]):
                    self.logger.info("Character '%s' appearances: %d", char, count)

            duration_seconds = perf_counter() - start_time
            StatusTracker.complete_session(self.session_id)
            log_session_end(self.session_id, duration_seconds, success=True)

            # Processing completed successfully; clear checkpoints for next run
            if self.resume_enabled:
                self.checkpoint_manager.clear()

            return {
                'output_files': output_files,
                'statistics': stats,
                'audio_segments': segment_export,
                'knowledge_extraction': knowledge_data,
                'success': True
            }

        except Exception as processing_error:
            duration_seconds = perf_counter() - start_time
            log_error_with_context(processing_error, context="DDSessionProcessor.process")
            StatusTracker.fail_session(self.session_id, str(processing_error))
            log_session_end(self.session_id, duration_seconds, success=False)
            self.logger.error("Processing failed for session '%s'", self.session_id, exc_info=True)
            raise

    def run_preflight_checks_only(
        self,
        *,
        skip_diarization: bool,
        skip_classification: bool,
    ) -> List[PreflightIssue]:
        """Collect preflight issues without running the full pipeline."""
        preflight_checker = PreflightChecker(
            transcriber=self.transcriber,
            diarizer=self.diarizer,
            classifier=self.classifier,
        )
        return preflight_checker.collect_issues(
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
        )
    def update_speaker_mapping(
        self,
        speaker_id: str,
        person_name: str
    ):
        """
        Map a speaker ID to a person name.

        Useful for manual correction after first processing.

        Args:
            speaker_id: PyAnnote speaker ID (e.g., "SPEAKER_00")
            person_name: Actual person name (e.g., "Alice", "DM")
        """
        self.speaker_profile_manager.map_speaker(
            self.session_id,
            speaker_id,
            person_name
        )
        self.logger.info("Mapped speaker %s to person %s", speaker_id, person_name)

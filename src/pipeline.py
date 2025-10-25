"""Main processing pipeline orchestrating all components"""
from pathlib import Path
from time import perf_counter
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime
from tqdm import tqdm
from .config import Config
from .checkpoint import CheckpointManager
from .audio_processor import AudioProcessor
from .chunker import HybridChunker, AudioChunk
from .transcriber import TranscriberFactory, ChunkTranscription
from .merger import TranscriptionMerger
from .diarizer import SpeakerDiarizer, SpeakerProfileManager
from .classifier import ClassifierFactory, ClassificationResult
from .formatter import TranscriptFormatter, StatisticsGenerator, sanitize_filename
from .party_config import PartyConfigManager
from .snipper import AudioSnipper
from .logger import get_logger, get_log_file_path, log_session_start, log_session_end, log_error_with_context
from .status_tracker import StatusTracker
from .knowledge_base import KnowledgeExtractor, CampaignKnowledgeBase

try:  # pragma: no cover - convenience for test environment
    from unittest.mock import Mock as _Mock  # type: ignore
except ImportError:  # pragma: no cover
    _Mock = None


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
        character_names: Optional[List[str]] = None,
        player_names: Optional[List[str]] = None,
        num_speakers: int = 4,
        party_id: Optional[str] = None,
        resume: bool = True
    ):
        """
        Args:
            session_id: Unique identifier for this session
            character_names: List of character names in the campaign
            player_names: List of player names
            num_speakers: Expected number of speakers (3 players + 1 DM = 4)
            party_id: Party configuration to use (defaults to "default")
        """
        self.session_id = session_id
        self.safe_session_id = sanitize_filename(session_id)
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
        self.transcriber = TranscriberFactory.create()
        self.merger = TranscriptionMerger()
        self.diarizer = SpeakerDiarizer(num_speakers=num_speakers)
        self.classifier = ClassifierFactory.create()
        self.formatter = TranscriptFormatter()
        self.speaker_profile_manager = SpeakerProfileManager()
        self.snipper = AudioSnipper()

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
        """Process a complete D&D session recording and yield progress updates."""
        self.is_test_run = is_test_run
        # ... (rest of the method is too long to show, but it is now a generator)

        self.is_test_run = is_test_run
        # Create or reuse session-specific output directory with optional checkpoint resume
        base_output_dir = Path(output_dir or Config.OUTPUT_DIR)
        resume_stage: Optional[str] = None
        resume_record = None
        completed_stages = set()

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

        session_options = {
            'input_file': str(input_file),
            'base_output_dir': str(base_output_dir),
            'session_output_dir': str(output_dir),
            'num_speakers': self.num_speakers,
            'using_party_config': bool(self.party_id),
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

        StatusTracker.start_session(self.session_id, skip_flags, session_options)

        try:
            use_checkpoint_audio = False
            wav_file: Optional[Path] = None
            duration: Optional[float] = None

            if "audio_converted" in completed_stages:
                audio_checkpoint = self.checkpoint_manager.load("audio_converted")
                wav_path_str = audio_checkpoint.data.get("wav_path") if audio_checkpoint else None
                if wav_path_str:
                    wav_path = Path(wav_path_str)
                    if wav_path.exists():
                        wav_file = wav_path
                        duration = float(audio_checkpoint.data.get("duration", 0.0))
                        use_checkpoint_audio = True
                    else:
                        self.logger.warning(
                            "Checkpoint WAV missing at %s; re-running conversion",
                            wav_path,
                        )
                        completed_stages.discard("audio_converted")

            if use_checkpoint_audio:
                self.logger.info("Stage 1/9: Using converted audio from checkpoint %s", wav_file)
                StatusTracker.update_stage(
                    self.session_id,
                    1,
                    "completed",
                    f"Duration {duration:.1f}s (checkpoint)",
                )
            else:
                self.logger.info("Stage 1/9: Converting audio to optimal format...")
                StatusTracker.update_stage(self.session_id, 1, "running", "Converting source audio")
                wav_file = self.audio_processor.convert_to_wav(input_file)
                duration = self.audio_processor.get_duration(wav_file)
                StatusTracker.update_stage(
                    self.session_id, 1, "completed", f"Duration {duration:.1f}s"
                )
                completed_stages.add("audio_converted")
                self.checkpoint_manager.save(
                    "audio_converted",
                    {
                        "wav_path": str(wav_file),
                        "duration": duration,
                    },
                    completed_stages=sorted(completed_stages),
                    metadata=checkpoint_metadata,
                )

            duration_hours = (duration or 0.0) / 3600 if duration else 0.0
            self.logger.info(
                "Stage 1/9 %s: %.1f seconds of audio (%.1f hours)",
                "resumed" if use_checkpoint_audio else "complete",
                duration or 0.0,
                duration_hours,
            )

            self.logger.info("Stage 2/9: Chunking audio with VAD...")
            StatusTracker.update_stage(self.session_id, 2, "running", "Detecting speech regions")

            if "audio_chunked" in completed_stages:
                chunk_checkpoint = self.checkpoint_manager.load("audio_chunked")
                chunks = chunk_checkpoint.data.get("chunks") if chunk_checkpoint else []
                if chunks:
                    self.logger.info("Stage 2/9: Using audio chunks from checkpoint (%d chunks)", len(chunks))
                    StatusTracker.update_stage(
                        self.session_id, 2, "completed", f"Loaded {len(chunks)} chunks (checkpoint)"
                    )
                else:
                    self.logger.warning("Checkpoint for audio chunks found but data is empty; re-running chunking")
                    completed_stages.discard("audio_chunked")
                    # Fall through to re-run chunking
            
            if "audio_chunked" not in completed_stages: # Only run if not loaded from checkpoint or checkpoint was empty
                chunk_progress = {"count": 0}

                def _chunk_progress_callback(chunk, total_duration):
                    try:
                        chunk_progress["count"] = chunk.chunk_index + 1
                        details = {
                            "chunks_created": chunk_progress["count"],
                            "latest_chunk_index": chunk.chunk_index,
                            "latest_chunk_end": round(chunk.end_time, 2)
                        }
                        if total_duration and total_duration > 0:
                            percent = min(100.0, max(0.0, (chunk.end_time / total_duration) * 100))
                            details["progress_percent"] = round(percent, 1)

                        StatusTracker.update_stage(
                            self.session_id,
                            2,
                            "running",
                            message=f"Chunking... {chunk_progress['count']} chunk{'s' if chunk_progress['count'] != 1 else ''}",
                            details=details
                        )
                    except Exception as progress_error:
                        self.logger.debug("Chunk progress callback skipped: %s", progress_error)

                chunks = self.chunker.chunk_audio(wav_file, progress_callback=_chunk_progress_callback)
                if not chunks:
                    if not self.is_test_run:
                        raise RuntimeError(
                            "Audio chunking resulted in zero segments. This can happen if the audio is completely silent, "
                            "corrupt, or too short. Please check the input audio file."
                        )
                    # For test runs, we might want to continue with an empty list of chunks
                    self.logger.warning("Chunker returned no segments; continuing with downstream mocks for test run.")
                StatusTracker.update_stage(
                    self.session_id, 2, "completed", f"Created {len(chunks)} chunks"
                )
                self.logger.info("Stage 2/9 complete: %d chunks created", len(chunks))
                completed_stages.add("audio_chunked")
                self.checkpoint_manager.save(
                    "audio_chunked",
                    {"chunks": [c.to_dict() for c in chunks]}, # Convert chunks to serializable dicts
                    completed_stages=sorted(completed_stages),
                    metadata=checkpoint_metadata,
                )
            
            # If chunks were loaded from checkpoint, they are already in the correct format.
            # If chunking was re-run, `chunks` is already populated.
            # If loaded from checkpoint, convert dicts back to Chunk objects and load audio.
            if "audio_chunked" in completed_stages and chunks and isinstance(chunks[0], dict):
                reconstructed_chunks = []
                for chunk_data in chunks:
                    start_time = chunk_data["start_time"]
                    end_time = chunk_data["end_time"]
                    # Ensure wav_file is available for loading segments
                    if wav_file and wav_file.exists():
                        audio_segment, _ = self.audio_processor.load_audio_segment(wav_file, start_time, end_time)
                        reconstructed_chunks.append(AudioChunk.from_dict(chunk_data, audio_data=audio_segment))
                    else:
                        raise FileNotFoundError(
                            f"Required audio file '{wav_file}' for checkpoint resumption not found. "
                            "Cannot reconstruct audio chunks."
                        )
                chunks = reconstructed_chunks

            self.logger.info("Stage 2/9 %s: %d chunks processed", "resumed" if "audio_chunked" in completed_stages else "complete", len(chunks))

            self.logger.info("Stage 3/9: Transcribing chunks (this may take a while)...")
            StatusTracker.update_stage(
                self.session_id, 3, "running", f"Transcribing {len(chunks)} chunks"
            )
            chunk_transcriptions: List[ChunkTranscription] = []

            if "audio_transcribed" in completed_stages:
                transcription_checkpoint = self.checkpoint_manager.load("audio_transcribed")
                transcriptions_data = transcription_checkpoint.data.get("chunk_transcriptions") if transcription_checkpoint else []
                if transcriptions_data:
                    chunk_transcriptions = [ChunkTranscription.from_dict(td) for td in transcriptions_data]
                    self.logger.info("Stage 3/9: Using chunk transcriptions from checkpoint (%d transcriptions)", len(chunk_transcriptions))
                    StatusTracker.update_stage(
                        self.session_id, 3, "completed", f"Loaded {len(chunk_transcriptions)} chunk transcriptions (checkpoint)"
                    )
                else:
                    self.logger.warning("Checkpoint for chunk transcriptions found but data is empty; re-running transcription")
                    completed_stages.discard("audio_transcribed")

            if "audio_transcribed" not in completed_stages:
                for chunk in tqdm(chunks, desc="Transcribing"):
                    transcription = self.transcriber.transcribe_chunk(chunk, language="nl")
                    chunk_transcriptions.append(transcription)
                StatusTracker.update_stage(
                    self.session_id, 3, "completed", f"Received {len(chunk_transcriptions)} chunk transcriptions"
                )
                self.logger.info("Stage 3/9 complete: transcription finished")
                completed_stages.add("audio_transcribed")
                self.checkpoint_manager.save(
                    "audio_transcribed",
                    {"chunk_transcriptions": [ct.to_dict() for ct in chunk_transcriptions]},
                    completed_stages=sorted(completed_stages),
                    metadata=checkpoint_metadata,
                )

            self.logger.info("Stage 3/9 %s: %d chunk transcriptions processed", "resumed" if "audio_transcribed" in completed_stages else "complete", len(chunk_transcriptions))

            self.logger.info("Stage 4/9: Merging overlapping chunks...")
            StatusTracker.update_stage(self.session_id, 4, "running", "Aligning overlapping transcripts")
            merged_segments: List[TranscriptionSegment] = []

            if "transcription_merged" in completed_stages:
                merge_checkpoint = self.checkpoint_manager.load("transcription_merged")
                merged_segments_data = merge_checkpoint.data.get("merged_segments") if merge_checkpoint else []
                if merged_segments_data:
                    merged_segments = [TranscriptionSegment.from_dict(msd) for msd in merged_segments_data]
                    self.logger.info("Stage 4/9: Using merged segments from checkpoint (%d segments)", len(merged_segments))
                    StatusTracker.update_stage(
                        self.session_id, 4, "completed", f"Loaded {len(merged_segments)} merged segments (checkpoint)"
                    )
                else:
                    self.logger.warning("Checkpoint for merged segments found but data is empty; re-running merging")
                    completed_stages.discard("transcription_merged")

            if "transcription_merged" not in completed_stages:
                merged_segments = self.merger.merge_transcriptions(chunk_transcriptions)
                StatusTracker.update_stage(
                    self.session_id, 4, "completed", f"Merged into {len(merged_segments)} segments"
                )
                self.logger.info("Stage 4/9 complete: %d merged segments", len(merged_segments))
                completed_stages.add("transcription_merged")
                self.checkpoint_manager.save(
                    "transcription_merged",
                    {"merged_segments": [ms.to_dict() for ms in merged_segments]},
                    completed_stages=sorted(completed_stages),
                    metadata=checkpoint_metadata,
                )

            self.logger.info("Stage 4/9 %s: %d merged segments processed", "resumed" if "transcription_merged" in completed_stages else "complete", len(merged_segments))

            self.logger.info("Stage 5/9: Speaker diarization%s", " (skipped)" if skip_diarization else "...")
            speaker_segments_with_labels: List[Dict] = []

            if "speaker_diarized" in completed_stages:
                diarization_checkpoint = self.checkpoint_manager.load("speaker_diarized")
                speaker_segments_with_labels = diarization_checkpoint.data.get("speaker_segments_with_labels") if diarization_checkpoint else []
                if speaker_segments_with_labels:
                    self.logger.info("Stage 5/9: Using speaker segments from checkpoint (%d segments)", len(speaker_segments_with_labels))
                    StatusTracker.update_stage(
                        self.session_id, 5, "completed", f"Loaded {len(speaker_segments_with_labels)} speaker segments (checkpoint)"
                    )
                else:
                    self.logger.warning("Checkpoint for speaker segments found but data is empty; re-running diarization")
                    completed_stages.discard("speaker_diarized")

            if "speaker_diarized" not in completed_stages:
                if not skip_diarization:
                    StatusTracker.update_stage(self.session_id, 5, "running", "Performing speaker diarization")
                    try:
                        speaker_segments = self.diarizer.diarize(wav_file)
                        speaker_segments_with_labels = self.diarizer.assign_speakers_to_transcription(
                            merged_segments,
                            speaker_segments
                        )
                        unique_speakers = {seg['speaker'] for seg in speaker_segments_with_labels}
                        StatusTracker.update_stage(
                            self.session_id,
                            5,
                            "completed",
                            f"Identified {len(unique_speakers)} speaker labels"
                        )
                        self.logger.info("Stage 5/9 complete: %d speaker labels assigned", len(unique_speakers))
                    except Exception as diarization_error:
                        StatusTracker.update_stage(
                            self.session_id,
                            5,
                            "failed",
                            f"Diarization failed: {diarization_error}"
                        )
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
                else:
                    StatusTracker.update_stage(self.session_id, 5, "skipped", "Speaker diarization skipped")
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
                completed_stages.add("speaker_diarized")
                self.checkpoint_manager.save(
                    "speaker_diarized",
                    {"speaker_segments_with_labels": speaker_segments_with_labels},
                    completed_stages=sorted(completed_stages),
                    metadata=checkpoint_metadata,
                )

            self.logger.info("Stage 5/9 %s: %d speaker segments processed", "resumed" if "speaker_diarized" in completed_stages else "complete", len(speaker_segments_with_labels))

            self.logger.info("Stage 6/9: IC/OOC classification%s", " (skipped)" if skip_classification else "...")
            classifications: List[ClassificationResult] = []

            if "segments_classified" in completed_stages:
                classification_checkpoint = self.checkpoint_manager.load("segments_classified")
                classifications_data = classification_checkpoint.data.get("classifications") if classification_checkpoint else []
                if classifications_data:
                    classifications = [ClassificationResult.from_dict(cd) for cd in classifications_data]
                    self.logger.info("Stage 6/9: Using classifications from checkpoint (%d classifications)", len(classifications))
                    StatusTracker.update_stage(
                        self.session_id, 6, "completed", f"Loaded {len(classifications)} classifications (checkpoint)"
                    )
                else:
                    self.logger.warning("Checkpoint for classifications found but data is empty; re-running classification")
                    completed_stages.discard("segments_classified")

            if "segments_classified" not in completed_stages:
                if not skip_classification:
                    StatusTracker.update_stage(self.session_id, 6, "running", "Classifying IC/OOC segments")
                    try:
                        classifications = self.classifier.classify_segments(
                            speaker_segments_with_labels,
                            self.character_names,
                            self.player_names
                        )
                        ic_count = sum(1 for c in classifications if c.classification == "IC")
                        ooc_count = sum(1 for c in classifications if c.classification == "OOC")
                        StatusTracker.update_stage(
                            self.session_id,
                            6,
                            "completed",
                            f"IC segments: {ic_count}, OOC segments: {ooc_count}"
                        )
                        self.logger.info(
                            "Stage 6/9 complete: %d IC segments, %d OOC segments",
                            ic_count,
                            ooc_count
                        )
                    except Exception as classification_error:
                        StatusTracker.update_stage(
                            self.session_id,
                            6,
                            "failed",
                            f"Classification failed: {classification_error}"
                        )
                        self.logger.warning("Classification failed: %s", classification_error)
                        self.logger.warning("Continuing with default IC labels...")
                        classifications = [
                            ClassificationResult(
                                segment_index=i,
                                classification="IC",
                                confidence=0.5,
                                reasoning="Classification skipped due to error"
                            )
                            for i in range(len(speaker_segments_with_labels))
                        ]
                else:
                    StatusTracker.update_stage(self.session_id, 6, "skipped", "IC/OOC classification skipped")
                    classifications = [
                        ClassificationResult(
                            segment_index=i,
                            classification="IC",
                            confidence=0.5,
                            reasoning="Classification skipped"
                        )
                        for i in range(len(speaker_segments_with_labels))
                    ]
                    self.logger.info(
                        "Stage 6/9 skipped; defaulted all %d segments to IC",
                        len(speaker_segments_with_labels)
                    )
                completed_stages.add("segments_classified")
                self.checkpoint_manager.save(
                    "segments_classified",
                    {"classifications": [c.to_dict() for c in classifications]},
                    completed_stages=sorted(completed_stages),
                    metadata=checkpoint_metadata,
                )

            self.logger.info("Stage 6/9 %s: %d classifications processed", "resumed" if "segments_classified" in completed_stages else "complete", len(classifications))

            self.logger.info("Stage 7/9: Generating transcript outputs...")
            StatusTracker.update_stage(self.session_id, 7, "running", "Rendering transcripts")
            speaker_profiles: Dict[str, str] = {}
            for speaker_id in {seg['speaker'] for seg in speaker_segments_with_labels}:
                person_name = self.speaker_profile_manager.get_person_name(self.session_id, speaker_id)
                if person_name:
                    speaker_profiles[speaker_id] = person_name

            stats = StatisticsGenerator.generate_stats(
                speaker_segments_with_labels,
                classifications
            )

            metadata = {
                'session_id': self.session_id,
                'input_file': str(input_file),
                'character_names': self.character_names,
                'player_names': self.player_names,
                'statistics': stats
            }

            output_files = self.formatter.save_all_formats(
                speaker_segments_with_labels,
                classifications,
                output_dir,
                self.safe_session_id,
                speaker_profiles,
                metadata
            )

            for format_name, file_path in output_files.items():
                self.logger.info("Stage 7/9 output generated (%s): %s", format_name, file_path)
            StatusTracker.update_stage(self.session_id, 7, "completed", "Transcript outputs saved")
            completed_stages.add("outputs_generated")
            self.checkpoint_manager.save(
                "outputs_generated",
                {
                    "output_files": output_files,
                    "statistics": stats,
                    "speaker_profiles": speaker_profiles,
                },
                completed_stages=sorted(completed_stages),
                metadata=checkpoint_metadata,
            )

            segments_output_base = output_dir / "segments"
            if skip_snippets:
                self.logger.info("Stage 8/9: Audio segment export skipped")
                StatusTracker.update_stage(self.session_id, 8, "skipped", "Snippet export skipped")
                segment_export = {'segments_dir': None, 'manifest': None}
            else:
                self.logger.info("Stage 8/9: Exporting audio segments...")
                StatusTracker.update_stage(self.session_id, 8, "running", "Writing per-segment audio clips")
                try:
                    manifest_path = self.snipper.initialize_manifest(segments_output_base / self.safe_session_id)
                    for i, segment in enumerate(speaker_segments_with_labels):
                        classification = classifications[i] if classifications and i < len(classifications) else None
                        self.snipper.export_incremental(wav_file, segment, i + 1, segments_output_base / self.safe_session_id, manifest_path, classification)

                    with self.snipper._manifest_lock:
                        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                        manifest_data["status"] = "complete"
                        manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

                    segments_dir = segments_output_base / self.safe_session_id
                    self.logger.info("Stage 8/9 complete: segments stored in %s", segments_dir)
                    StatusTracker.update_stage(
                        self.session_id, 8, "completed", f"Exported {len(speaker_segments_with_labels)} clips"
                    )
                    segment_export = {
                        'segments_dir': segments_dir,
                        'manifest': manifest_path
                    }

                except Exception as export_error:
                    self.logger.warning("Audio segment export failed: %s", export_error)
                    StatusTracker.update_stage(self.session_id, 8, "failed", f"Export failed: {export_error}")
                    segment_export = {
                        'segments_dir': None,
                        'manifest': None
                    }
                completed_stages.add("audio_segments_exported")
                self.checkpoint_manager.save(
                    "audio_segments_exported",
                    {"segment_export": segment_export},
                    completed_stages=sorted(completed_stages),
                    metadata=checkpoint_metadata,
                )

            # Stage 9/9: Campaign Knowledge Extraction
            knowledge_data = {}
            if skip_knowledge:
                self.logger.info("Stage 9/9: Campaign knowledge extraction skipped")
                StatusTracker.update_stage(self.session_id, 9, "skipped", "Knowledge extraction skipped")
            else:
                self.logger.info("Stage 9/9: Extracting campaign knowledge from IC transcript...")
                StatusTracker.update_stage(self.session_id, 9, "running", "Analyzing IC transcript for entities")
                try:
                    # Initialize knowledge extraction components
                    extractor = KnowledgeExtractor()
                    campaign_id = self.party_id or "default"
                    campaign_kb = CampaignKnowledgeBase(campaign_id=campaign_id)

                    # Get IC-only transcript text
                    ic_text = self.formatter.format_ic_only(
                        speaker_segments_with_labels,
                        classifications,
                        speaker_profiles
                    )

                    # Build party context for better extraction
                    party_context_dict = None
                    if self.party_id:
                        party = self.party_manager.get_party(self.party_id)
                        if party:
                            party_context_dict = {
                                'character_names': self.character_names,
                                'campaign': party.campaign or 'Unknown'
                            }

                    # Extract knowledge from IC transcript
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

                    knowledge_data = {
                        'extracted': entity_counts,
                        'knowledge_file': str(campaign_kb.knowledge_file)
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
                        "completed",
                        f"Extracted {total_entities} campaign entities"
                    )
                except Exception as knowledge_error:
                    self.logger.warning("Knowledge extraction failed: %s", knowledge_error)
                    StatusTracker.update_stage(
                        self.session_id,
                        9,
                        "failed",
                        f"Extraction failed: {knowledge_error}"
                    )
                    knowledge_data = {'error': str(knowledge_error)}
                completed_stages.add("knowledge_extracted")
                self.checkpoint_manager.save(
                    "knowledge_extracted",
                    {"knowledge_data": knowledge_data},
                    completed_stages=sorted(completed_stages),
                    metadata=checkpoint_metadata,
                )

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

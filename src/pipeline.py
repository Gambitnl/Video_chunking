"""Main processing pipeline orchestrating all components"""
from pathlib import Path
from time import perf_counter
from typing import Optional, List, Dict
from tqdm import tqdm
from .config import Config
from .audio_processor import AudioProcessor
from .chunker import HybridChunker
from .transcriber import TranscriberFactory, ChunkTranscription
from .merger import TranscriptionMerger
from .diarizer import SpeakerDiarizer, SpeakerProfileManager
from .classifier import ClassifierFactory, ClassificationResult
from .formatter import TranscriptFormatter, StatisticsGenerator
from .party_config import PartyConfigManager
from .snipper import AudioSnipper
from .logger import get_logger, log_session_start, log_session_end, log_error_with_context


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
        party_id: Optional[str] = None
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
        self.logger = get_logger(f"pipeline.{self.session_id}")

        self.party_manager = PartyConfigManager()

        # Load party configuration if provided
        if party_id:
            party = self.party_manager.get_party(party_id)
            if party:
                self.logger.info("Using party configuration: %s", party.party_name)
                self.character_names = self.party_manager.get_character_names(party_id)
                self.player_names = self.party_manager.get_player_names(party_id)
                self.party_context = self.party_manager.get_party_context_for_llm(party_id)
            else:
                self.logger.warning("Party '%s' not found, falling back to provided defaults", party_id)
                self.character_names = character_names or []
                self.player_names = player_names or []
                self.party_context = None
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
        skip_snippets: bool = False
    ) -> Dict:
        """Process a complete D&D session recording and return output metadata."""
        output_dir = output_dir or Config.OUTPUT_DIR
        output_dir = Path(output_dir)

        start_time = perf_counter()
        log_session_start(
            self.session_id,
            input_file=str(input_file),
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets
        )
        self.logger.info("Processing session '%s' from %s", self.session_id, input_file)

        try:
            self.logger.info("Stage 1/8: Converting audio to optimal format...")
            wav_file = self.audio_processor.convert_to_wav(input_file)
            duration = self.audio_processor.get_duration(wav_file)
            self.logger.info(
                "Stage 1/8 complete: %.1f seconds of audio (%.1f hours)",
                duration,
                duration / 3600
            )

            self.logger.info("Stage 2/8: Chunking audio with VAD...")
            chunks = self.chunker.chunk_audio(wav_file)
            self.logger.info("Stage 2/8 complete: %d chunks created", len(chunks))

            self.logger.info("Stage 3/8: Transcribing chunks (this may take a while)...")
            chunk_transcriptions: List[ChunkTranscription] = []
            for chunk in tqdm(chunks, desc="Transcribing"):
                transcription = self.transcriber.transcribe_chunk(chunk, language="nl")
                chunk_transcriptions.append(transcription)
            self.logger.info("Stage 3/8 complete: transcription finished")

            self.logger.info("Stage 4/8: Merging overlapping chunks...")
            merged_segments = self.merger.merge_transcriptions(chunk_transcriptions)
            self.logger.info("Stage 4/8 complete: %d merged segments", len(merged_segments))

            self.logger.info("Stage 5/8: Speaker diarization%s", " (skipped)" if skip_diarization else "...")
            if not skip_diarization:
                try:
                    speaker_segments = self.diarizer.diarize(wav_file)
                    speaker_segments_with_labels = self.diarizer.assign_speakers_to_transcription(
                        merged_segments,
                        speaker_segments
                    )
                    unique_speakers = {seg['speaker'] for seg in speaker_segments_with_labels}
                    self.logger.info("Stage 5/8 complete: %d speaker labels assigned", len(unique_speakers))
                except Exception as diarization_error:
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

            self.logger.info("Stage 6/8: IC/OOC classification%s", " (skipped)" if skip_classification else "...")
            if not skip_classification:
                try:
                    classifications = self.classifier.classify_segments(
                        speaker_segments_with_labels,
                        self.character_names,
                        self.player_names
                    )
                    ic_count = sum(1 for c in classifications if c.classification == "IC")
                    ooc_count = sum(1 for c in classifications if c.classification == "OOC")
                    self.logger.info(
                        "Stage 6/8 complete: %d IC segments, %d OOC segments",
                        ic_count,
                        ooc_count
                    )
                except Exception as classification_error:
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
                classifications = [
                    ClassificationResult(
                        segment_index=i,
                        classification="IC",
                        confidence=0.5,
                        reasoning="Classification skipped"
                    )
                    for i in range(len(speaker_segments_with_labels))
                ]

            self.logger.info("Stage 7/8: Generating transcript outputs...")
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
                self.session_id,
                speaker_profiles,
                metadata
            )

            for format_name, file_path in output_files.items():
                self.logger.info("Stage 7/8 output generated (%s): %s", format_name, file_path)

            segments_output_base = output_dir / "segments"
            if skip_snippets:
                self.logger.info("Stage 8/8: Audio segment export skipped")
                segment_export = {'segments_dir': None, 'manifest': None}
            else:
                self.logger.info("Stage 8/8: Exporting audio segments...")
                try:
                    segment_export = self.snipper.export_segments(
                        wav_file,
                        speaker_segments_with_labels,
                        segments_output_base,
                        self.session_id,
                        classifications=classifications
                    )
                    segments_dir = segment_export.get('segments_dir')
                    manifest_path = segment_export.get('manifest')
                    if segments_dir:
                        self.logger.info("Stage 8/8 complete: segments stored in %s", segments_dir)
                        if manifest_path:
                            self.logger.info("Segment manifest written to %s", manifest_path)
                    else:
                        self.logger.warning("No audio segments were exported")
                except Exception as export_error:
                    self.logger.warning("Audio segment export failed: %s", export_error)
                    segment_export = {
                        'segments_dir': None,
                        'manifest': None
                    }

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
            log_session_end(self.session_id, duration_seconds, success=True)

            return {
                'output_files': output_files,
                'statistics': stats,
                'audio_segments': segment_export,
                'success': True
            }

        except Exception as processing_error:
            duration_seconds = perf_counter() - start_time
            log_error_with_context(processing_error, context="DDSessionProcessor.process")
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

"""Main processing pipeline orchestrating all components"""
from pathlib import Path
from typing import Optional, List, Dict
from tqdm import tqdm
from .config import Config
from .audio_processor import AudioProcessor
from .chunker import HybridChunker
from .transcriber import TranscriberFactory, ChunkTranscription
from .merger import TranscriptionMerger
from .diarizer import SpeakerDiarizer, SpeakerProfileManager
from .classifier import ClassifierFactory
from .formatter import TranscriptFormatter, StatisticsGenerator
from .party_config import PartyConfigManager
from .snipper import AudioSnipper


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
        self.party_manager = PartyConfigManager()

        # Load party configuration if provided
        if party_id:
            party = self.party_manager.get_party(party_id)
            if party:
                print(f"Using party config: {party.party_name}")
                self.character_names = self.party_manager.get_character_names(party_id)
                self.player_names = self.party_manager.get_player_names(party_id)
                self.party_context = self.party_manager.get_party_context_for_llm(party_id)
            else:
                print(f"Warning: Party '{party_id}' not found, using defaults")
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
        skip_classification: bool = False
    ) -> Dict:
        """
        Process a complete D&D session recording.

        Args:
            input_file: Path to M4A (or any audio format) file
            output_dir: Output directory (defaults to Config.OUTPUT_DIR)
            skip_diarization: Skip speaker diarization (faster, but no speaker labels)
            skip_classification: Skip IC/OOC classification (faster, but no separation)

        Returns:
            Dictionary with output file paths, statistics, and segment export info
        """
        output_dir = output_dir or Config.OUTPUT_DIR
        output_dir = Path(output_dir)

        print(f"\n{'='*80}")
        print(f"Processing D&D Session: {self.session_id}")
        print(f"Input: {input_file}")
        print(f"{'='*80}\n")

        # Stage 1: Audio Conversion
        print("Stage 1/8: Converting audio to optimal format...")
        wav_file = self.audio_processor.convert_to_wav(input_file)
        duration = self.audio_processor.get_duration(wav_file)
        print(f"✓ Conversion complete. Duration: {duration:.1f} seconds ({duration/3600:.1f} hours)")

        # Stage 2: Chunking
        print("\nStage 2/8: Chunking audio with VAD...")
        chunks = self.chunker.chunk_audio(wav_file)
        print(f"✓ Created {len(chunks)} chunks")

        # Stage 3: Transcription
        print("\nStage 3/8: Transcribing chunks (this may take a while)...")
        chunk_transcriptions = []

        for chunk in tqdm(chunks, desc="Transcribing"):
            transcription = self.transcriber.transcribe_chunk(chunk, language="nl")
            chunk_transcriptions.append(transcription)

        print(f"✓ Transcription complete")

        # Stage 4: Merge overlapping transcriptions
        print("\nStage 4/8: Merging overlapping chunks...")
        merged_segments = self.merger.merge_transcriptions(chunk_transcriptions)
        print(f"✓ Merged into {len(merged_segments)} segments")

        # Stage 5: Speaker Diarization (optional)
        speaker_segments_with_labels = None

        if not skip_diarization:
            print("\nStage 5/8: Identifying speakers...")
            try:
                speaker_segments = self.diarizer.diarize(wav_file)
                speaker_segments_with_labels = self.diarizer.assign_speakers_to_transcription(
                    merged_segments,
                    speaker_segments
                )
                unique_speakers = set(seg['speaker'] for seg in speaker_segments_with_labels)
                print(f"✓ Identified {len(unique_speakers)} speakers")
            except Exception as e:
                print(f"⚠ Diarization failed: {e}")
                print("  Continuing without speaker labels...")
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
            print("\nStage 5/8: Speaker diarization skipped")
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

        # Stage 6: IC/OOC Classification (optional)
        classifications = None

        if not skip_classification:
            print("\nStage 6/8: Classifying IC/OOC segments...")
            try:
                classifications = self.classifier.classify_segments(
                    speaker_segments_with_labels,
                    self.character_names,
                    self.player_names
                )
                ic_count = sum(1 for c in classifications if c.classification == "IC")
                ooc_count = sum(1 for c in classifications if c.classification == "OOC")
                print(f"✓ Classification complete: {ic_count} IC, {ooc_count} OOC")
            except Exception as e:
                print(f"⚠ Classification failed: {e}")
                print("  Continuing without classification...")
                # Create dummy classifications
                from .classifier import ClassificationResult
                classifications = [
                    ClassificationResult(
                        segment_index=i,
                        classification="IC",
                        confidence=0.5,
                        reasoning="Classification skipped"
                    )
                    for i in range(len(speaker_segments_with_labels))
                ]
        else:
            print("\nStage 6/8: IC/OOC classification skipped")
            from .classifier import ClassificationResult
            classifications = [
                ClassificationResult(
                    segment_index=i,
                    classification="IC",
                    confidence=0.5,
                    reasoning="Classification skipped"
                )
                for i in range(len(speaker_segments_with_labels))
            ]

        # Stage 7: Generate Outputs
        print("\nStage 7/8: Generating output files...")

        # Get speaker profiles
        speaker_profiles = {}
        for speaker_id in set(seg['speaker'] for seg in speaker_segments_with_labels):
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

        # Prepare metadata
        metadata = {
            'session_id': self.session_id,
            'input_file': str(input_file),
            'character_names': self.character_names,
            'player_names': self.player_names,
            'statistics': stats
        }

        # Save all formats
        output_files = self.formatter.save_all_formats(
            speaker_segments_with_labels,
            classifications,
            output_dir,
            self.session_id,
            speaker_profiles,
            metadata
        )

        print(f"✓ Output files generated:")
        for format_name, file_path in output_files.items():
            print(f"  - {format_name}: {file_path}")

        print("\nStage 8/8: Exporting audio segments...")
        segments_output_base = output_dir / "segments"
        try:
            segment_export = self.snipper.export_segments(
                wav_file,
                speaker_segments_with_labels,
                segments_output_base,
                self.session_id
            )
            segments_dir = segment_export.get('segments_dir')
            if segments_dir:
                print(f"✓ Audio segments saved to: {segments_dir}")
                manifest_path = segment_export.get('manifest')
                if manifest_path:
                    print(f"  Manifest: {manifest_path}")
            else:
                print("⚠ No segments exported (no transcription segments available).")
        except Exception as e:
            print(f"⚠ Audio segment export failed: {e}")
            segment_export = {
                'segments_dir': None,
                'manifest': None
            }

        print(f"\n{'='*80}")
        print("Processing Complete!")
        print(f"{'='*80}")

        # Print statistics
        print("\nSession Statistics:")
        print(f"  Total Duration: {stats['total_duration_formatted']}")
        print(f"  IC Duration: {stats['ic_duration_formatted']} ({stats['ic_percentage']:.1f}%)")
        print(f"  Total Segments: {stats['total_segments']}")
        print(f"  IC Segments: {stats['ic_segments']}")
        print(f"  OOC Segments: {stats['ooc_segments']}")

        if stats['character_appearances']:
            print(f"\n  Character Appearances:")
            for char, count in sorted(stats['character_appearances'].items(), key=lambda x: -x[1]):
                print(f"    - {char}: {count}")

        return {
            'output_files': output_files,
            'statistics': stats,
            'audio_segments': segment_export,
            'success': True
        }

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
        print(f"✓ Mapped {speaker_id} → {person_name}")

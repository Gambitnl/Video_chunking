"""
Test suite for src/pipeline.py

Priority: P0 - Critical
Estimated Effort: 2-3 days
Status: Template - Not Implemented

See docs/TEST_PLANS.md for detailed specifications.
"""
import json
import pytest
import numpy as np
from src.config import Config
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.pipeline import DDSessionProcessor, create_session_output_dir
from src.chunker import AudioChunk
from src.transcriber import ChunkTranscription, TranscriptionSegment


# ============================================================================
# Session Directory Tests
# ============================================================================

def test_create_session_output_dir_format(tmp_path):
    """Test session directory naming format (YYYYMMDD_HHMMSS_session_id)."""
    session_dir = create_session_output_dir(tmp_path, "test_session")

    assert session_dir.exists()
    assert "test_session" in session_dir.name
    # Format should be: YYYYMMDD_HHMMSS_test_session
    parts = session_dir.name.split("_")
    assert len(parts) >= 3


def test_create_session_output_dir_creates_parents(tmp_path):
    """Test that parent directories are created if they don't exist."""
    base = tmp_path / "nonexistent" / "path"
    session_dir = create_session_output_dir(base, "test")

    assert session_dir.exists()
    assert session_dir.parent.exists()


def test_create_session_output_dir_idempotent(tmp_path):
    """Test that calling twice creates different directories (different timestamps)."""
    import time

    # Create first directory
    dir1 = create_session_output_dir(tmp_path, "test")
    assert dir1.exists()

    # Wait a moment to ensure different timestamp
    time.sleep(1.1)  # Sleep >1 second to get different timestamp

    # Create second directory with same session_id
    dir2 = create_session_output_dir(tmp_path, "test")
    assert dir2.exists()

    # Should create two different directories due to different timestamps
    assert dir1 != dir2
    assert "test" in dir1.name
    assert "test" in dir2.name


# ============================================================================
# Initialization Tests
# ============================================================================

@patch('src.pipeline.TranscriberFactory')
@patch('src.pipeline.DiarizerFactory')
@patch('src.pipeline.ClassifierFactory')
class TestDDSessionProcessorInit:
    """Test initialization of DDSessionProcessor."""

    def test_init_basic(self, MockClassifierFactory, MockDiarizerFactory, MockTranscriberFactory):
        """Test basic initialization with minimal parameters."""
        processor = DDSessionProcessor("test_session")

        assert processor.session_id == "test_session"
        assert processor.safe_session_id == "test_session"
        assert processor.logger is not None

    def test_init_sanitizes_session_id(self, MockClassifierFactory, MockDiarizerFactory, MockTranscriberFactory):
        """Test session ID sanitization for filesystem safety."""
        # Test with session_id containing filesystem-unsafe characters
        processor = DDSessionProcessor("test/session:2*file?")

        # Should sanitize to filesystem-safe name
        assert "/" not in processor.safe_session_id
        assert ":" not in processor.safe_session_id
        assert "*" not in processor.safe_session_id
        assert "?" not in processor.safe_session_id

        # Should still be valid
        assert processor.session_id == "test/session:2*file?"
        assert len(processor.safe_session_id) > 0

    def test_init_with_party_config(self, MockClassifierFactory, MockDiarizerFactory, MockTranscriberFactory, tmp_path):
        """Test initialization with party configuration."""
        # Test with explicit character and player names
        processor = DDSessionProcessor(
            "test",
            character_names=["Aragorn", "Legolas"],
            player_names=["Alice", "Bob"]
        )

        assert processor.character_names == ["Aragorn", "Legolas"]
        assert processor.player_names == ["Alice", "Bob"]
        assert processor.party_id is None  # No party_id provided
        assert processor.party_context is None

    def test_init_creates_checkpoint_manager(self, MockClassifierFactory, MockDiarizerFactory, MockTranscriberFactory):
        """Test that checkpoint manager is created when resume=True."""
        processor = DDSessionProcessor("test", resume=True)

        assert processor.checkpoint_manager is not None
        assert processor.resume_enabled is True

        # Test with resume=False
        processor_no_resume = DDSessionProcessor("test2", resume=False)
        assert processor_no_resume.checkpoint_manager is not None  # Manager created but not used
        assert processor_no_resume.resume_enabled is False

    @pytest.mark.skip(reason="N/A - output directory created in process(), not __init__()")
    def test_init_creates_output_directory(self, tmp_path):
        """Test that output directory structure is created."""
        # Note: Output directories are created during process(), not during initialization
        pass


# ============================================================================
# Stage Execution Tests (Mocked)
# ============================================================================

class TestPipelineStageExecution:
    """Test execution of individual pipeline stages with mocked dependencies."""

    def test_process_stage_audio_conversion(self, monkeypatch, tmp_path):
        """Test audio conversion stage with mocked AudioProcessor."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()

        # Mock all components to avoid full pipeline execution
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Patch all pipeline components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'):

            mock_audio_processor = mock_audio_cls.return_value
            mock_audio_processor.convert_to_wav.return_value = wav_file
            mock_audio_processor.get_duration.return_value = 120.0

            processor = DDSessionProcessor("test", resume=False)

            # Mock remaining pipeline stages to stop after conversion
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock())
            processor.merger.merge_transcriptions = MagicMock(return_value=[])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process the file
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify audio conversion was called
            mock_audio_processor.convert_to_wav.assert_called_once_with(input_file)
            mock_audio_processor.get_duration.assert_called_once_with(wav_file)

    @pytest.mark.skip(reason="Template - not implemented")
    def test_process_stage_chunking(self, monkeypatch, tmp_path):
        """Test chunking stage execution."""
        # TODO: Mock HybridChunker
        # TODO: Verify chunk_audio called
        # TODO: Verify chunks passed to next stage
        pass

    @pytest.mark.skip(reason="Template - not implemented")
    def test_process_stage_transcription(self, monkeypatch):
        """Test transcription stage with mocked transcriber."""
        # TODO: Mock TranscriberFactory.create()
        # TODO: Verify correct backend selected
        # TODO: Verify all chunks transcribed
        pass

    @pytest.mark.skip(reason="Template - not implemented")
    def test_process_stage_merging(self, monkeypatch):
        """Test overlap merging stage."""
        # TODO: Mock TranscriptionMerger
        # TODO: Verify merge_transcriptions called
        # TODO: Verify overlaps removed
        pass

    def test_process_stage_diarization_when_enabled(self, monkeypatch, tmp_path):
        """Test diarization runs when skip_diarization=False."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.CheckpointManager'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.DiarizerFactory') as mock_diarizer_factory, \
             patch('src.pipeline.ClassifierFactory'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            mock_diarizer = MagicMock()
            mock_diarizer_factory.create.return_value = mock_diarizer
            mock_diarizer.diarize.return_value = ([{'speaker': 'SPEAKER_00'}], {})  # Return tuple: (segments, embeddings)
            mock_diarizer.assign_speakers_to_transcription.return_value = [
                {'text': 'test', 'speaker': 'SPEAKER_00', 'start_time': 0, 'end_time': 1,
                 'confidence': 0.9, 'words': []}
            ]

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process with diarization enabled
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=False,  # Enable diarization
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify diarization was called
            mock_diarizer.diarize.assert_called_once_with(wav_file)
            mock_diarizer.assign_speakers_to_transcription.assert_called_once()

    def test_process_stage_diarization_when_skipped(self, monkeypatch, tmp_path):
        """Test diarization is skipped when skip_diarization=True."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.CheckpointManager'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.DiarizerFactory') as mock_diarizer_factory, \
             patch('src.pipeline.ClassifierFactory'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            mock_diarizer = MagicMock()
            mock_diarizer_factory.create.return_value = mock_diarizer

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process with diarization skipped
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,  # Skip diarization
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify diarizer was NOT called
            mock_diarizer.diarize.assert_not_called()
            mock_diarizer.assign_speakers_to_transcription.assert_not_called()

    def test_process_stage_classification_when_enabled(self, monkeypatch, tmp_path):
        """Test classification runs when skip_classification=False."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.CheckpointManager'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.ClassifierFactory') as mock_classifier_factory:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            mock_classifier = MagicMock()
            from src.classifier import ClassificationResult
            mock_classifier.classify_segments.return_value = [
                ClassificationResult(segment_index=0, classification="IC", confidence=0.9, reasoning="test")
            ]
            mock_classifier_factory.create.return_value = mock_classifier

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process with classification enabled
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=False,  # Enable classification
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify classification was called
            mock_classifier.classify_segments.assert_called_once()

    def test_process_stage_classification_when_skipped(self, monkeypatch, tmp_path):
        """Test classification is skipped when skip_classification=True."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.ClassifierFactory') as mock_classifier_factory:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            mock_classifier = MagicMock()
            mock_classifier_factory.create.return_value = mock_classifier

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process with classification skipped
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,  # Skip classification
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify classifier was NOT called
            mock_classifier.classify_segments.assert_not_called()


# ============================================================================
# Checkpoint/Resume Tests
# ============================================================================

class TestPipelineCheckpointResume:
    """Test checkpoint saving and resume functionality."""

    def test_checkpoint_saved_after_each_stage(self, monkeypatch, tmp_path):
        """Test checkpoint is saved after each major stage."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            processor = DDSessionProcessor("test", resume=True)

            # Mock checkpoint manager
            mock_checkpoint_manager = MagicMock()
            mock_checkpoint_manager.latest.return_value = None
            processor.checkpoint_manager = mock_checkpoint_manager

            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock())
            processor.merger.merge_transcriptions = MagicMock(return_value=[])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process the file
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify checkpoint manager save was called (at least for audio conversion stage)
            assert mock_checkpoint_manager.save.call_count > 0

            # Verify checkpoint was cleared after successful completion
            mock_checkpoint_manager.clear.assert_called_once()

    def test_resume_from_checkpoint_skips_completed_stages(self, tmp_path):
        """Test resuming skips already-completed stages."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'):

            mock_audio = mock_audio_cls.return_value

            processor = DDSessionProcessor("test", resume=True)

            # Mock checkpoint manager to return existing checkpoint
            from src.checkpoint import CheckpointRecord
            mock_checkpoint_record = CheckpointRecord(
                session_id="test",
                stage="audio_converted",
                timestamp="2025-10-24T12:00:00",
                data={"wav_path": str(wav_file), "duration": 60.0},
                completed_stages=["audio_converted"],
                metadata={"session_output_dir": str(tmp_path)}
            )

            mock_checkpoint_manager = MagicMock()
            mock_checkpoint_manager.latest.return_value = ("audio_converted", mock_checkpoint_record)
            mock_checkpoint_manager.load.return_value = mock_checkpoint_record
            processor.checkpoint_manager = mock_checkpoint_manager

            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock())
            processor.merger.merge_transcriptions = MagicMock(return_value=[])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process the file
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify audio conversion was NOT called (skipped due to checkpoint)
            mock_audio.convert_to_wav.assert_not_called()

            # Verify checkpoint was loaded
            mock_checkpoint_manager.load.assert_called_with("audio_converted")

    def test_resume_disabled_runs_from_beginning(self, tmp_path):
        """Test that resume=False ignores existing checkpoints."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory') as mock_classifier_factory, \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0
            mock_classifier_factory.create.return_value = MagicMock()


            # Initialize with resume=False
            processor = DDSessionProcessor("test", resume=False)

            # Mock checkpoint manager that has a checkpoint (but should be ignored)
            mock_checkpoint_manager = MagicMock()
            mock_checkpoint_manager.latest.return_value = None  # Not checked when resume=False
            processor.checkpoint_manager = mock_checkpoint_manager

            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock())
            processor.merger.merge_transcriptions = MagicMock(return_value=[])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process the file
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify audio conversion WAS called (no checkpoint resume)
            mock_audio.convert_to_wav.assert_called_once()

            # Verify resume_enabled is False
            assert processor.resume_enabled is False

    def test_resume_with_corrupted_checkpoint_restarts(self, tmp_path):
        """Test graceful handling of corrupted checkpoint."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            processor = DDSessionProcessor("test", resume=True)

            # Mock checkpoint manager to return None (simulating corrupted/missing checkpoint)
            mock_checkpoint_manager = MagicMock()
            mock_checkpoint_manager.latest.return_value = None  # No valid checkpoint
            processor.checkpoint_manager = mock_checkpoint_manager

            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock())
            processor.merger.merge_transcriptions = MagicMock(return_value=[])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process should succeed by starting from beginning
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify audio conversion was called (restart from beginning)
            mock_audio.convert_to_wav.assert_called_once()

            # Verify processing completed successfully
            assert result['success'] is True


# ============================================================================
# Error Handling & Graceful Degradation
# ============================================================================

class TestPipelineErrorHandling:
    """Test error handling and graceful degradation."""

    def test_continue_on_diarization_failure(self, monkeypatch, tmp_path):
        """Test pipeline continues if diarization fails."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.CheckpointManager'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.DiarizerFactory') as mock_diarizer_factory, \
             patch('src.pipeline.ClassifierFactory'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            # Mock diarizer to raise an exception
            mock_diarizer = MagicMock()
            mock_diarizer_factory.create.return_value = mock_diarizer
            mock_diarizer.diarize.side_effect = RuntimeError("Diarization failed")

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process should NOT raise exception (graceful degradation)
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=False,  # Enable diarization (but it will fail)
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify diarization was attempted
            mock_diarizer.diarize.assert_called_once()

            # Verify processing completed successfully despite diarization failure
            assert result['success'] is True

    def test_continue_on_classification_failure(self, monkeypatch, tmp_path):
        """Test pipeline continues if classification fails."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.CheckpointManager'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.ClassifierFactory') as mock_classifier_factory:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            # Mock classifier to raise an exception
            mock_classifier = MagicMock()
            mock_classifier.classify_segments.side_effect = RuntimeError("Classification failed")
            mock_classifier_factory.create.return_value = mock_classifier

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process should NOT raise exception (graceful degradation)
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=False,  # Enable classification (but it will fail)
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify classification was attempted
            mock_classifier.classify_segments.assert_called_once()

            # Verify processing completed successfully despite classification failure
            assert result['success'] is True

    def test_abort_on_conversion_failure(self, monkeypatch, tmp_path):
        """Test pipeline aborts on audio conversion failure."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.ClassifierFactory'):

            # Mock audio processor to raise an exception on conversion
            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.side_effect = RuntimeError("Audio conversion failed")

            processor = DDSessionProcessor("test", resume=False)

            # Process should raise exception (critical failure)
            with pytest.raises(RuntimeError, match="Audio conversion failed"):
                processor.process(
                    input_file=input_file,
                    output_dir=tmp_path,
                    skip_diarization=True,
                    skip_classification=True,
                    skip_snippets=True,
                    skip_knowledge=True,
                    is_test_run=True
                )

    def test_abort_on_transcription_failure(self, monkeypatch, tmp_path):
        """Test pipeline aborts if transcription fails."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.ClassifierFactory'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[MagicMock(spec=AudioChunk)])

            # Mock transcriber to raise an exception
            processor.transcriber.transcribe_chunk = MagicMock(
                side_effect=RuntimeError("Transcription failed")
            )

            # Process should raise exception (critical failure)
            with pytest.raises(RuntimeError, match="Transcription failed"):
                processor.process(
                    input_file=input_file,
                    output_dir=tmp_path,
                    skip_diarization=True,
                    skip_classification=True,
                    skip_snippets=True,
                    skip_knowledge=True,
                    is_test_run=True
                )

    def test_abort_on_zero_chunks(self, monkeypatch, tmp_path):
        """Test pipeline aborts if chunker returns zero chunks for a real run."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
                patch('src.pipeline.HybridChunker') as mock_chunker_cls, \
                patch('src.pipeline.StatusTracker'), \
                patch('src.pipeline.ClassifierFactory'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            mock_chunker = mock_chunker_cls.return_value
            mock_chunker.chunk_audio.return_value = []

            processor = DDSessionProcessor("test", resume=False)

            # Process should raise exception (critical failure)
            with pytest.raises(RuntimeError, match="Audio chunking resulted in zero segments"):
                processor.process(
                    input_file=input_file,
                    output_dir=tmp_path,
                    is_test_run=False  # This is a real run
                )

    def test_continue_on_zero_chunks_for_test_run(self, monkeypatch, tmp_path):
        """Test pipeline continues if chunker returns zero chunks for a test run."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
                patch('src.pipeline.HybridChunker') as mock_chunker_cls, \
                patch('src.pipeline.TranscriberFactory'), \
                patch('src.pipeline.StatusTracker'), \
                patch('src.pipeline.ClassifierFactory'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            mock_chunker = mock_chunker_cls.return_value
            mock_chunker.chunk_audio.return_value = []

            processor = DDSessionProcessor("test", resume=False)

            # Process should not raise exception
            processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                is_test_run=True  # This is a test run
            )


# ============================================================================
# Output Generation Tests
# ============================================================================

class TestPipelineOutputs:
    """Test output file generation."""

    def test_all_output_files_created(self, tmp_path, monkeypatch):
        """Test that all expected output files are created."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.CheckpointManager'):

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            processor = DDSessionProcessor("test", resume=False)

            # Mock formatter to return expected output files
            expected_outputs = {
                'full_txt': str(tmp_path / 'test_full.txt'),
                'ic_only_txt': str(tmp_path / 'test_ic_only.txt'),
                'ooc_only_txt': str(tmp_path / 'test_ooc_only.txt'),
                'structured_json': str(tmp_path / 'test_structured.json'),
                'full_srt': str(tmp_path / 'test_full.srt'),
                'ic_only_srt': str(tmp_path / 'test_ic_only.srt'),
                'ooc_only_srt': str(tmp_path / 'test_ooc_only.srt'),
            }

            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value=expected_outputs)
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process the file
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify formatter was called
            processor.formatter.save_all_formats.assert_called_once()

            # Verify output files are in result
            assert 'output_files' in result
            assert result['output_files'] == expected_outputs

    def test_output_directory_structure(self, tmp_path):
        """Test correct directory structure is created."""
        # The output directory structure is created by create_session_output_dir
        # which we've already tested. This test verifies the timestamped directory exists.
        from src.pipeline import create_session_output_dir

        session_dir = create_session_output_dir(tmp_path, "test_session")

        # Verify directory exists
        assert session_dir.exists()
        assert session_dir.is_dir()

        # Verify directory name format: YYYYMMDD_HHMMSS_test_session
        assert "test_session" in session_dir.name
        parts = session_dir.name.split("_")
        assert len(parts) >= 3

        # Verify it's under the base output directory
        assert session_dir.parent == tmp_path

    def test_statistics_included_in_output(self, monkeypatch, tmp_path):
        """Test statistics are generated and saved."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.CheckpointManager'), \
             patch('src.pipeline.StatisticsGenerator') as mock_stats_gen:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            # Mock statistics generator
            test_stats = {
                'total_duration': 60.0,
                'total_duration_formatted': '0:01:00',
                'ic_duration': 40.0,
                'ic_duration_formatted': '0:00:40',
                'ic_percentage': 66.7,
                'total_segments': 10,
                'ic_segments': 7,
                'ooc_segments': 3,
                'character_appearances': {}
            }
            mock_stats_gen.generate_stats.return_value = test_stats

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process the file
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify statistics were generated
            mock_stats_gen.generate_stats.assert_called_once()

            # Verify statistics are in result
            assert 'statistics' in result
            assert result['statistics'] == test_stats


# ============================================================================
# Status Tracking Tests
# ============================================================================

class TestPipelineStatusTracking:
    """Test status JSON creation and updates."""

    def test_status_json_created(self, tmp_path):
        """Test that status.json is created."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker') as mock_status_tracker:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock())
            processor.merger.merge_transcriptions = MagicMock(return_value=[])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process the file
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify StatusTracker.start_session was called
            mock_status_tracker.start_session.assert_called_once()

            # Verify StatusTracker.complete_session was called
            mock_status_tracker.complete_session.assert_called_once_with("test")

    def test_status_updated_per_stage(self, monkeypatch, tmp_path):
        """Test status.json updated after each stage."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker') as mock_status_tracker:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock())
            processor.merger.merge_transcriptions = MagicMock(return_value=[])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process the file
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify StatusTracker.update_stage was called multiple times
            # (once for each stage: audio conversion, chunking, transcription, merging, etc.)
            assert mock_status_tracker.update_stage.call_count > 0

    def test_status_shows_progress_percentage(self, monkeypatch, tmp_path):
        """Test progress percentage calculation."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker') as mock_status_tracker:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock())
            processor.merger.merge_transcriptions = MagicMock(return_value=[])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process the file
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,
                is_test_run=True
            )

            # Verify update_stage was called with stage numbers
            # Pipeline has 9 stages total, verify at least stages 1-4 were called
            # (audio, chunking, transcription, merging)
            calls = mock_status_tracker.update_stage.call_args_list
            stage_numbers = [call[0][1] for call in calls if len(call[0]) > 1]

            # Should have updates for multiple stages
            assert len(stage_numbers) > 0
            # Stage numbers should be between 1 and 9
            assert all(1 <= s <= 9 for s in stage_numbers if isinstance(s, int))


# ============================================================================
# Knowledge Extraction Tests
# ============================================================================

class TestPipelineKnowledgeExtraction:
    """Test campaign knowledge extraction."""

    def test_knowledge_extraction_when_enabled(self, monkeypatch, tmp_path):
        """Test knowledge extraction runs when enabled."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.KnowledgeExtractor') as mock_extractor_cls, \
             patch('src.pipeline.CampaignKnowledgeBase') as mock_kb_cls:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            mock_extractor = mock_extractor_cls.return_value
            mock_extractor.extract_knowledge.return_value = {
                'quests': [], 'npcs': [], 'plot_hooks': [], 'locations': [], 'items': []
            }

            mock_kb = mock_kb_cls.return_value

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.formatter.format_ic_only = MagicMock(return_value="IC text")
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process with knowledge extraction enabled
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=False,  # Enable knowledge extraction
                is_test_run=True
            )

            # Verify knowledge extraction was called
            mock_extractor.extract_knowledge.assert_called_once()
            mock_kb.merge_new_knowledge.assert_called_once()

    def test_knowledge_extraction_when_disabled(self, monkeypatch, tmp_path):
        """Test knowledge extraction skipped when disabled."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.KnowledgeExtractor') as mock_extractor_cls, \
             patch('src.pipeline.CampaignKnowledgeBase') as mock_kb_cls:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            # Process with knowledge extraction disabled
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=True,  # Skip knowledge extraction
                is_test_run=True
            )

            # Verify knowledge extractor was NOT called
            mock_extractor_cls.assert_not_called()
            mock_kb_cls.assert_not_called()

    def test_knowledge_merged_with_campaign(self, monkeypatch, tmp_path):
        """Test extracted knowledge is merged with campaign KB."""
        # Create test input file
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        # Mock all components
        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker'), \
             patch('src.pipeline.TranscriberFactory'), \
             patch('src.pipeline.DiarizerFactory'), \
             patch('src.pipeline.ClassifierFactory'), \
             patch('src.pipeline.TranscriptionMerger'), \
             patch('src.pipeline.TranscriptFormatter'), \
             patch('src.pipeline.AudioSnipper'), \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.KnowledgeExtractor') as mock_extractor_cls, \
             patch('src.pipeline.CampaignKnowledgeBase') as mock_kb_cls:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0

            mock_extractor = mock_extractor_cls.return_value
            test_knowledge = {
                'quests': [{'name': 'Test Quest'}],
                'npcs': [{'name': 'Test NPC'}],
                'plot_hooks': [],
                'locations': [],
                'items': []
            }
            mock_extractor.extract_knowledge.return_value = test_knowledge

            mock_kb = mock_kb_cls.return_value

            processor = DDSessionProcessor("test", resume=False)
            processor.chunker.chunk_audio = MagicMock(return_value=[])
            processor.transcriber.transcribe_chunk = MagicMock(return_value=Mock(
                text='test', start_time=0, end_time=1, confidence=0.9, words=[]
            ))
            processor.merger.merge_transcriptions = MagicMock(return_value=[
                Mock(text='test', start_time=0, end_time=1, confidence=0.9, words=[])
            ])
            processor.formatter.save_all_formats = MagicMock(return_value={})
            processor.formatter.format_ic_only = MagicMock(return_value="IC text")
            processor.snipper.export_segments = MagicMock(return_value={'segments_dir': None, 'manifest': None})

            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=False,
                is_test_run=True
            )

            # Verify knowledge was merged with campaign KB
            mock_kb.merge_new_knowledge.assert_called_once_with(test_knowledge, "test")


class TestPipelineResume:
    """Tests for pipeline checkpoint resume behaviour."""

    def test_resume_from_checkpoint_after_transcription_failure(self, monkeypatch, tmp_path):
        """Ensure pipeline resumes from checkpoint without rerunning earlier stages."""
        input_file = tmp_path / "test.m4a"
        input_file.touch()
        wav_file = tmp_path / "test.wav"
        wav_file.touch()

        audio_chunk = AudioChunk(
            audio=np.zeros(16000, dtype=np.float32),
            start_time=0.0,
            end_time=1.0,
            sample_rate=16000,
            chunk_index=0
        )
        transcription_segment = TranscriptionSegment(
            text="hello",
            start_time=0.0,
            end_time=1.0,
            confidence=0.9,
            words=[]
        )
        chunk_transcription = ChunkTranscription(
            chunk_index=0,
            chunk_start=0.0,
            chunk_end=1.0,
            segments=[transcription_segment],
            language="nl"
        )

        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker') as mock_chunker_cls, \
             patch('src.pipeline.TranscriberFactory') as mock_transcriber_factory, \
             patch('src.pipeline.TranscriptionMerger') as mock_merger_cls, \
             patch('src.pipeline.TranscriptFormatter') as mock_formatter_cls, \
             patch('src.pipeline.AudioSnipper') as mock_snipper_cls, \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.KnowledgeExtractor') as mock_extractor_cls, \
             patch('src.pipeline.CampaignKnowledgeBase') as mock_kb_cls, \
             patch('src.pipeline.DiarizerFactory') as mock_diarizer_factory, \
             patch('src.pipeline.ClassifierFactory') as mock_classifier_factory:

            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0
            mock_audio.load_audio_segment.return_value = (np.zeros(1600, dtype=np.float32), 16000)

            mock_chunker = mock_chunker_cls.return_value
            mock_chunker.chunk_audio.return_value = [audio_chunk]

            mock_transcriber = MagicMock()
            mock_transcriber_factory.create.return_value = mock_transcriber
            mock_transcriber.transcribe_chunk.side_effect = RuntimeError("bang")

            mock_merger = mock_merger_cls.return_value
            mock_merger.merge_transcriptions.return_value = [transcription_segment]

            mock_diarizer = MagicMock()
            mock_diarizer_factory.create.return_value = mock_diarizer
            mock_diarizer.diarize.return_value = ([], {})
            mock_diarizer.assign_speakers_to_transcription.return_value = [{
                "text": "hello",
                "start_time": 0.0,
                "end_time": 1.0,
                "speaker": "SPEAKER_00"
            }]

            mock_classifier = MagicMock()
            mock_classifier.classify_segments.return_value = []
            mock_classifier_factory.create.return_value = mock_classifier

            mock_formatter = mock_formatter_cls.return_value
            mock_formatter.save_all_formats.return_value = {
                "full": tmp_path / "full.txt",
                "ic_only": tmp_path / "ic.txt",
                "ooc_only": tmp_path / "ooc.txt",
                "json": tmp_path / "data.json",
                "srt_full": tmp_path / "full.srt",
                "srt_ic": tmp_path / "ic.srt",
                "srt_ooc": tmp_path / "ooc.srt",
            }
            mock_formatter.format_ic_only.return_value = "IC transcript"

            mock_snipper = mock_snipper_cls.return_value
            mock_snipper.export_segments.return_value = {'segments_dir': None, 'manifest': None}

            mock_extractor = mock_extractor_cls.return_value
            mock_extractor.extract_knowledge.return_value = {}
            mock_kb = mock_kb_cls.return_value

            processor = DDSessionProcessor("resume_test", resume=True)

            # First run should fail during transcription and leave checkpoints for earlier stages.
            with pytest.raises(RuntimeError, match="bang"):
                processor.process(
                    input_file=input_file,
                    output_dir=tmp_path,
                    skip_diarization=True,
                    skip_classification=True,
                    skip_snippets=True,
                    skip_knowledge=True,
                    is_test_run=True
                )
            assert mock_chunker.chunk_audio.call_count == 1

            # Configure mocks for resumed run
            mock_transcriber.transcribe_chunk.side_effect = None
            mock_transcriber.transcribe_chunk.return_value = chunk_transcription
            mock_chunker.chunk_audio.reset_mock()
            mock_chunker.chunk_audio.side_effect = AssertionError("chunker should not be called when resuming")

            # Run again; should resume from checkpoint and complete without chunker invocation.
            result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=True,
                skip_knowledge=False,
                is_test_run=True
            )

            assert result["success"] is True
            mock_extractor.extract_knowledge.assert_called_once()
            mock_kb.merge_new_knowledge.assert_called_once()

    def test_resume_skips_completed_stages(self, tmp_path):
        """Completed stages should not re-run and should load data from checkpoint blobs."""

        class DummyLock:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        input_file = tmp_path / "complete.m4a"
        input_file.touch()
        wav_file = tmp_path / "complete.wav"
        wav_file.touch()

        audio_chunk = AudioChunk(
            audio=np.zeros(16000, dtype=np.float32),
            start_time=0.0,
            end_time=1.0,
            sample_rate=16000,
            chunk_index=0,
        )
        transcription_segment = TranscriptionSegment(
            text="hello",
            start_time=0.0,
            end_time=1.0,
            confidence=0.9,
            words=[],
        )
        chunk_transcription = ChunkTranscription(
            chunk_index=0,
            chunk_start=0.0,
            chunk_end=1.0,
            segments=[transcription_segment],
            language="nl",
        )

        def init_manifest(target_path: Path) -> Path:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(json.dumps({"status": "in_progress", "segments": []}), encoding="utf-8")
            return target_path

        def noop_export(*args, **kwargs):
            return None

        with patch('src.pipeline.AudioProcessor') as mock_audio_cls, \
             patch('src.pipeline.HybridChunker') as mock_chunker_cls, \
             patch('src.pipeline.TranscriberFactory') as mock_transcriber_factory, \
             patch('src.pipeline.TranscriptionMerger') as mock_merger_cls, \
             patch('src.pipeline.TranscriptFormatter') as mock_formatter_cls, \
             patch('src.pipeline.AudioSnipper') as mock_snipper_cls, \
             patch('src.pipeline.StatusTracker'), \
             patch('src.pipeline.KnowledgeExtractor') as mock_extractor_cls, \
             patch('src.pipeline.CampaignKnowledgeBase') as mock_kb_cls, \
             patch('src.pipeline.DiarizerFactory') as mock_diarizer_factory, \
             patch('src.pipeline.ClassifierFactory') as mock_classifier_factory:

            mock_diarizer_factory.create.return_value = MagicMock()
            mock_classifier_factory.create.return_value = MagicMock()
            mock_audio = mock_audio_cls.return_value
            mock_audio.convert_to_wav.return_value = wav_file
            mock_audio.get_duration.return_value = 60.0
            mock_audio.load_audio_segment.return_value = (np.zeros(1600, dtype=np.float32), 16000)

            mock_chunker = mock_chunker_cls.return_value
            mock_chunker.chunk_audio.return_value = [audio_chunk]

            mock_transcriber = MagicMock()
            mock_transcriber_factory.create.return_value = mock_transcriber
            mock_transcriber.transcribe_chunk.return_value = chunk_transcription

            mock_merger = mock_merger_cls.return_value
            mock_merger.merge_transcriptions.return_value = [transcription_segment]

            mock_formatter = mock_formatter_cls.return_value
            mock_formatter.save_all_formats.return_value = {
                "full": str(tmp_path / "full.txt"),
                "ic_only": str(tmp_path / "ic.txt"),
                "ooc_only": str(tmp_path / "ooc.txt"),
                "json": str(tmp_path / "data.json"),
                "srt_full": str(tmp_path / "full.srt"),
                "srt_ic": str(tmp_path / "ic.srt"),
                "srt_ooc": str(tmp_path / "ooc.srt"),
            }
            mock_formatter.format_ic_only.return_value = "IC transcript"

            mock_snipper = mock_snipper_cls.return_value
            mock_snipper.initialize_manifest.side_effect = init_manifest
            mock_snipper.export_incremental.side_effect = noop_export
            mock_snipper._manifest_lock = DummyLock()

            mock_extractor = mock_extractor_cls.return_value
            mock_extractor.extract_knowledge.return_value = {
                "quests": [],
                "npcs": [],
                "plot_hooks": [],
                "locations": [],
                "items": [],
            }
            mock_kb = mock_kb_cls.return_value
            mock_kb.knowledge_file = tmp_path / "knowledge.json"

            processor = DDSessionProcessor("resume_skip_test", resume=True)
            processor.checkpoint_manager.clear = MagicMock()

            first_result = processor.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=False,
                skip_knowledge=False,
                is_test_run=True,
            )
            assert first_result["success"] is True
            processor.checkpoint_manager.clear.assert_called_once()
            blob_files = list((Config.OUTPUT_DIR / "_checkpoints" / processor.safe_session_id).glob("*.json.gz"))
            assert blob_files, "Expected compressed checkpoint payloads to be created"

            # Configure mocks to fail if any completed stage runs again.
            mock_chunker.chunk_audio.reset_mock()
            mock_transcriber.transcribe_chunk.reset_mock()
            mock_merger.merge_transcriptions.reset_mock()
            mock_formatter.save_all_formats.reset_mock()
            mock_snipper.initialize_manifest.reset_mock()
            mock_snipper.export_incremental.reset_mock()
            initial_extract_calls = mock_extractor.extract_knowledge.call_count

            mock_chunker.chunk_audio.side_effect = AssertionError("chunker should not run on resume")
            mock_transcriber.transcribe_chunk.side_effect = AssertionError("transcribe should not run on resume")
            mock_merger.merge_transcriptions.side_effect = AssertionError("merge should not run on resume")
            mock_formatter.save_all_formats.side_effect = AssertionError("formatter should not run on resume")
            mock_snipper.initialize_manifest.side_effect = AssertionError("manifest should not be created on resume")
            mock_snipper.export_incremental.side_effect = AssertionError("snipper should not run on resume")

            processor_resume = DDSessionProcessor("resume_skip_test", resume=True)
            resume_result = processor_resume.process(
                input_file=input_file,
                output_dir=tmp_path,
                skip_diarization=True,
                skip_classification=True,
                skip_snippets=False,
                skip_knowledge=False,
                is_test_run=True,
            )

            assert resume_result["success"] is True
            mock_chunker.chunk_audio.assert_not_called()
            mock_transcriber.transcribe_chunk.assert_not_called()
            mock_merger.merge_transcriptions.assert_not_called()
            mock_formatter.save_all_formats.assert_not_called()
            mock_snipper.export_incremental.assert_not_called()
            assert mock_extractor.extract_knowledge.call_count == initial_extract_calls

            # Cleanup checkpoints created for the session.
            processor_resume.checkpoint_manager.clear()

# ============================================================================
# Integration Tests (Slow)
# ============================================================================

@pytest.mark.slow
@pytest.mark.skip(reason="Template - not implemented - requires real audio file")
def test_pipeline_end_to_end_minimal(tmp_path):
    """
    Test complete pipeline with minimal options (no diarization/classification).

    Duration: ~2-3 minutes
    Requires: tests/fixtures/sample_30s.wav
    """
    # TODO: Use small test audio file (~30s)
    # TODO: Run with skip_diarization=True, skip_classification=True
    # TODO: Verify all outputs created
    # TODO: Verify transcript content is reasonable
    pass


@pytest.mark.slow
@pytest.mark.skip(reason="Template - not implemented - requires real audio file")
def test_pipeline_end_to_end_full_features(tmp_path):
    """
    Test complete pipeline with all features enabled.

    Duration: ~10-15 minutes
    Requires: tests/fixtures/sample_5min.wav
    """
    # TODO: Use larger test file (~5 min)
    # TODO: Run with all features enabled
    # TODO: Verify speaker labels present
    # TODO: Verify IC/OOC labels present
    # TODO: Verify knowledge extracted
    pass


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_audio(path: Path, duration: int, sample_rate: int = 16000):
    """
    Create a mock audio file for testing.

    Args:
        path: Output file path
        duration: Duration in seconds
        sample_rate: Sample rate in Hz

    TODO: Implement actual WAV file creation
    """
    raise NotImplementedError("Mock audio creation not implemented")


def create_mock_transcription(num_segments: int = 5):
    """
    Create mock transcription data.

    Returns:
        List of mock transcription segments

    TODO: Implement
    """
    raise NotImplementedError("Mock transcription creation not implemented")

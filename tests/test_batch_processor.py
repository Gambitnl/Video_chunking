"""Tests for batch processing module."""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from src.batch_processor import BatchProcessor, BatchReport, BatchResult


@pytest.fixture
def sample_batch_results():
    """Create sample batch results for testing reports."""
    return [
        BatchResult(
            file=Path("session1.m4a"),
            session_id="session1",
            status="success",
            start_time=datetime(2025, 10, 24, 10, 0, 0),
            end_time=datetime(2025, 10, 24, 10, 30, 0),
            processing_duration=1800.0,
            output_dir=Path("output/session1"),
            resumed_from_checkpoint=False,
        ),
        BatchResult(
            file=Path("session2.m4a"),
            session_id="session2",
            status="success",
            start_time=datetime(2025, 10, 24, 10, 35, 0),
            end_time=datetime(2025, 10, 24, 11, 0, 0),
            processing_duration=1500.0,
            output_dir=Path("output/session2"),
            resumed_from_checkpoint=True,
        ),
        BatchResult(
            file=Path("session3.m4a"),
            session_id="session3",
            status="failed",
            start_time=datetime(2025, 10, 24, 11, 5, 0),
            end_time=datetime(2025, 10, 24, 11, 10, 0),
            processing_duration=300.0,
            error="FileNotFoundError: Audio file corrupted",
        ),
    ]


class TestBatchResult:
    """Test BatchResult dataclass."""

    def test_batch_result_success_property(self):
        """Test success property returns correct value."""
        result = BatchResult(
            file=Path("test.m4a"),
            session_id="test",
            status="success",
            start_time=datetime.now(),
        )
        assert result.success is True
        assert result.failed is False

    def test_batch_result_failed_property(self):
        """Test failed property returns correct value."""
        result = BatchResult(
            file=Path("test.m4a"),
            session_id="test",
            status="failed",
            start_time=datetime.now(),
            error="Test error",
        )
        assert result.failed is True
        assert result.success is False

    def test_duration_str_with_duration(self):
        """Test duration formatting when processing_duration is set."""
        result = BatchResult(
            file=Path("test.m4a"),
            session_id="test",
            status="success",
            start_time=datetime.now(),
            processing_duration=3665.0,  # 1h 1m 5s
        )
        assert result.duration_str() == "1:01:05"

    def test_duration_str_without_duration(self):
        """Test duration formatting when processing_duration is None."""
        result = BatchResult(
            file=Path("test.m4a"),
            session_id="test",
            status="failed",
            start_time=datetime.now(),
        )
        assert result.duration_str() == "N/A"


class TestBatchReport:
    """Test BatchReport dataclass and methods."""

    def test_empty_batch_report(self):
        """Test batch report with no results."""
        report = BatchReport(start_time=datetime.now())
        assert report.successful_count == 0
        assert report.failed_count == 0
        assert report.resumed_count == 0

    def test_batch_report_counts(self, sample_batch_results):
        """Test batch report correctly counts results."""
        report = BatchReport(
            start_time=datetime(2025, 10, 24, 10, 0, 0),
            end_time=datetime(2025, 10, 24, 11, 10, 0),
            results=sample_batch_results,
            total_files=3,
        )

        assert report.successful_count == 2
        assert report.failed_count == 1
        assert report.resumed_count == 1
        assert report.total_duration == 4200.0  # 70 minutes

    def test_summary_markdown(self, sample_batch_results):
        """Test summary markdown generation."""
        report = BatchReport(
            start_time=datetime(2025, 10, 24, 10, 0, 0),
            end_time=datetime(2025, 10, 24, 11, 10, 0),
            results=sample_batch_results,
            total_files=3,
        )

        summary = report.summary_markdown()
        assert "## Batch Processing Summary" in summary
        assert "**Total Files**: 3" in summary
        assert "**Successful**: 2" in summary
        assert "**Failed**: 1" in summary
        assert "**Resumed from Checkpoint**: 1" in summary
        assert "**Total Time**: 1:10:00" in summary

    def test_full_markdown(self, sample_batch_results):
        """Test full markdown report generation."""
        report = BatchReport(
            start_time=datetime(2025, 10, 24, 10, 0, 0),
            end_time=datetime(2025, 10, 24, 11, 10, 0),
            results=sample_batch_results,
            total_files=3,
        )

        markdown = report.full_markdown()
        assert "# Batch Processing Report" in markdown
        assert "**Total Sessions**: 3" in markdown
        assert "## Successful Sessions" in markdown
        assert "## Failed Sessions" in markdown
        assert "session1.m4a" in markdown
        assert "session2.m4a ✓" in markdown  # Resumed from checkpoint
        assert "session3.m4a" in markdown
        assert "FileNotFoundError" in markdown

    def test_save_report(self, sample_batch_results, tmp_path):
        """Test saving report to file."""
        report = BatchReport(
            start_time=datetime(2025, 10, 24, 10, 0, 0),
            end_time=datetime(2025, 10, 24, 11, 10, 0),
            results=sample_batch_results,
            total_files=3,
        )

        report_path = tmp_path / "test_report.md"
        report.save(report_path)

        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "# Batch Processing Report" in content


class TestBatchProcessor:
    """Test BatchProcessor class."""

    def test_batch_processor_initialization(self):
        """Test batch processor initializes with correct defaults."""
        processor = BatchProcessor()
        assert processor.party_id is None
        assert processor.num_speakers == 4
        assert processor.resume_enabled is True

    def test_batch_processor_custom_config(self):
        """Test batch processor with custom configuration."""
        processor = BatchProcessor(
            party_id="test_party",
            num_speakers=5,
            resume_enabled=False,
            output_dir="custom/output",
        )
        assert processor.party_id == "test_party"
        assert processor.num_speakers == 5
        assert processor.resume_enabled is False
        assert processor.output_dir == Path("custom/output")

    @patch("src.batch_processor.DDSessionProcessor")
    def test_process_batch_empty_list(self, mock_processor_class):
        """Test batch processing with empty file list."""
        processor = BatchProcessor()
        report = processor.process_batch(files=[])

        assert report.total_files == 0
        assert report.successful_count == 0
        assert report.failed_count == 0
        assert report.end_time is not None

    @patch("src.batch_processor.DDSessionProcessor")
    def test_process_batch_successful_files(self, mock_processor_class, tmp_path):
        """Test batch processing with successful files."""
        # Create mock files
        file1 = tmp_path / "session1.m4a"
        file2 = tmp_path / "session2.m4a"
        file1.touch()
        file2.touch()

        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.checkpoint_manager.latest.return_value = None
        mock_processor.process.return_value = {"output_dir": "output/session1"}
        mock_processor_class.return_value = mock_processor

        # Process batch
        processor = BatchProcessor(resume_enabled=False)
        report = processor.process_batch(files=[file1, file2])

        # Verify results
        assert report.total_files == 2
        assert report.successful_count == 2
        assert report.failed_count == 0
        assert len(report.results) == 2
        assert all(r.success for r in report.results)

    @patch("src.batch_processor.DDSessionProcessor")
    def test_process_batch_with_failure(self, mock_processor_class, tmp_path):
        """Test batch processing handles failures gracefully."""
        # Create mock files
        file1 = tmp_path / "session1.m4a"
        file2 = tmp_path / "session2.m4a"
        file1.touch()
        file2.touch()

        # Mock the processor - first succeeds, second fails
        mock_processor = MagicMock()
        mock_processor.checkpoint_manager.latest.return_value = None
        mock_processor.process.side_effect = [
            {"output_dir": "output/session1"},
            RuntimeError("Processing failed"),
        ]
        mock_processor_class.return_value = mock_processor

        # Process batch
        processor = BatchProcessor(resume_enabled=False)
        report = processor.process_batch(files=[file1, file2])

        # Verify results
        assert report.total_files == 2
        assert report.successful_count == 1
        assert report.failed_count == 1
        assert report.results[0].success
        assert report.results[1].failed
        assert "Processing failed" in report.results[1].error

    @patch("src.batch_processor.DDSessionProcessor")
    def test_process_batch_with_resume(self, mock_processor_class, tmp_path):
        """Test batch processing resumes from checkpoint."""
        # Create mock file
        file1 = tmp_path / "session1.m4a"
        file1.touch()

        # Mock the processor with checkpoint
        mock_processor = MagicMock()
        mock_checkpoint_record = MagicMock()
        mock_checkpoint_record.stage = "transcription"
        mock_processor.checkpoint_manager.latest.return_value = (
            "transcription",
            mock_checkpoint_record,
        )
        mock_processor.process.return_value = {"output_dir": "output/session1"}
        mock_processor_class.return_value = mock_processor

        # Process batch with resume enabled
        processor = BatchProcessor(resume_enabled=True)
        report = processor.process_batch(files=[file1])

        # Verify results
        assert report.total_files == 1
        assert report.successful_count == 1
        assert report.resumed_count == 1
        assert report.results[0].resumed_from_checkpoint is True

    @patch("src.batch_processor.DDSessionProcessor")
    def test_process_batch_keyboard_interrupt(self, mock_processor_class, tmp_path):
        """Test batch processing stops on KeyboardInterrupt."""
        # Create mock files
        file1 = tmp_path / "session1.m4a"
        file2 = tmp_path / "session2.m4a"
        file1.touch()
        file2.touch()

        # Mock the processor to raise KeyboardInterrupt
        mock_processor = MagicMock()
        mock_processor.checkpoint_manager.latest.return_value = None
        mock_processor.process.side_effect = KeyboardInterrupt()
        mock_processor_class.return_value = mock_processor

        # Process batch
        processor = BatchProcessor(resume_enabled=False)

        with pytest.raises(KeyboardInterrupt):
            processor.process_batch(files=[file1, file2])

    @patch("src.batch_processor.DDSessionProcessor")
    def test_process_batch_skip_options(self, mock_processor_class, tmp_path):
        """Test batch processing passes skip options correctly."""
        # Create mock file
        file1 = tmp_path / "session1.m4a"
        file1.touch()

        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.checkpoint_manager.latest.return_value = None
        mock_processor.process.return_value = {"output_dir": "output/session1"}
        mock_processor_class.return_value = mock_processor

        # Process batch with skip options
        processor = BatchProcessor(resume_enabled=False)
        processor.process_batch(
            files=[file1],
            skip_diarization=True,
            skip_classification=True,
            skip_snippets=True,
            skip_knowledge=True,
        )

        # Verify skip options were passed
        mock_processor.process.assert_called_once_with(
            input_file=file1,
            output_dir=processor.output_dir,
            skip_diarization=True,
            skip_classification=True,
            skip_snippets=True,
            skip_knowledge=True,
        )

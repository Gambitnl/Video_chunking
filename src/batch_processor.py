"""Batch processing module for handling multiple sessions sequentially."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Dict, List, Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from .config import Config
from .logger import get_logger
from .pipeline import DDSessionProcessor


@dataclass
class BatchResult:
    """Result of processing a single file in a batch."""

    file: Path
    session_id: str
    status: str  # "success", "failed", "skipped"
    start_time: datetime
    end_time: Optional[datetime] = None
    processing_duration: Optional[float] = None
    error: Optional[str] = None
    output_dir: Optional[Path] = None
    resumed_from_checkpoint: bool = False

    @property
    def success(self) -> bool:
        """Return True if processing succeeded."""
        return self.status == "success"

    @property
    def failed(self) -> bool:
        """Return True if processing failed."""
        return self.status == "failed"

    def duration_str(self) -> str:
        """Format processing duration as human-readable string."""
        if self.processing_duration is None:
            return "N/A"
        return str(timedelta(seconds=int(self.processing_duration)))


@dataclass
class BatchReport:
    """Summary report for batch processing operation."""

    start_time: datetime
    end_time: Optional[datetime] = None
    results: List[BatchResult] = field(default_factory=list)
    total_files: int = 0

    @property
    def total_duration(self) -> Optional[float]:
        """Return total batch processing duration in seconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    @property
    def successful_count(self) -> int:
        """Count successfully processed files."""
        return sum(1 for r in self.results if r.success)

    @property
    def failed_count(self) -> int:
        """Count failed files."""
        return sum(1 for r in self.results if r.failed)

    @property
    def resumed_count(self) -> int:
        """Count files resumed from checkpoint."""
        return sum(1 for r in self.results if r.resumed_from_checkpoint)

    def summary_markdown(self) -> str:
        """Generate a concise summary in markdown format."""
        lines = ["## Batch Processing Summary"]
        lines.append(f"- **Total Files**: {self.total_files}")
        lines.append(f"- **Successful**: {self.successful_count}")
        lines.append(f"- **Failed**: {self.failed_count}")
        lines.append(f"- **Resumed from Checkpoint**: {self.resumed_count}")

        if self.total_duration:
            duration_str = str(timedelta(seconds=int(self.total_duration)))
            lines.append(f"- **Total Time**: {duration_str}")

        return "\n".join(lines)

    def full_markdown(self) -> str:
        """Generate complete batch processing report in markdown format."""
        lines = ["# Batch Processing Report\n"]
        lines.append(f"**Started**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if self.end_time:
            lines.append(
                f"**Completed**: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            duration_str = str(timedelta(seconds=int(self.total_duration)))
            lines.append(f"**Total Time**: {duration_str}\n")

        lines.append("## Summary\n")
        lines.append(f"- **Total Sessions**: {self.total_files}")
        lines.append(f"- **Successful**: {self.successful_count}")
        lines.append(f"- **Failed**: {self.failed_count}")
        lines.append(f"- **Resumed from Checkpoint**: {self.resumed_count}\n")

        # Successful sessions
        if self.successful_count > 0:
            lines.append("## Successful Sessions\n")
            lines.append("| Session | Duration | Output |")
            lines.append("|---------|----------|--------|")

            for result in self.results:
                if result.success:
                    duration = result.duration_str()
                    output = str(result.output_dir) if result.output_dir else "N/A"
                    checkpoint_mark = "✓" if result.resumed_from_checkpoint else ""
                    lines.append(
                        f"| {result.file.name} {checkpoint_mark} | {duration} | {output} |"
                    )
            lines.append("")

        # Failed sessions
        if self.failed_count > 0:
            lines.append("## Failed Sessions\n")
            lines.append("| Session | Error |")
            lines.append("|---------|-------|")

            for result in self.results:
                if result.failed:
                    error = result.error or "Unknown error"
                    # Truncate very long errors but preserve more context
                    if len(error) > 150:
                        error = error[:147] + "..."
                    lines.append(f"| {result.file.name} | {error} |")
            lines.append("")

        lines.append("---")
        lines.append(
            "\n_Generated by VideoChunking Batch Processor_"
        )

        return "\n".join(lines)

    def save(self, output_path: Path) -> None:
        """Save the full report to a markdown file."""
        output_path.write_text(self.full_markdown(), encoding="utf-8")


class BatchProcessor:
    """
    Process multiple D&D session recordings sequentially.

    Features:
    - Automatic checkpoint resumption for partially processed sessions
    - Graceful error handling (continue on failure)
    - Progress reporting with rich progress bars
    - Summary report generation
    """

    def __init__(
        self,
        party_id: Optional[str] = None,
        num_speakers: int = 4,
        resume_enabled: bool = True,
        output_dir: Optional[str] = None,
    ):
        """
        Initialize batch processor.

        Args:
            party_id: Party configuration ID to use for all sessions
            num_speakers: Expected number of speakers for all sessions
            resume_enabled: Whether to resume from checkpoints
            output_dir: Base output directory for all sessions
        """
        self.party_id = party_id
        self.num_speakers = num_speakers
        self.resume_enabled = resume_enabled
        self.output_dir = Path(output_dir) if output_dir else Config.OUTPUT_DIR
        self.logger = get_logger("batch_processor")
        self.console = Console()

        # Validate party_id if provided
        if self.party_id:
            from .party_config import PartyConfigManager
            party_manager = PartyConfigManager()
            if self.party_id not in party_manager.list_parties():
                self.logger.warning(
                    "Party ID '%s' not found. Processing will continue but may fail during session processing.",
                    self.party_id
                )

    def process_batch(
        self,
        files: List[Path],
        skip_diarization: bool = False,
        skip_classification: bool = False,
        skip_snippets: bool = False,
        skip_knowledge: bool = False,
    ) -> BatchReport:
        """
        Process multiple audio files sequentially.

        Args:
            files: List of audio file paths to process
            skip_diarization: Skip speaker diarization for all files
            skip_classification: Skip IC/OOC classification for all files
            skip_snippets: Skip audio snippet export for all files
            skip_knowledge: Skip campaign knowledge extraction for all files

        Returns:
            BatchReport with summary and individual results
        """
        report = BatchReport(
            start_time=datetime.now(),
            total_files=len(files),
        )

        self.logger.info("Starting batch processing of %d files", len(files))

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Processing sessions...", total=len(files)
            )

            for idx, file in enumerate(files, 1):
                progress.update(
                    task,
                    description=f"[cyan]Processing {idx}/{len(files)}: {file.name}",
                )

                result = self._process_file(
                    file=file,
                    skip_diarization=skip_diarization,
                    skip_classification=skip_classification,
                    skip_snippets=skip_snippets,
                    skip_knowledge=skip_knowledge,
                )

                report.results.append(result)

                # Log result
                if result.success:
                    status_msg = "✓ SUCCESS"
                    if result.resumed_from_checkpoint:
                        status_msg += " (resumed from checkpoint)"
                    self.logger.info("%s: %s", status_msg, file.name)
                else:
                    self.logger.error("✗ FAILED: %s - %s", file.name, result.error)

                progress.advance(task)

        report.end_time = datetime.now()
        self.logger.info(
            "Batch processing complete: %d successful, %d failed",
            report.successful_count,
            report.failed_count,
        )

        return report

    def _process_file(
        self,
        file: Path,
        skip_diarization: bool,
        skip_classification: bool,
        skip_snippets: bool,
        skip_knowledge: bool,
    ) -> BatchResult:
        """
        Process a single audio file.

        Args:
            file: Path to audio file
            skip_diarization: Skip speaker diarization
            skip_classification: Skip IC/OOC classification
            skip_snippets: Skip audio snippet export
            skip_knowledge: Skip campaign knowledge extraction

        Returns:
            BatchResult with processing outcome
        """
        session_id = file.stem
        result = BatchResult(
            file=file,
            session_id=session_id,
            status="failed",
            start_time=datetime.now(),
        )

        try:
            # Create processor for this session
            processor = DDSessionProcessor(
                session_id=session_id,
                party_id=self.party_id,
                num_speakers=self.num_speakers,
                resume=self.resume_enabled,
            )

            # Check if resuming from checkpoint
            if self.resume_enabled:
                latest = processor.checkpoint_manager.latest()
                if latest:
                    result.resumed_from_checkpoint = True
                    self.logger.info(
                        "Resuming session '%s' from checkpoint at stage '%s'",
                        session_id,
                        latest[0],
                    )

            # Process the file
            start = perf_counter()
            output_metadata = processor.process(
                input_file=file,
                output_dir=self.output_dir,
                skip_diarization=skip_diarization,
                skip_classification=skip_classification,
                skip_snippets=skip_snippets,
                skip_knowledge=skip_knowledge,
            )
            end = perf_counter()

            # Mark as successful
            result.status = "success"
            result.end_time = datetime.now()
            result.processing_duration = end - start
            result.output_dir = Path(output_metadata.get("output_dir", ""))

        except KeyboardInterrupt:
            # Re-raise keyboard interrupt to stop batch
            self.logger.warning("Batch processing interrupted by user")
            raise

        except FileNotFoundError as exc:
            result.status = "failed"
            result.end_time = datetime.now()
            result.error = f"File not found: {exc}"
            result.processing_duration = (
                datetime.now() - result.start_time
            ).total_seconds()

            self.logger.error(
                "Failed to process %s: File not accessible. Check file path and permissions.",
                file.name,
                exc_info=True,
            )

        except PermissionError as exc:
            result.status = "failed"
            result.end_time = datetime.now()
            result.error = f"Permission denied: {exc}"
            result.processing_duration = (
                datetime.now() - result.start_time
            ).total_seconds()

            self.logger.error(
                "Failed to process %s: Permission denied. Run with elevated privileges or check file permissions.",
                file.name,
                exc_info=True,
            )

        except Exception as exc:
            # Generic catch-all
            result.status = "failed"
            result.end_time = datetime.now()
            result.error = str(exc)
            result.processing_duration = (
                datetime.now() - result.start_time
            ).total_seconds()

            self.logger.error(
                "Failed to process %s: %s (may be retryable - check logs)",
                file.name,
                exc,
                exc_info=True,
            )

        return result

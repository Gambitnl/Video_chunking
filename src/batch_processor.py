"""\nProcess multiple D&D session recordings in batch mode.\n"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from rich.console import Console

from .config import Config
from .pipeline import DDSessionProcessor
from .logger import get_logger

console = Console()


@dataclass
class BatchReport:
    """Summary report for a completed batch process."""

    start_time: datetime
    end_time: Optional[datetime] = None
    total_files: int = 0
    processed_files: List[Dict[str, Any]] = field(default_factory=list)
    failed_files: List[Dict[str, Any]] = field(default_factory=list)
    resumed_files: List[str] = field(default_factory=list)

    def record_success(self, file: Path, duration: float, output_dir: Path, resumed: bool):
        self.processed_files.append({
            "file": str(file),
            "duration": duration,
            "output_dir": str(output_dir),
        })
        if resumed:
            self.resumed_files.append(str(file))

    def record_failure(self, file: Path, error: str):
        self.failed_files.append({"file": str(file), "error": error})

    def finalize(self):
        self.end_time = datetime.now()

    @property
    def total_duration(self) -> float:
        if not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    def summary_markdown(self) -> str:
        """Generate a markdown summary of the batch report."""
        report = [
            "# Batch Processing Report",
            f"**Started**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Completed**: {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else 'In Progress'}",
            f"**Total Time**: {self.total_duration:.2f}s",
            "",
            "## Summary",
            f"- **Total Sessions**: {self.total_files}",
            f"- **Successful**: {len(self.processed_files)}",
            f"- **Failed**: {len(self.failed_files)}",
            f"- **Resumed from Checkpoint**: {len(self.resumed_files)}",
            "",
        ]

        if self.processed_files:
            report.append("### Successful")
            report.append("| Session | Processing Time | Output |")
            report.append("|---|---|---|")
            for item in self.processed_files:
                report.append(f"| {Path(item['file']).name} | {item['duration']:.2f}s | {item['output_dir']} |")
            report.append("")

        if self.failed_files:
            report.append("### Failed")
            report.append("| Session | Error |")
            report.append("|---|---|")
            for item in self.failed_files:
                report.append(f"| {Path(item['file']).name} | {item['error']} |")
            report.append("")

        return "\n".join(report)
    
    def save(self, path: Path):
        """Save the markdown report to a file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.summary_markdown(), encoding="utf-8")


class BatchProcessor:
    """Process multiple sessions with retry and resumption."""

    def __init__( 
        self,
        party_id: Optional[str] = None,
        num_speakers: int = 4,
        resume_enabled: bool = True,
        output_dir: Optional[str] = None,
    ):
        self.party_id = party_id
        self.num_speakers = num_speakers
        self.resume_enabled = resume_enabled
        self.output_dir = Path(output_dir) if output_dir else None
        self.logger = get_logger("DDSessionProcessor.batch")

    def process_batch(
        self,
        files: List[Path],
        skip_diarization: bool = False,
        skip_classification: bool = False,
        skip_snippets: bool = False,
        skip_knowledge: bool = False,
    ) -> BatchReport:
        """Process multiple files sequentially."""
        report = BatchReport(start_time=datetime.now(), total_files=len(files))

        for i, file in enumerate(files):
            session_id = file.stem
            console.print(f"\n[bold]Processing file {i+1}/{len(files)}: {file.name}[/bold]")

            try:
                processor = DDSessionProcessor(
                    session_id=session_id,
                    num_speakers=self.num_speakers,
                    party_id=self.party_id,
                    resume=self.resume_enabled,
                )

                start_time = time.perf_counter()
                
                result = processor.process(
                    input_file=file,
                    output_dir=self.output_dir,
                    skip_diarization=skip_diarization,
                    skip_classification=skip_classification,
                    skip_snippets=skip_snippets,
                    skip_knowledge=skip_knowledge,
                )
                
                duration = time.perf_counter() - start_time
                
                output_dir = result.get('output_files', {}).get('full_transcript')
                if output_dir:
                    output_dir = Path(output_dir).parent

                report.record_success(file, duration, output_dir, processor.checkpoint_manager.latest() is not None)

            except Exception as e:
                self.logger.error(f"Failed to process {file}: {e}", exc_info=True)
                report.record_failure(file, str(e))
                console.print(f"[red]✗ Error processing {file.name}: {e}[/red]")


        report.finalize()
        return report
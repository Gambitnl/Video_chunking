"""File processing history tracker for detecting re-processed files."""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from .config import Config


@dataclass
class ProcessingRecord:
    """Record of a processed file."""
    filename: str
    file_hash: str
    file_size: int
    session_id: str
    campaign_id: Optional[str]
    first_processed: str  # ISO format timestamp
    last_processed: str  # ISO format timestamp
    process_count: int
    processing_stage: str  # Stage where processing completed or failed
    status: str  # completed, failed, in_progress
    output_path: Optional[str]


class FileProcessingTracker:
    """Tracks file processing history to detect duplicates and show progress."""

    STAGES = [
        "uploaded",
        "audio_conversion",
        "chunking",
        "transcription",
        "diarization",
        "classification",
        "knowledge_extraction",
        "completed"
    ]

    def __init__(self, tracking_file: Optional[Path] = None):
        self.tracking_file = tracking_file or (Config.PROJECT_ROOT / "logs" / "processed_files.json")
        self.records = self._load_records()

    def _load_records(self) -> Dict[str, ProcessingRecord]:
        """Load processing records from JSON."""
        if not self.tracking_file.exists():
            return {}

        try:
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            records = {}
            for file_hash, record_data in data.items():
                records[file_hash] = ProcessingRecord(**record_data)

            return records
        except Exception as e:
            print(f"Warning: Could not load processing records: {e}")
            return {}

    def _save_records(self):
        """Save processing records to JSON."""
        self.tracking_file.parent.mkdir(exist_ok=True, parents=True)

        data = {}
        for file_hash, record in self.records.items():
            data[file_hash] = asdict(record)

        with open(self.tracking_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def calculate_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
        """Calculate SHA256 hash of file for duplicate detection."""
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)

        return sha256.hexdigest()

    def check_file(self, file_path: Path) -> Optional[ProcessingRecord]:
        """Check if file has been processed before. Returns existing record if found."""
        file_hash = self.calculate_file_hash(file_path)
        return self.records.get(file_hash)

    def record_processing_start(
        self,
        file_path: Path,
        session_id: str,
        campaign_id: Optional[str] = None
    ) -> str:
        """Record that processing has started for a file. Returns file hash."""
        file_hash = self.calculate_file_hash(file_path)
        now = datetime.utcnow().isoformat()

        existing_record = self.records.get(file_hash)

        if existing_record:
            # File was processed before - update
            existing_record.last_processed = now
            existing_record.process_count += 1
            existing_record.processing_stage = "uploaded"
            existing_record.status = "in_progress"
            existing_record.session_id = session_id  # Update with new session ID
            if campaign_id:
                existing_record.campaign_id = campaign_id
        else:
            # New file
            self.records[file_hash] = ProcessingRecord(
                filename=file_path.name,
                file_hash=file_hash,
                file_size=file_path.stat().st_size,
                session_id=session_id,
                campaign_id=campaign_id,
                first_processed=now,
                last_processed=now,
                process_count=1,
                processing_stage="uploaded",
                status="in_progress",
                output_path=None
            )

        self._save_records()
        return file_hash

    def update_stage(self, file_hash: str, stage: str):
        """Update the processing stage for a file."""
        if file_hash not in self.records:
            return

        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}. Must be one of {self.STAGES}")

        record = self.records[file_hash]
        record.processing_stage = stage
        record.last_processed = datetime.utcnow().isoformat()

        if stage == "completed":
            record.status = "completed"

        self._save_records()

    def record_completion(
        self,
        file_hash: str,
        output_path: Optional[Path] = None
    ):
        """Mark file processing as completed."""
        if file_hash not in self.records:
            return

        record = self.records[file_hash]
        record.processing_stage = "completed"
        record.status = "completed"
        record.last_processed = datetime.utcnow().isoformat()

        if output_path:
            record.output_path = str(output_path)

        self._save_records()

    def record_failure(self, file_hash: str, failed_stage: str):
        """Mark file processing as failed at a specific stage."""
        if file_hash not in self.records:
            return

        record = self.records[file_hash]
        record.processing_stage = failed_stage
        record.status = "failed"
        record.last_processed = datetime.utcnow().isoformat()

        self._save_records()

    def get_processing_history(self, limit: Optional[int] = None) -> List[ProcessingRecord]:
        """Get processing history, optionally limited to N most recent."""
        records = sorted(
            self.records.values(),
            key=lambda r: r.last_processed,
            reverse=True
        )

        if limit:
            return records[:limit]

        return records

    def get_stage_progress(self, file_hash: str) -> Dict[str, bool]:
        """Get progress through pipeline stages."""
        if file_hash not in self.records:
            return {stage: False for stage in self.STAGES}

        record = self.records[file_hash]
        current_stage_idx = self.STAGES.index(record.processing_stage) if record.processing_stage in self.STAGES else 0

        return {
            stage: i <= current_stage_idx
            for i, stage in enumerate(self.STAGES)
        }

"""Data models for JavaScript metadata classification."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ProcessingStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class MetadataRecord:
    """Represents a parsed metadata record from a JS file."""
    note_unid: str
    sys_name: str
    status: str
    file_name: str
    is_valid: bool = True
    parse_errors: list = field(default_factory=list)


@dataclass
class ClassificationResult:
    """Result of classifying records by sys_name."""
    sys_name: str
    total_records: int
    unique_note_count: int
    note_unids: list = field(default_factory=list)


@dataclass
class ProcessingStats:
    """Real-time processing statistics."""
    total_files_found: int = 0
    files_processed: int = 0
    files_remaining: int = 0
    valid_records: int = 0
    cancelled_records: int = 0
    files_with_errors: int = 0
    unique_systems: int = 0
    elapsed_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0
    files_per_second: float = 0.0
    status: ProcessingStatus = ProcessingStatus.PENDING
    current_file: str = ""
    current_system: str = ""
    current_status: str = ""

    def to_dict(self) -> dict:
        return {
            "total_files_found": self.total_files_found,
            "files_processed": self.files_processed,
            "files_remaining": self.files_remaining,
            "valid_records": self.valid_records,
            "cancelled_records": self.cancelled_records,
            "files_with_errors": self.files_with_errors,
            "unique_systems": self.unique_systems,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "estimated_remaining_seconds": round(self.estimated_remaining_seconds, 2),
            "files_per_second": round(self.files_per_second, 2),
            "status": self.status.value,
            "current_file": self.current_file,
            "current_system": self.current_system,
            "current_status": self.current_status,
        }


@dataclass
class LogEntry:
    """A log entry for processing activities."""
    timestamp: datetime
    file_name: str
    action: str
    status: str
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "file_name": self.file_name,
            "action": self.action,
            "status": self.status,
            "error_message": self.error_message or "",
        }


@dataclass
class SkippedFile:
    """Record of a skipped file."""
    file_name: str
    reason: str

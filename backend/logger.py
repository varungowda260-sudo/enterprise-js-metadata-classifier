"""
Logging system for JavaScript Metadata Classification.

Provides comprehensive logging of processing activities.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from models import LogEntry


class ProcessingLogger:
    """
    Logger for tracking processing activities.
    Maintains in-memory log with export capabilities.
    """

    def __init__(self, max_entries: int = 100000):
        self.entries: List[LogEntry] = []
        self.max_entries = max_entries

    def log(
        self,
        file_name: str,
        action: str,
        status: str,
        error_message: Optional[str] = None,
        result: str = "",
        reason: str = ""
    ) -> LogEntry:
        """
        Log a processing activity.
        """

        entry = LogEntry(
            timestamp=datetime.now(),
            file_name=file_name,
            action=action,
            status=status,
            result=result,
            reason=reason,
            error_message=error_message
        )

        self.entries.append(entry)

        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

        return entry

    def log_parse_success(self, file_name: str) -> LogEntry:
        """Log successful parsing."""
        return self.log(
            file_name=file_name,
            action="Completed",
            status="success",
            result="Accepted",
            reason="Passed all validation filters"
        )

    def log_parse_error(self, file_name: str, error: str) -> LogEntry:
        """Log parsing error."""
        return self.log(
            file_name=file_name,
            action="Completed",
            status="error",
            error_message=error,
            result="Failed",
            reason=error
        )

    def log_filter_skip(self, file_name: str, reason: str) -> LogEntry:
        """Log filtered/skipped record."""
        return self.log(
            file_name=file_name,
            action="Completed",
            status="success",
            result="Rejected",
            reason=reason
        )

    def log_classify_success(self, file_name: str) -> LogEntry:
        """Log successful classification."""
        return self.log(
            file_name=file_name,
            action="Completed",
            status="success",
            result="Accepted",
            reason="Passed all validation filters"
        )

    def get_entries(self) -> List[LogEntry]:
        """Get all log entries."""
        return self.entries

    def get_entries_by_status(self, status: str) -> List[LogEntry]:
        """Filter entries by status."""
        return [e for e in self.entries if e.status == status]

    def get_errors(self) -> List[LogEntry]:
        """Get all error entries."""
        return self.get_entries_by_status("error")

    def to_dict_list(self) -> List[dict]:
        """Convert all entries to dictionary format."""
        return [e.to_dict() for e in self.entries]

    def to_json(self) -> str:
        """Export log as JSON string."""
        return json.dumps(self.to_dict_list(), indent=2)

    def to_csv(self) -> str:
        """Export log as CSV string."""
        if not self.entries:
            return "timestamp,file_name,action,status,error_message\n"

        lines = ["timestamp,file_name,action,status,error_message"]
        for entry in self.entries:
            # Escape commas and quotes in fields
            ts = entry.timestamp.isoformat()
            fn = entry.file_name.replace('"', '""')
            act = entry.action
            st = entry.status
            err = (entry.error_message or "").replace('"', '""').replace('\n', ' ')
            lines.append(f'"{ts}","{fn}","{act}","{st}","{err}"')

        return '\n'.join(lines)

    def save_to_file(self, file_path: Path, format: str = "json") -> None:
        """
        Save log to file.

        Args:
            file_path: Path to save the log
            format: Output format ("json" or "csv")
        """
        content = self.to_json() if format == "json" else self.to_csv()
        Path(file_path).write_text(content, encoding='utf-8')

    def clear(self) -> None:
        """Clear all log entries."""
        self.entries.clear()

    def get_summary(self) -> dict:
        """Get summary statistics of the log."""
        total = len(self.entries)
        if total == 0:
            return {
                "total_entries": 0,
                "by_status": {},
                "by_action": {}
            }

        by_status = {}
        by_action = {}

        for entry in self.entries:
            by_status[entry.status] = by_status.get(entry.status, 0) + 1
            by_action[entry.action] = by_action.get(entry.action, 0) + 1

        return {
            "total_entries": total,
            "by_status": by_status,
            "by_action": by_action
        }

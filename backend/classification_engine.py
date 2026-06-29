"""
Classification Engine for JavaScript Metadata.

Groups filtered records by sys_name and provides analysis results.
"""
from collections import defaultdict
from typing import Dict, List
from models import MetadataRecord, ClassificationResult


class ClassificationEngine:
    """
    Classification engine that groups records by system name
    and tracks unique note IDs.
    """

    def __init__(self):
        self.classifications: Dict[str, ClassificationResult] = {}
        self._records_by_system: Dict[str, List[MetadataRecord]] = defaultdict(list)

    def classify(self, records: List[MetadataRecord]) -> Dict[str, ClassificationResult]:
        """
        Classify records by sys_name.

        Args:
            records: List of valid, filtered records

        Returns:
            Dictionary mapping sys_name to ClassificationResult
        """
        self.classifications.clear()
        self._records_by_system.clear()

        # Group records by sys_name
        for record in records:
            if record.sys_name:
                self._records_by_system[record.sys_name].append(record)

        # Create classification results for each system
        for sys_name, sys_records in self._records_by_system.items():
            # Collect unique note_unids
            unique_unids = set()
            status_note_map = defaultdict(list)

            for r in sys_records:
                if r.note_unid:
                    unique_unids.add(r.note_unid)
                     status = (r.status or "").strip()
                     if r.note_unid not in status_note_map[status]:
                         status_note_map[status].append(r.note_unid)

                       
            # Count occurrences of each status
            status_counts = {}
            
            for r in sys_records:
                status = (r.status or "").strip()
            
                if status:
                    status_counts[status] = status_counts.get(status, 0) + 1
            status_summary = ", ".join(
                f"{status} ({count})"
                for status, count in sorted(
                    status_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
            )
        )
            
            result = ClassificationResult(
                sys_name=sys_name,
                total_records=len(sys_records),

                valid_records=sum(
                    1 for r in sys_records
                    if r.result == "Accepted"
                ),

                status_summary=status_summary,

                unique_note_count=len(unique_unids),

                note_unids=sorted(list(unique_unids))

                status_note_map=dict(status_note_map)
            )

            self.classifications[sys_name] = result

        return self.classifications

    def get_classification(self, sys_name: str) -> ClassificationResult | None:
        """Get classification result for a specific system."""
        return self.classifications.get(sys_name)

    def get_all_classifications(self) -> List[ClassificationResult]:
        """Get all classification results sorted by sys_name."""
        return sorted(self.classifications.values(), key=lambda x: x.sys_name)

    def get_unique_systems_count(self) -> int:
        """Get count of unique systems."""
        return len(self.classifications)

    def get_total_records(self) -> int:
        """Get total record count across all systems."""
        return sum(c.total_records for c in self.classifications.values())

    def search(
        self,
        sys_name: str = None,
        note_unid: str = None,
        status: str = None
    ) -> List[ClassificationResult]:
        """
        Search classifications by various criteria.

        Args:
            sys_name: Filter by system name (partial match)
            note_unid: Filter by containing this note_unid
            status: Filter by status (requires access to original records)

        Returns:
            List of matching ClassificationResults
        """
        results = []

        for sys, classification in self.classifications.items():
            match = True

            if sys_name and sys_name.lower() not in sys.lower():
                match = False

            if note_unid:
                # Check if any note_unid contains the search term
                found = any(
                    note_unid.lower() in uid.lower()
                    for uid in classification.note_unids
                )
                if not found:
                    match = False

            if match:
                results.append(classification)

        return sorted(results, key=lambda x: x.sys_name)

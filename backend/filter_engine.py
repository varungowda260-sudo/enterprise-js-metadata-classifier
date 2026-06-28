"""
Filter Engine for JavaScript Metadata Classification.

This engine applies configurable filter rules to determine which records
should be included or excluded from the classification.

The engine is designed to be extensible - new filter rules can be added
without modifying the parser or core classification logic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from models import MetadataRecord


class FilterOperator(Enum):
    """Supported filter operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class FilterAction(Enum):
    """Action to take when filter matches."""
    INCLUDE = "include"
    EXCLUDE = "exclude"


@dataclass
class FilterRule:
    """A single filter rule."""
    field: str  # note_unid, sys_name, status, etc.
    operator: FilterOperator
    value: Any
    action: FilterAction
    case_sensitive: bool = False
    enabled: bool = True
    description: Optional[str] = None


class Filter(ABC):
    """Abstract base class for filters."""

    @abstractmethod
    def matches(self, record: MetadataRecord) -> bool:
        """Check if record matches this filter."""
        pass

    @abstractmethod
    def get_action(self) -> FilterAction:
        """Get the action for matching records."""
        pass


class StatusFilter(Filter):
    """
    Filter for status field.
    Default implementation: exclude records where status == "Cancel" (case insensitive).
    """

    def __init__(
        self,
        excluded_statuses: list[str] = None,
        case_sensitive: bool = False
    ):
        self.excluded_statuses = [s.lower() for s in (excluded_statuses or ["Cancel"])]
        self.case_sensitive = case_sensitive

    def matches(self, record: MetadataRecord) -> bool:
        """Check if status should be excluded."""
        if not record.status:
            return False

        status_to_check = record.status if self.case_sensitive else record.status.lower()
        return status_to_check in self.excluded_statuses

    def get_action(self) -> FilterAction:
        return FilterAction.EXCLUDE


class RuleBasedFilter(Filter):
    """Filter based on configurable rules."""

    def __init__(self, rule: FilterRule):
        self.rule = rule

    def _get_field_value(self, record: MetadataRecord) -> Optional[str]:
        """Get the field value from the record."""
        field_map = {
            "note_unid": record.note_unid,
            "sys_name": record.sys_name,
            "status": record.status,
            "file_name": record.file_name,
        }
        return field_map.get(self.rule.field)

    def matches(self, record: MetadataRecord) -> bool:
        """Check if record matches the filter rule."""
        if not self.rule.enabled:
            return False

        value = self._get_field_value(record)
        filter_value = self.rule.value

        if not self.rule.case_sensitive:
            if isinstance(value, str):
                value = value.lower()
            if isinstance(filter_value, str):
                filter_value = filter_value.lower()
            elif isinstance(filter_value, list):
                filter_value = [v.lower() if isinstance(v, str) else v for v in filter_value]

        operator = self.rule.operator

        if operator == FilterOperator.EQUALS:
            return value == filter_value
        elif operator == FilterOperator.NOT_EQUALS:
            return value != filter_value
        elif operator == FilterOperator.CONTAINS:
            return filter_value in value if value else False
        elif operator == FilterOperator.NOT_CONTAINS:
            return filter_value not in value if value else True
        elif operator == FilterOperator.STARTS_WITH:
            return value.startswith(filter_value) if value else False
        elif operator == FilterOperator.ENDS_WITH:
            return value.endswith(filter_value) if value else False
        elif operator == FilterOperator.IN:
            return value in filter_value if value else False
        elif operator == FilterOperator.NOT_IN:
            return value not in filter_value if value else True
        elif operator == FilterOperator.IS_NULL:
            return not value
        elif operator == FilterOperator.IS_NOT_NULL:
            return bool(value)

        return False

    def get_action(self) -> FilterAction:
        return self.rule.action


class FilterEngine:
    """
    Filter engine that applies multiple filter rules.
    Rules are evaluated in order - first match wins.
    """

    def __init__(self):
        self.filters: list[Filter] = []
        self._initialize_default_filters()

    def _initialize_default_filters(self):
        """Initialize with default filter rules."""
        # Default: exclude cancelled records
        self.add_filter(StatusFilter(excluded_statuses=["Cancel"]))

    def add_filter(self, filter_obj: Filter) -> None:
        """Add a filter to the engine."""
        self.filters.append(filter_obj)

    def add_rule(self, rule: FilterRule) -> None:
        """Add a filter rule."""
        self.add_filter(RuleBasedFilter(rule))

    def clear_filters(self) -> None:
        """Remove all filters."""
        self.filters.clear()

    def reset_to_default(self) -> None:
        """Reset to default filters."""
        self.filters.clear()
        self._initialize_default_filters()

    def should_include(self, record: MetadataRecord) -> tuple[bool, str]:
        """
        Determine if a record should be included in classification.

        Returns:
            Tuple of (should_include, reason)
        """
        if not record.is_valid:
            return False, "Invalid record - missing required fields"

        for f in self.filters:
            if f.matches(record):
                action = f.get_action()
                if action == FilterAction.EXCLUDE:
                    return False, f"Excluded by filter: {type(f).__name__}"
                elif action == FilterAction.INCLUDE:
                    return True, "Included by filter"

        # Default: include if no filters matched
        return True, "No filter rules matched - included by default"

    def filter_records(
        self,
        records: list[MetadataRecord]
    ) -> tuple[list[MetadataRecord], list[MetadataRecord]]:
        """
        Filter a list of records.

        Returns:
            Tuple of (included_records, excluded_records)
        """
        included = []
        excluded = []

        for record in records:
            should_include, reason = self.should_include(record)
            if should_include:
                included.append(record)
            else:
                excluded.append(record)

        return included, excluded

#!/usr/bin/env python3
"""
Test script to verify the parser works with sample files.
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from parser import parse_js_metadata_file
from filter_engine import FilterEngine
from logger import ProcessingLogger

def test_parser():
    """Test the parser with sample files."""
    sample_dir = Path(__file__).parent.parent / "sample_files"

    if not sample_dir.exists():
        print("Sample directory not found")
        return False

    js_files = list(sample_dir.rglob("*.js"))
    print(f"Found {len(js_files)} sample files:")

    filter_engine = FilterEngine()
    logger = ProcessingLogger()

    results = []

    for js_file in js_files:
        print(f"\n--- Processing: {js_file.name} ---")

        record = parse_js_metadata_file(js_file)

        print(f"  note_unid: {record.note_unid or 'MISSING'}")
        print(f"  sys_name: {record.sys_name or 'MISSING'}")
        print(f"  status: {record.status or 'MISSING'}")
        print(f"  is_valid: {record.is_valid}")

        if not record.is_valid:
            print(f"  errors: {record.parse_errors}")

        should_include, reason = filter_engine.should_include(record)
        print(f"  include: {should_include} ({reason})")

        if should_include:
            results.append(record)
        else:
            logger.log_filter_skip(record.file_name, reason)

    print(f"\n\n=== SUMMARY ===")
    print(f"Total files: {len(js_files)}")
    print(f"Valid records: {len(results)}")
    print(f"Filtered out: {len(logger.get_entries_by_status('skipped'))}")

    # Group by sys_name
    from collections import defaultdict
    by_system = defaultdict(list)
    for r in results:
        by_system[r.sys_name].append(r.note_unid)

    print(f"\n{len(by_system)} unique systems:")
    for sys_name, unids in sorted(by_system.items()):
        unique_unids = set(unids)
        print(f"  {sys_name}: {len(unids)} records, {len(unique_unids)} unique UNIDs")

    return True

if __name__ == "__main__":
    test_parser()

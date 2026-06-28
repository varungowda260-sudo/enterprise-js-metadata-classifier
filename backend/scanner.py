"""
Scanner module for discovering JavaScript files.

Handles ZIP extraction and recursive directory scanning.
"""
import asyncio
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from models import MetadataRecord, SkippedFile, ProcessingStats, ProcessingStatus
from parser import parse_js_metadata_file
from filter_engine import FilterEngine
from logger import ProcessingLogger
from classification_engine import ClassificationEngine


class FileScanner:
    """
    Scanner for discovering and processing JavaScript metadata files.
    Supports ZIP archives and directory recursion.
    """

    def __init__(
        self,
        filter_engine: FilterEngine,
        logger: ProcessingLogger,
        max_workers: int = 8
    ):
        self.filter_engine = filter_engine
        self.logger = logger
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Processing state
        self.stats = ProcessingStats()
        self.is_paused = False
        self.is_cancelled = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused by default

        # Results storage
        self.valid_records: List[MetadataRecord] = []
        self.cancelled_records: List[MetadataRecord] = []
        self.skipped_files: List[SkippedFile] = []
        self.temp_dirs: List[Path] = []

    def discovered_js_files(self, directory: Path) -> List[Path]:
        """
        Recursively discover all .js files in a directory.

        Args:
            directory: Root directory to scan

        Returns:
            List of Path objects for .js files
        """
        js_files = []
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() == ".js":
                js_files.append(path)
        return js_files

    def extract_zip(self, zip_path: Path, extract_dir: Optional[Path] = None) -> Path:
        """
        Extract a ZIP archive and return the extraction directory.

        Args:
            zip_path: Path to ZIP file
            extract_dir: Optional extraction directory (creates temp if None)

        Returns:
            Path to extraction directory
        """
        if extract_dir is None:
            extract_dir = Path(tempfile.mkdtemp(prefix="js_metadata_"))
            self.temp_dirs.append(extract_dir)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        return extract_dir

    async def _process_file(self, file_path: Path) -> Tuple[Optional[MetadataRecord], Optional[SkippedFile]]:
        """
        Process a single JavaScript file.

        Returns:
            Tuple of (record, skipped_file) - one will be None
        """
        # Wait if paused
        await self._pause_event.wait()

        if self.is_cancelled:
            return None, None

        try:
            # Parse the file
            record = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                parse_js_metadata_file,
                file_path
            )

            if not record.is_valid:
                skipped = SkippedFile(
                    file_name=file_path.name,
                    reason="; ".join(record.parse_errors)
                )
                self.logger.log_parse_error(file_path.name, "; ".join(record.parse_errors))
                return None, skipped

            self.logger.log_parse_success(file_path.name)

            # Apply filter
            should_include, reason = self.filter_engine.should_include(record)

            if should_include:
                self.logger.log_classify_success(file_path.name)
                return record, None
            else:
                self.logger.log_filter_skip(file_path.name, reason)
                return None, SkippedFile(file_name=file_path.name, reason=reason)

        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            self.logger.log_parse_error(file_path.name, error_msg)
            return None, SkippedFile(file_name=file_path.name, reason=error_msg)

    async def scan_directory(
        self,
        directory: Path,
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[MetadataRecord], List[MetadataRecord], List[SkippedFile], ProcessingStats]:
        """
        Scan a directory for JS files and process them.

        Args:
            directory: Root directory to scan
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (valid_records, cancelled_records, skipped_files, stats)
        """
        # Reset state
        self.valid_records.clear()
        self.cancelled_records.clear()
        self.skipped_files.clear()
        self.stats = ProcessingStats(status=ProcessingStatus.RUNNING)
        self.is_cancelled = False
        self.is_paused = False

        # Discover files
        import time
        start_time = time.time()

        js_files = await asyncio.get_event_loop().run_in_executor(
            None,
            self.discovered_js_files,
            directory
        )

        self.stats.total_files_found = len(js_files)
        self.stats.files_remaining = len(js_files)

        if progress_callback:
            await progress_callback(self.stats)

        # Process files concurrently
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_with_semaphore(file_path):
            async with semaphore:
                return await self._process_file(file_path)

        tasks = []
        for i, file_path in enumerate(js_files):
            if self.is_cancelled:
                self.stats.status = ProcessingStatus.CANCELLED
                break

            self.stats.current_file = file_path.name

            tasks.append(process_with_semaphore(file_path))

            # Batch processing for progress updates
            if len(tasks) >= 100 or i == len(js_files) - 1:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        self.stats.files_with_errors += 1
                        continue

                    if result:
                        record, skipped = result
                        if record:
                            self.valid_records.append(record)
                            self.stats.valid_records += 1
                            self.stats.current_system = record.sys_name
                            self.stats.current_status = record.status
                        elif skipped:
                            self.skipped_files.append(skipped)
                            if "cancel" in skipped.reason.lower() or "excluded" in skipped.reason.lower():
                                self.cancelled_records.append(
                                    MetadataRecord(
                                        note_unid="",
                                        sys_name="",
                                        status="Cancel",
                                        file_name=skipped.file_name
                                    )
                                )
                                self.stats.cancelled_records += 1
                            else:
                                self.stats.files_with_errors += 1

                tasks = []

            # Update stats
            self.stats.files_processed = i + 1
            self.stats.files_remaining = len(js_files) - (i + 1)
            self.stats.elapsed_seconds = time.time() - start_time

            if self.stats.files_processed > 0:
                self.stats.files_per_second = self.stats.files_processed / self.stats.elapsed_seconds

                if self.stats.files_per_second > 0:
                    self.stats.estimated_remaining_seconds = (
                        self.stats.files_remaining / self.stats.files_per_second
                    )

            if progress_callback and i % 10 == 0:
                await progress_callback(self.stats)

        # Final stats
        self.stats.elapsed_seconds = time.time() - start_time
        self.stats.files_per_second = (
            self.stats.files_processed / self.stats.elapsed_seconds
            if self.stats.elapsed_seconds > 0 else 0
        )
        self.stats.files_remaining = 0

        if not self.is_cancelled:
            self.stats.status = ProcessingStatus.COMPLETED

        # Calculate unique systems
        unique_systems = set(r.sys_name for r in self.valid_records if r.sys_name)
        self.stats.unique_systems = len(unique_systems)

        if progress_callback:
            await progress_callback(self.stats)

        return self.valid_records, self.cancelled_records, self.skipped_files, self.stats

    def pause(self) -> None:
        """Pause processing."""
        self.is_paused = True
        self._pause_event.clear()
        self.stats.status = ProcessingStatus.PAUSED

    def resume(self) -> None:
        """Resume processing."""
        self.is_paused = False
        self._pause_event.set()
        self.stats.status = ProcessingStatus.RUNNING

    def cancel(self) -> None:
        """Cancel processing."""
        self.is_cancelled = True
        self._pause_event.set()  # Unblock if paused
        self.stats.status = ProcessingStatus.CANCELLED

    def cleanup(self) -> None:
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        self.temp_dirs.clear()

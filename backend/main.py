"""
FastAPI Backend for JavaScript Metadata Classification System.

Provides REST API and WebSocket for real-time progress updates.
"""
import asyncio
import io
import json
import os
import sys
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add backend directory to path for imports when running from project root
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models import MetadataRecord, ProcessingStats, ProcessingStatus, SkippedFile
from parser import parse_js_metadata_content
from filter_engine import FilterEngine, FilterRule, FilterOperator, FilterAction
from classification_engine import ClassificationEngine
from excel_generator import ExcelGenerator
from scanner import FileScanner
from logger import ProcessingLogger


# Global state
class AppState:
    scanner: Optional[FileScanner] = None
    filter_engine: FilterEngine
    logger: ProcessingLogger
    classification_engine: ClassificationEngine
    valid_records: List[MetadataRecord] = []
    cancelled_records: List[MetadataRecord] = []
    skipped_files: List[SkippedFile] = []
    stats: ProcessingStats = ProcessingStats()
    excel_bytes: Optional[bytes] = None
    websocket_clients: List[WebSocket] = []
    processing_lock: asyncio.Lock = asyncio.Lock()
    temp_upload_dir: Optional[Path] = None

    def __init__(self):
        self.filter_engine = FilterEngine()
        self.logger = ProcessingLogger()
        self.classification_engine = ClassificationEngine()


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    state.temp_upload_dir = Path(tempfile.mkdtemp(prefix="js_upload_"))
    yield
    # Shutdown
    if state.temp_upload_dir:
        shutil.rmtree(state.temp_upload_dir, ignore_errors=True)
    if state.scanner:
        state.scanner.cleanup()


app = FastAPI(
    title="JavaScript Metadata Classification System",
    description="Enterprise system for classifying JavaScript metadata files",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class StatsResponse(BaseModel):
    total_files_found: int
    files_processed: int
    files_remaining: int
    valid_records: int
    cancelled_records: int
    files_with_errors: int
    unique_systems: int
    elapsed_seconds: float
    estimated_remaining_seconds: float
    files_per_second: float
    status: str
    current_file: str
    current_system: str
    current_status: str


class ClassificationResult(BaseModel):
    sys_name: str
    total_records: int
    unique_note_count: int
    note_unids: List[str]


class FilterRuleCreate(BaseModel):
    field: str
    operator: str
    value: str
    action: str
    case_sensitive: bool = False
    description: Optional[str] = None


class SearchQuery(BaseModel):
    sys_name: Optional[str] = None
    note_unid: Optional[str] = None
    status: Optional[str] = None


async def broadcast_progress(stats: ProcessingStats):
    """Broadcast progress to all connected WebSocket clients."""
    message = json.dumps({
        "type": "progress",
        "data": stats.to_dict()
    })

    disconnected = []
    for client in state.websocket_clients:
        try:
            await client.send_text(message)
        except:
            disconnected.append(client)

    for client in disconnected:
        state.websocket_clients.remove(client)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "JavaScript Metadata Classification", "version": "3.0.0"}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get current processing statistics."""
    return state.stats.to_dict()


@app.post("/api/upload")
async def upload_zip(file: UploadFile = File(...)):
    """
    Upload a ZIP file containing JavaScript metadata files.
    Returns a session ID for tracking.
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted")

    # Save uploaded file
    upload_path = state.temp_upload_dir / file.filename
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Extract ZIP to count files
    extract_dir = state.temp_upload_dir / f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        with zipfile.ZipFile(upload_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Count JS files
        js_files = list(extract_dir.rglob("*.js"))

        return {
            "filename": file.filename,
            "extract_dir": str(extract_dir),
            "total_files": len(js_files),
            "message": "ZIP uploaded successfully. Call /api/scan to start processing."
        }
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")


@app.post("/api/process-zip")
async def process_uploaded_zip(file: UploadFile = File(...)):
    """
    Upload and immediately process a ZIP file.
    Streams progress updates via WebSocket if connected.
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted")

    async with state.processing_lock:
        # Reset state
        state.logger.clear()
        state.valid_records.clear()
        state.cancelled_records.clear()
        state.skipped_files.clear()
        state.stats = ProcessingStats()

        # Create scanner
        state.scanner = FileScanner(
            state.filter_engine,
            state.logger,
            max_workers=8
        )

        # Save and extract ZIP
        upload_path = state.temp_upload_dir / file.filename
        with open(upload_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            extract_dir = state.scanner.extract_zip(upload_path)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")

        # Process files
        valid, cancelled, skipped, stats = await state.scanner.scan_directory(
            extract_dir,
            progress_callback=broadcast_progress
        )

        state.valid_records = valid
        state.cancelled_records = cancelled
        state.skipped_files = skipped
        state.stats = stats

        # Classify records
        classifications = state.classification_engine.classify(valid)
        state.stats.unique_systems = len(classifications)

        # Generate Excel report
        generator = ExcelGenerator()

        # Calculate duplicates (records with duplicate note_unids per system)
        duplicates = 0
        for classification in classifications.values():
            duplicates += classification.total_records - classification.unique_note_count

        state.excel_bytes = generator.generate(
            list(classifications.values()),
            valid,
            skipped,
            stats,
            duplicates
        )

        return {
            "status": "completed",
            "stats": stats.to_dict(),
            "valid_records": len(valid),
            "cancelled_records": len(cancelled),
            "skipped_files": len(skipped),
            "unique_systems": len(classifications)
        }


@app.post("/api/process-folder")
async def process_folder(folder_path: str):
    """
    Process a folder path (for local development).
    Note: In browser, this requires File System Access API.
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    async with state.processing_lock:
        state.logger.clear()
        state.valid_records.clear()
        state.cancelled_records.clear()
        state.skipped_files.clear()
        state.stats = ProcessingStats()

        state.scanner = FileScanner(
            state.filter_engine,
            state.logger,
            max_workers=8
        )

        valid, cancelled, skipped, stats = await state.scanner.scan_directory(
            folder,
            progress_callback=broadcast_progress
        )

        state.valid_records = valid
        state.cancelled_records = cancelled
        state.skipped_files = skipped
        state.stats = stats

        classifications = state.classification_engine.classify(valid)
        state.stats.unique_systems = len(classifications)

        generator = ExcelGenerator()
        duplicates = sum(
            c.total_records - c.unique_note_count
            for c in classifications.values()
        )

        state.excel_bytes = generator.generate(
            list(classifications.values()),
            valid,
            skipped,
            stats,
            duplicates
        )

        return {
            "status": "completed",
            "stats": stats.to_dict(),
            "valid_records": len(valid),
            "cancelled_records": len(cancelled),
            "skipped_files": len(skipped),
            "unique_systems": len(classifications)
        }


@app.post("/api/pause")
async def pause_processing():
    """Pause current processing."""
    if state.scanner and state.stats.status == ProcessingStatus.RUNNING:
        state.scanner.pause()
        return {"status": "paused"}
    raise HTTPException(status_code=400, detail="No active processing to pause")


@app.post("/api/resume")
async def resume_processing():
    """Resume paused processing."""
    if state.scanner and state.stats.status == ProcessingStatus.PAUSED:
        state.scanner.resume()
        return {"status": "resumed"}
    raise HTTPException(status_code=400, detail="No paused processing to resume")


@app.post("/api/cancel")
async def cancel_processing():
    """Cancel current processing."""
    if state.scanner:
        state.scanner.cancel()
        return {"status": "cancelled"}
    raise HTTPException(status_code=400, detail="No active processing to cancel")


@app.post("/api/reset")
async def reset():
    """Reset all state and prepare for new session."""
    if state.scanner:
        state.scanner.cancel()
        state.scanner.cleanup()

    state.logger.clear()
    state.valid_records.clear()
    state.cancelled_records.clear()
    state.skipped_files.clear()
    state.stats = ProcessingStats()
    state.excel_bytes = None
    state.scanner = None

    return {"status": "reset"}


@app.get("/api/classifications")
async def get_classifications():
    """Get all classification results."""
    return {
        "classifications": [
            {
                "sys_name": c.sys_name,
                "total_records": c.total_records,
                "unique_note_count": c.unique_note_count,
                "note_unids": c.note_unids[:100]  # Limit for response size
            }
            for c in state.classification_engine.get_all_classifications()
        ]
    }


@app.post("/api/search")
async def search_records(query: SearchQuery):
    """Search records by various criteria."""
    results = state.classification_engine.search(
        sys_name=query.sys_name,
        note_unid=query.note_unid,
        status=query.status
    )

    return {
        "results": [
            {
                "sys_name": r.sys_name,
                "total_records": r.total_records,
                "unique_note_count": r.unique_note_count,
                "note_unids": r.note_unids[:50]
            }
            for r in results
        ]
    }


@app.get("/api/logs")
async def get_logs():
    """Get processing logs."""
    return {
        "entries": state.logger.to_dict_list(),
        "summary": state.logger.get_summary()
    }


@app.get("/api/logs/export")
async def export_logs(format: str = "json"):
    """Export logs as downloadable file."""
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Format must be json or csv")

    content = state.logger.to_json() if format == "json" else state.logger.to_csv()
    filename = f"processing_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"

    return StreamingResponse(
        io.BytesIO(content.encode('utf-8')),
        media_type="application/json" if format == "json" else "text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/export/excel")
async def export_excel():
    """Download the Excel report."""
    if not state.excel_bytes:
        raise HTTPException(status_code=404, detail="No report available. Process files first.")

    filename = f"Classification_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        io.BytesIO(state.excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/filters")
async def get_filters():
    """Get current filter configuration."""
    return {
        "filters": [
            {
                "type": type(f).__name__,
                "description": f.__class__.__doc__ or ""
            }
            for f in state.filter_engine.filters
        ]
    }


@app.post("/api/filters/add")
async def add_filter(rule: FilterRuleCreate):
    """Add a new filter rule."""
    try:
        operator = FilterOperator(rule.operator)
        action = FilterAction(rule.action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid operator or action: {e}")

    filter_rule = FilterRule(
        field=rule.field,
        operator=operator,
        value=rule.value,
        action=action,
        case_sensitive=rule.case_sensitive,
        description=rule.description
    )

    state.filter_engine.add_rule(filter_rule)

    return {"status": "added", "rule": rule.dict()}


@app.delete("/api/filters/reset")
async def reset_filters():
    """Reset filters to default."""
    state.filter_engine.reset_to_default()
    return {"status": "reset"}


@app.post("/api/parser-test")
async def test_parser(file: UploadFile = File(...)):
    """
    Test the parser with a single JavaScript metadata file.
    Returns extracted fields and parser validation results.
    Used to verify parser correctness before batch processing.
    """
    if not file.filename.endswith('.js'):
        raise HTTPException(status_code=400, detail="Only .js files are accepted for parser testing")

    try:
        content = await file.read()
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text_content = content.decode('latin-1')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to decode file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Parse the content
    record = parse_js_metadata_content(text_content, file.filename)

    # Build detailed result
    result = {
        "file_name": file.filename,
        "note_unid": record.note_unid,
        "sys_name": record.sys_name,
        "status": record.status,
        "parser_status": "PASS" if record.is_valid else "FAIL",
        "missing_fields": record.parse_errors,
        "details": {
            "note_unid_found": bool(record.note_unid),
            "sys_name_found": bool(record.sys_name),
            "status_found": bool(record.status)
        }
    }

    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates."""
    await websocket.accept()
    state.websocket_clients.append(websocket)

    try:
        # Send current stats
        await websocket.send_text(json.dumps({
            "type": "init",
            "data": state.stats.to_dict()
        }))

        while True:
            # Wait for client messages (ping/pong)
            data = await websocket.receive_text()

            # Handle client commands
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        if websocket in state.websocket_clients:
            state.websocket_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

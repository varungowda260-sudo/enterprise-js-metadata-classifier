# JavaScript Metadata Classification System (Version 3)

A production-ready enterprise web application for processing and classifying exported JavaScript metadata files.

## Overview

This application processes JavaScript metadata files (`.js`) that contain structured metadata in a specific format. It extracts key fields, filters records, and generates comprehensive Excel reports.

**Important:** The `.js` files processed by this system are NOT executable JavaScript code. They are metadata documents that use JavaScript object notation.

## Features

- Process 30,000+ JavaScript metadata files efficiently
- Real-time progress tracking via WebSocket
- Automatic exclusion of cancelled records (status = "Cancel")
- Comprehensive Excel report generation
- Search and filter capabilities
- Detailed logging and error tracking
- Dark/Light theme support
- Responsive enterprise dashboard design

## Technology Stack

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui components
- Lucide React icons

### Backend
- Python 3.11+
- FastAPI
- OpenPyXL
- Pandas

## Installation

### Prerequisites
- Node.js 18+
- Python 3.11+

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup

```bash
npm install
```

## Running the Application

### Option 1: Use the startup script

```bash
chmod +x start.sh
./start.sh
```

This will start both backend and frontend automatically.

### Option 2: Manual startup

Start the Backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

The backend will run on http://localhost:8000

Start the Frontend (in a new terminal):

```bash
npm run dev
```

The frontend will run on http://localhost:5173

## Usage

1. **Upload a ZIP file** containing JavaScript metadata files
2. The system automatically:
   - Extracts the ZIP archive
   - Recursively discovers all `.js` files
   - Parses each file to extract `note_unid`, `sys_name`, and `status`
   - Filters out records with `status = "Cancel"`
   - Groups remaining records by `sys_name`
   - Generates an Excel report

3. **Monitor progress** in real-time:
   - Files processed
   - Valid records
   - Cancelled records
   - Processing speed
   - Estimated time remaining

4. **Export the Excel report** with four sheets:
   - Summary: System name, record counts, note UNIDs
   - Details: Individual file records
   - Skipped Files: Files with errors or issues
   - Processing Statistics: Performance metrics

## Metadata File Format

The system expects JavaScript metadata files in this format:

```javascript
var metadata = {
    note_unid: "ABC123",
    note_items: [
        {
            "name": "sys_name",
            "value": ["SAP"]
        },
        {
            "name": "status",
            "value": ["Open"]
        }
    ]
}
```

## Extracted Fields

The parser extracts only these three fields:
- `note_unid` - Unique identifier
- `sys_name` - System name for grouping
- `status` - Record status (Cancel records are excluded)

## Classification Rules

Records are automatically excluded if `status` equals "Cancel" (case-insensitive).

The filtering system is designed to be extensible - additional filter rules can be added without modifying the parser.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload a ZIP file |
| `/api/process-zip` | POST | Upload and process a ZIP file |
| `/api/pause` | POST | Pause processing |
| `/api/resume` | POST | Resume processing |
| `/api/cancel` | POST | Cancel processing |
| `/api/reset` | POST | Reset session |
| `/api/stats` | GET | Get processing statistics |
| `/api/classifications` | GET | Get classification results |
| `/api/export/excel` | GET | Download Excel report |
| `/api/logs` | GET | Get processing logs |
| `/ws` | WebSocket | Real-time progress updates |

## Performance

- Concurrent file processing (configurable worker count)
- Memory-efficient streaming for large datasets
- Progress updates without UI blocking
- Efficient ZIP extraction and file discovery

## Architecture

```
project/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Data models
│   ├── parser.py            # Metadata parser
│   ├── scanner.py           # File scanner
│   ├── filter_engine.py     # Filtering engine
│   ├── classification_engine.py  # Classification logic
│   ├── excel_generator.py   # Excel report generation
│   ├── logger.py            # Processing logger
│   └── requirements.txt     # Python dependencies
├── src/
│   ├── App.tsx              # Main React component
│   ├── services/
│   │   └── api.ts           # API service
│   ├── hooks/
│   │   └── useProcessing.ts # Custom React hooks
│   ├── types/
│   │   └── index.ts         # TypeScript types
│   └── components/ui/       # shadcn/ui components
├── package.json
└── README.md
```

## Error Handling

The application never crashes due to individual file errors:
- Missing fields are logged as warnings
- Parse errors are tracked in the error log
- Processing continues for remaining files
- All errors are captured in the final report

## Configuration

Default settings can be modified in:
- Backend: `scanner.py` (worker count, batch size)
- Frontend: API service URLs in `api.ts`

## Browser Compatibility

The application runs locally and does not require cloud deployment. Modern browsers (Chrome, Firefox, Safari, Edge) are supported.

## License

Enterprise internal use only.

#!/bin/bash

# JavaScript Metadata Classification System - Startup Script

echo "Starting JavaScript Metadata Classification System..."
echo

# Start backend in background
echo "Starting Python backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 2

# Start frontend
echo "Starting React frontend..."
npm run dev &
FRONTEND_PID=$!

echo
echo "=========================================="
echo "Application started!"
echo "=========================================="
echo
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo
echo "Press Ctrl+C to stop both servers"
echo

# Trap exit
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# Wait
wait

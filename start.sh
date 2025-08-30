#!/bin/bash

# Audio Transcriber Startup Script
echo "🎤 Starting Audio Transcriber..."

# Change to script directory
cd "$(dirname "$0")"

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start backend
echo "🐍 Starting Python backend..."
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend
echo "⚡ Starting SvelteKit frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Wait a bit more for frontend to start
sleep 5

echo ""
echo "✅ Both servers are running!"
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Keep script running and wait for processes
wait $BACKEND_PID $FRONTEND_PID
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import whisper
import tempfile
import os
import uuid
from typing import Optional, Dict
import asyncio
from pydantic import BaseModel
import logging
import sys
import shutil

# Configure logging EARLY (before any logging calls)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure ffmpeg is discoverable when launched as a Tauri sidecar (limited PATH)
BREW_PATHS = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
if shutil.which("ffmpeg") is None:
    extra_paths = ":".join([p for p in BREW_PATHS if os.path.isdir(p)])
    os.environ["PATH"] = f"{extra_paths}:{os.environ.get('PATH','')}"
ffmpeg_path = shutil.which("ffmpeg")
if ffmpeg_path:
    logger.info(f"ffmpeg found at: {ffmpeg_path}")
else:
    logger.warning("ffmpeg not found on PATH. Please install via Homebrew: `brew install ffmpeg`")

# Set Whisper cache directory to a writable location
cache_dir = os.path.expanduser('~/.cache/whisper')
os.makedirs(cache_dir, exist_ok=True)
os.environ['XDG_CACHE_HOME'] = os.path.expanduser('~/.cache')
os.environ['WHISPER_CACHE'] = cache_dir
logger.info(f"Whisper cache directory set to: {cache_dir}")

# Handle PyInstaller bundled assets
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    bundle_dir = sys._MEIPASS
    logger.info(f"Running in PyInstaller bundle, bundle dir: {bundle_dir}")

    whisper_assets_path = os.path.join(bundle_dir, 'whisper', 'assets')
    logger.info(f"Looking for Whisper assets at: {whisper_assets_path}")

    if os.path.exists(whisper_assets_path):
        # Set environment variable to point to bundled assets
        os.environ['WHISPER_ASSETS_PATH'] = whisper_assets_path
        logger.info(f"Using bundled Whisper assets from: {whisper_assets_path}")
    else:
        logger.warning(f"Bundled Whisper assets not found at: {whisper_assets_path}")
        if os.path.exists(bundle_dir):
            bundle_contents = os.listdir(bundle_dir)
            logger.info(f"Available files in bundle: {bundle_contents}")
            # Check if whisper directory exists
            whisper_dir = os.path.join(bundle_dir, 'whisper')
            if os.path.exists(whisper_dir):
                whisper_contents = os.listdir(whisper_dir)
                logger.info(f"Contents of whisper directory: {whisper_contents}")
        else:
            logger.error(f"Bundle directory does not exist: {bundle_dir}")
else:
    logger.info("Running in development mode")

import signal
import sys
from contextlib import asynccontextmanager

# Store background tasks for cleanup
background_tasks_set = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    global model
    logger.info(f"Loading Whisper model: {MODEL_SIZE}")

    # Ensure cache directory exists and is writable
    cache_dir = os.path.expanduser('~/.cache/whisper')
    os.makedirs(cache_dir, exist_ok=True)
    logger.info(f"Whisper cache directory: {cache_dir}")

    # Set download root for Whisper models
    try:
        model = whisper.load_model(MODEL_SIZE, download_root=cache_dir)
        logger.info("Model loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        # Try loading without specifying download_root
        try:
            model = whisper.load_model(MODEL_SIZE)
            logger.info("Model loaded successfully (fallback)!")
        except Exception as e2:
            logger.error(f"Failed to load model even with fallback: {e2}")
            raise e2

    # Log presence of mel filter assets (debug)
    mel_path = os.path.join(os.path.dirname(whisper.__file__), "assets", "mel_filters.npz")
    logger.info(f"Whisper mel_filters path: {mel_path}; exists={os.path.exists(mel_path)}")

    yield

    # Shutdown - cleanup background tasks
    logger.info("Shutting down server...")
    for task in background_tasks_set:
        if not task.done():
            task.cancel()

    # Wait for tasks to finish
    if background_tasks_set:
        await asyncio.gather(*background_tasks_set, return_exceptions=True)

    logger.info("Server shutdown complete")

app = FastAPI(title="Audio Transcription API", version="1.0.0", lifespan=lifespan)

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost:*",
        "https://tauri.localhost:*",
        "*"  # Allow all origins for Tauri (you can restrict this later)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# In-memory storage for transcription jobs (use Redis for production)
transcription_jobs: Dict[str, dict] = {}

# Load Whisper model on startup (you can change model size based on your needs)
# Options: tiny, base, small, medium, large-v3
MODEL_SIZE = "medium"
model = None

class TranscriptionResponse(BaseModel):
    job_id: str
    status: str
    text: Optional[str] = None
    segments: Optional[list] = None
    language: Optional[str] = None
    error: Optional[str] = None

# Remove the old startup event
# @app.on_event("startup") - this is replaced by lifespan

@app.get("/")
async def root():
    return {"message": "Audio Transcription API is running!", "model": MODEL_SIZE}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": model is not None}

async def transcribe_audio_task(job_id: str, file_path: str, language: Optional[str] = None):
    """Background task to transcribe audio"""
    try:
        logger.info(f"Starting transcription for job {job_id}")
        transcription_jobs[job_id]["status"] = "processing"

        # Extra debug: confirm assets path exists at transcription time
        mel_path = os.path.join(os.path.dirname(whisper.__file__), "assets", "mel_filters.npz")
        logger.info(f"[Transcribe] mel_filters path: {mel_path}; exists={os.path.exists(mel_path)}")

        # Transcribe the audio
        result = model.transcribe(
            file_path,
            language=language,
            word_timestamps=True,  # Get word-level timestamps
            verbose=True
        )

        # Update job with results
        transcription_jobs[job_id].update({
            "status": "completed",
            "text": result["text"],
            "segments": result["segments"],
            "language": result["language"]
        })

        logger.info(f"Transcription completed for job {job_id}")

    except Exception as e:
        logger.error(f"Transcription failed for job {job_id}: {str(e)}")
        transcription_jobs[job_id].update({
            "status": "error",
            "error": str(e)
        })
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = None
):
    """
    Upload an audio file for transcription

    - **file**: Audio file (mp3, wav, m4a, mp4, etc.)
    - **language**: Optional language code (e.g., 'en', 'es', 'fr'). If not specified, Whisper will auto-detect.
    """
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Validate file type
    allowed_extensions = {'.mp3', '.wav', '.m4a', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.aac', '.ogg'}
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. Supported: {', '.join(allowed_extensions)}"
        )

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Initialize job
        transcription_jobs[job_id] = {
            "status": "queued",
            "filename": file.filename,
            "language": language
        }

        # Start background transcription and track the task
        task = asyncio.create_task(transcribe_audio_task(job_id, temp_file_path, language))
        background_tasks_set.add(task)
        task.add_done_callback(background_tasks_set.discard)

        return TranscriptionResponse(
            job_id=job_id,
            status="queued"
        )

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/transcribe/{job_id}", response_model=TranscriptionResponse)
async def get_transcription_status(job_id: str):
    """Get the status and results of a transcription job"""
    if job_id not in transcription_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = transcription_jobs[job_id]
    return TranscriptionResponse(
        job_id=job_id,
        **job
    )

@app.delete("/transcribe/{job_id}")
async def delete_transcription_job(job_id: str):
    """Delete a completed transcription job"""
    if job_id not in transcription_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    del transcription_jobs[job_id]
    return {"message": "Job deleted successfully"}

@app.get("/models")
async def get_available_models():
    """Get information about available Whisper models"""
    models_info = {
        "current_model": MODEL_SIZE,
        "available_models": {
            "tiny": {"size": "39 MB", "speed": "~32x realtime", "accuracy": "lowest"},
            "base": {"size": "74 MB", "speed": "~16x realtime", "accuracy": "good"},
            "small": {"size": "244 MB", "speed": "~6x realtime", "accuracy": "better"},
            "medium": {"size": "769 MB", "speed": "~2x realtime", "accuracy": "great"},
            "large-v3": {"size": "1550 MB", "speed": "~1x realtime", "accuracy": "best"}
        }
    }
    return models_info

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    import uvicorn

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    uvicorn.run(app, host="0.0.0.0", port=8000)
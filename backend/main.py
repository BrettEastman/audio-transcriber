# ============================================================================
# IMPORTS AND DEPENDENCIES
# ============================================================================
# FastAPI: The web framework that handles HTTP requests and routing
#   - FastAPI: Main application class
#   - File, UploadFile: Handle file uploads from clients
#   - HTTPException: Raise HTTP errors (404, 500, etc.)
#   - BackgroundTasks: Run tasks after sending response (not used here, we use asyncio instead)
#   - CORSMiddleware: Allow frontend apps to make requests (cross-origin resource sharing)
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# whisper: OpenAI's speech-to-text library (the AI model that does transcription)
import whisper

# Standard library imports for file handling, system operations, and async programming
import tempfile  # Create temporary files for uploaded audio
import os        # File system operations (paths, environment variables)
import uuid      # Generate unique IDs for transcription jobs
from typing import Optional, Dict  # Type hints for better code documentation
import asyncio   # Handle asynchronous operations (background tasks)
from pydantic import BaseModel  # Data validation and serialization (like TypeScript interfaces)
import logging   # Log messages for debugging and monitoring
import sys       # System-specific parameters and functions
import shutil    # File operations (like finding executables in PATH)

# ============================================================================
# LOGGING SETUP
# ============================================================================
# Configure logging to output INFO level messages and above
# This helps us see what's happening in the server (startup, errors, etc.)
# We set this up early so all subsequent code can use logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # Create a logger for this specific file

# ============================================================================
# FFMPEG SETUP
# ============================================================================
# ffmpeg is a tool that converts audio/video files. Whisper needs it to process
# various audio formats. This section ensures ffmpeg can be found even if it's
# not in the default PATH (common on macOS with Homebrew installations).
#
# How it works:
# 1. Check if ffmpeg is already in PATH
# 2. If not, add common installation directories to PATH
# 3. Verify ffmpeg is now accessible
BREW_PATHS = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
if shutil.which("ffmpeg") is None:
    extra_paths = ":".join([p for p in BREW_PATHS if os.path.isdir(p)])
    os.environ["PATH"] = f"{extra_paths}:{os.environ.get('PATH','')}"
ffmpeg_path = shutil.which("ffmpeg")
if ffmpeg_path:
    logger.info(f"ffmpeg found at: {ffmpeg_path}")
else:
    logger.warning("ffmpeg not found on PATH. Please install via Homebrew: `brew install ffmpeg`")

# ============================================================================
# WHISPER CACHE CONFIGURATION
# ============================================================================
# Whisper models are large (hundreds of MB) and download automatically on first use.
# We configure a cache directory so the model is downloaded once and reused.
# This saves time and bandwidth on subsequent server starts.
#
# The cache directory is typically at ~/.cache/whisper (in your home folder)
cache_dir = os.path.expanduser('~/.cache/whisper')
os.makedirs(cache_dir, exist_ok=True)  # Create directory if it doesn't exist
os.environ['XDG_CACHE_HOME'] = os.path.expanduser('~/.cache')
os.environ['WHISPER_CACHE'] = cache_dir
logger.info(f"Whisper cache directory set to: {cache_dir}")

# Running in development mode (Python directly, not bundled)
logger.info("Running in development mode")

# ============================================================================
# ADDITIONAL IMPORTS FOR LIFECYCLE MANAGEMENT
# ============================================================================
# signal: Handle system signals (like Ctrl+C) for graceful shutdown
# asynccontextmanager: Create a context manager for startup/shutdown logic
import signal
import sys
from contextlib import asynccontextmanager

# ============================================================================
# BACKGROUND TASK TRACKING
# ============================================================================
# When we transcribe audio, it happens in the background (async task).
# We keep track of all running tasks so we can cancel them gracefully
# when the server shuts down. This prevents tasks from being interrupted
# mid-transcription, which could corrupt data.
background_tasks_set = set()  # A set stores unique items (no duplicates)

# ============================================================================
# APPLICATION LIFESPAN MANAGEMENT
# ============================================================================
# This function runs code when the server starts up and when it shuts down.
# Think of it like React's useEffect with cleanup, or Next.js middleware.
#
# The @asynccontextmanager decorator makes this function work as a context manager.
# Everything before "yield" runs at startup, everything after runs at shutdown.
#
# Why this matters: We need to load the Whisper model (which is large and slow)
# BEFORE the server accepts any requests. Otherwise, the first transcription would
# fail because the model isn't ready yet.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown logic"""

    # ========================================================================
    # STARTUP: Load the Whisper AI model
    # ========================================================================
    # The "global" keyword means we're modifying the model variable defined
    # at the module level (line 120), not creating a new local variable.
    global model
    logger.info(f"Loading Whisper model: {MODEL_SIZE}")

    # Ensure cache directory exists and is writable
    cache_dir = os.path.expanduser('~/.cache/whisper')
    os.makedirs(cache_dir, exist_ok=True)
    logger.info(f"Whisper cache directory: {cache_dir}")

    # Try multiple strategies to load the model (with fallbacks):
    # 1. First: Try loading from our specified cache directory
    # 2. Second: Try loading from Whisper's default cache location
    # 3. Third: Download the model if it doesn't exist anywhere
    # This ensures the server starts even if the cache is in an unexpected location
    try:
        # First try to load from cache directory
        model = whisper.load_model(MODEL_SIZE, download_root=cache_dir)
        logger.info("Model loaded successfully from cache!")
    except Exception as e:
        logger.error(f"Failed to load model from cache: {e}")
        # Try loading without specifying download_root (uses default cache)
        try:
            model = whisper.load_model(MODEL_SIZE)
            logger.info("Model loaded successfully from default cache!")
        except Exception as e2:
            logger.error(f"Failed to load model from default cache: {e2}")
            # Last resort: force download and load
            try:
                logger.info("Attempting to download model...")
                model = whisper.load_model(MODEL_SIZE, download_root=cache_dir, download=True)
                logger.info("Model downloaded and loaded successfully!")
            except Exception as e3:
                logger.error(f"Failed to download and load model: {e3}")
                raise e3  # If all attempts fail, crash the server (can't work without model)

    # Log presence of mel filter assets (debug)
    mel_path = os.path.join(os.path.dirname(whisper.__file__), "assets", "mel_filters.npz")
    logger.info(f"Whisper mel_filters path: {mel_path}; exists={os.path.exists(mel_path)}")

    # ========================================================================
    # YIELD: Server is now running and ready to accept requests
    # ========================================================================
    # The "yield" statement is where control passes to FastAPI.
    # The server runs here, handling requests. When shutdown is requested,
    # execution continues after the yield statement.
    yield

    # ========================================================================
    # SHUTDOWN: Clean up background tasks gracefully
    # ========================================================================
    # When the server is shutting down (Ctrl+C, system stop, etc.),
    # we need to cancel any running transcription tasks to avoid corruption.
    logger.info("Shutting down server...")

    # Cancel all running background tasks
    for task in background_tasks_set:
        if not task.done():  # Only cancel if task hasn't finished yet
            task.cancel()

    # Wait for all tasks to finish (or be cancelled)
    # return_exceptions=True means we don't crash if a task raises an error
    if background_tasks_set:
        await asyncio.gather(*background_tasks_set, return_exceptions=True)

    logger.info("Server shutdown complete")

# ============================================================================
# FASTAPI APPLICATION CREATION
# ============================================================================
# Create the main FastAPI application instance. This is like creating an Express
# app in Node.js or a Flask app in Python. The "lifespan" parameter tells FastAPI
# to use our lifespan function for startup/shutdown logic.
app = FastAPI(title="Audio Transcription API", version="1.0.0", lifespan=lifespan)

# ============================================================================
# CORS (CROSS-ORIGIN RESOURCE SHARING) CONFIGURATION
# ============================================================================
# CORS is a browser security feature. By default, browsers block requests from
# one domain (like localhost:5173) to another (like localhost:8000).
#
# Since our frontend runs on a different port than our backend, we need to
# explicitly allow these cross-origin requests. This middleware tells the browser
# "it's okay for these frontend URLs to make requests to this API."
#
# In production, you'd want to restrict this to your actual frontend domain
# instead of allowing all localhost ports.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Common React dev server port
        "http://localhost:5173",   # Vite dev server port (Svelte, React, etc.)
        "http://127.0.0.1:5173",   # Alternative localhost format
    ],
    allow_credentials=True,        # Allow cookies/auth headers
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],  # Which HTTP methods to allow
    allow_headers=["*"],           # Allow all headers (can be more restrictive)
)

# ============================================================================
# DATA STORAGE
# ============================================================================
# Store transcription jobs in memory (a Python dictionary).
# Each job has a unique ID as the key, and job data as the value.
#
# Note: This is in-memory storage, so jobs are lost when the server restarts.
# For production, you'd use a database (PostgreSQL, MongoDB) or Redis.
# Dictionary structure: { "job-id-123": { "status": "completed", "text": "...", ... } }
transcription_jobs: Dict[str, dict] = {}

# ============================================================================
# WHISPER MODEL CONFIGURATION
# ============================================================================
# Whisper comes in different sizes. Larger models = better accuracy but slower.
# - tiny: Fastest, least accurate (good for testing)
# - base: Good balance
# - small: Better accuracy
# - medium: Great accuracy (current choice)
# - large-v3: Best accuracy, slowest
#
# The model variable will be set during startup (in the lifespan function).
# We initialize it to None so we can check if it's loaded before processing requests.
MODEL_SIZE = "medium"
model = None  # Will be loaded at startup

# ============================================================================
# DATA MODELS (Pydantic Schemas)
# ============================================================================
# Pydantic models are like TypeScript interfaces - they define the shape of data
# and automatically validate it. FastAPI uses these to:
# 1. Validate incoming/outgoing data
# 2. Generate API documentation automatically
# 3. Provide type hints for better IDE support
#
# This model defines what a transcription response looks like when sent to clients.
class TranscriptionResponse(BaseModel):
    job_id: str                    # Unique identifier for the job
    status: str                    # "queued", "processing", "completed", or "error"
    text: Optional[str] = None     # The transcribed text (null until completed)
    segments: Optional[list] = None # Word-level timestamps (null until completed)
    language: Optional[str] = None  # Detected language (null until completed)
    error: Optional[str] = None    # Error message if something went wrong

# ============================================================================
# API ENDPOINTS (ROUTES)
# ============================================================================
# FastAPI uses decorators (like @app.get) to define routes, similar to Express.js.
# The decorator tells FastAPI: "When someone makes a GET request to '/', run this function."
#
# Note: The old @app.on_event("startup") pattern is replaced by the lifespan function above.

# ----------------------------------------------------------------------------
# Root endpoint - Basic API information
# ----------------------------------------------------------------------------
# GET / - Simple endpoint to check if the API is running
# Returns basic info about the API and which model is configured
@app.get("/")
async def root():
    return {"message": "Audio Transcription API is running!", "model": MODEL_SIZE}

# ----------------------------------------------------------------------------
# Health check endpoint - Server status
# ----------------------------------------------------------------------------
# GET /health - Used by monitoring tools and load balancers to check if the
# server is healthy and ready to handle requests. Returns whether the model
# is loaded (if model is None, the server isn't ready yet).
@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": model is not None}

# ============================================================================
# BACKGROUND TRANSCRIPTION TASK
# ============================================================================
# This function runs in the background (asynchronously) to transcribe audio.
# It's called from the /transcribe endpoint, but runs separately so the API
# can return immediately with a job ID instead of waiting for transcription
# to complete (which could take minutes for long audio files).
#
# This is similar to queuing a job in a background worker (like Sidekiq in Ruby
# or Bull in Node.js), but we're using Python's asyncio for simplicity.
async def transcribe_audio_task(job_id: str, file_path: str, language: Optional[str] = None):
    """Background task to transcribe audio - runs asynchronously after API response"""
    try:
        logger.info(f"Starting transcription for job {job_id}")

        # Update job status so clients polling /transcribe/{job_id} know we're working
        transcription_jobs[job_id]["status"] = "processing"

        # Extra debug: confirm assets path exists at transcription time
        mel_path = os.path.join(os.path.dirname(whisper.__file__), "assets", "mel_filters.npz")
        logger.info(f"[Transcribe] mel_filters path: {mel_path}; exists={os.path.exists(mel_path)}")

        # ====================================================================
        # THE ACTUAL TRANSCRIPTION
        # ====================================================================
        # This is where Whisper does the heavy lifting - converting audio to text.
        # This can take seconds to minutes depending on audio length and model size.
        # - file_path: Path to the temporary audio file
        # - language: Optional hint (e.g., "en" for English). If None, auto-detects.
        # - word_timestamps: Get timing info for each word (useful for subtitles)
        # - verbose: Print progress to console
        result = model.transcribe(
            file_path,
            language=language,
            word_timestamps=True,  # Get word-level timestamps
            verbose=True
        )

        # ====================================================================
        # SAVE RESULTS
        # ====================================================================
        # Update the job in our in-memory storage with the transcription results.
        # Clients can now fetch these results via GET /transcribe/{job_id}
        transcription_jobs[job_id].update({
            "status": "completed",
            "text": result["text"],           # Full transcribed text
            "segments": result["segments"],   # Array of segments with timestamps
            "language": result["language"]    # Detected language code
        })

        logger.info(f"Transcription completed for job {job_id}")

    except Exception as e:
        # ====================================================================
        # ERROR HANDLING
        # ====================================================================
        # If anything goes wrong (file corruption, model error, etc.), mark the
        # job as failed and store the error message so the client knows what happened.
        logger.error(f"Transcription failed for job {job_id}: {str(e)}")
        transcription_jobs[job_id].update({
            "status": "error",
            "error": str(e)
        })
    finally:
        # ====================================================================
        # CLEANUP
        # ====================================================================
        # Always delete the temporary file, even if transcription failed.
        # This prevents disk space from filling up with old audio files.
        if os.path.exists(file_path):
            os.remove(file_path)

# ============================================================================
# MAIN TRANSCRIPTION ENDPOINT
# ============================================================================
# POST /transcribe - The main endpoint clients use to upload audio files.
# This endpoint:
# 1. Accepts an uploaded audio file
# 2. Validates the file type
# 3. Saves it temporarily to disk
# 4. Creates a job and starts background transcription
# 5. Returns immediately with a job ID (doesn't wait for transcription)
#
# The client then polls GET /transcribe/{job_id} to check status and get results.
@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),  # File(...) means this parameter is required
    language: Optional[str] = None  # Optional language hint (e.g., "en", "es")
):
    """
    Upload an audio file for transcription

    - **file**: Audio file (mp3, wav, m4a, mp4, etc.)
    - **language**: Optional language code (e.g., 'en', 'es', 'fr'). If not specified, Whisper will auto-detect.
    """
    # ========================================================================
    # VALIDATION: Check if model is loaded
    # ========================================================================
    # If the model isn't loaded yet (shouldn't happen, but safety check),
    # return a 503 Service Unavailable error.
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # ========================================================================
    # GENERATE JOB ID
    # ========================================================================
    # Create a unique identifier for this transcription job.
    # UUIDs (Universally Unique Identifiers) are guaranteed to be unique.
    job_id = str(uuid.uuid4())

    # ========================================================================
    # FILE VALIDATION
    # ========================================================================
    # Check that the uploaded file has a supported extension.
    # We validate this before saving to disk to avoid wasting resources.
    allowed_extensions = {'.mp3', '.wav', '.m4a', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.aac', '.ogg'}
    file_extension = os.path.splitext(file.filename)[1].lower()  # Get extension, lowercase

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,  # Bad Request
            detail=f"Unsupported file type: {file_extension}. Supported: {', '.join(allowed_extensions)}"
        )

    try:
        # ====================================================================
        # SAVE UPLOADED FILE TO DISK
        # ====================================================================
        # FastAPI gives us the file as a stream. We need to save it to disk
        # because Whisper needs a file path to process it.
        #
        # tempfile.NamedTemporaryFile creates a temporary file that will be
        # deleted later. We set delete=False because we need to keep it until
        # transcription completes (it gets deleted in the background task).
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()  # Read the entire file into memory
            temp_file.write(content)      # Write it to the temporary file
            temp_file_path = temp_file.name  # Get the path for later use

        # ====================================================================
        # CREATE JOB RECORD
        # ====================================================================
        # Store job information in our in-memory dictionary.
        # The status starts as "queued" and will be updated by the background task.
        transcription_jobs[job_id] = {
            "status": "queued",
            "filename": file.filename,
            "language": language
        }

        # ====================================================================
        # START BACKGROUND TRANSCRIPTION
        # ====================================================================
        # Create an async task that will run the transcription in the background.
        # This allows the API to return immediately instead of waiting for
        # transcription to complete (which could take minutes).
        #
        # asyncio.create_task schedules the function to run concurrently.
        # We add it to background_tasks_set so we can cancel it on shutdown.
        task = asyncio.create_task(transcribe_audio_task(job_id, temp_file_path, language))
        background_tasks_set.add(task)  # Track it for cleanup
        task.add_done_callback(background_tasks_set.discard)  # Remove from set when done

        # ====================================================================
        # RETURN JOB ID TO CLIENT
        # ====================================================================
        # Return immediately with the job ID. The client can use this to
        # poll for status and results later.
        return TranscriptionResponse(
            job_id=job_id,
            status="queued"
        )

    except Exception as e:
        # ====================================================================
        # ERROR HANDLING
        # ====================================================================
        # If anything goes wrong during file upload or task creation,
        # log the error and return a 500 Internal Server Error.
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ============================================================================
# JOB STATUS ENDPOINT
# ============================================================================
# GET /transcribe/{job_id} - Check the status of a transcription job
#
# This is a polling endpoint. The client calls this repeatedly (every few seconds)
# to check if transcription is complete. When status is "completed", the response
# includes the transcribed text and segments.
#
# The {job_id} in the path is a path parameter - FastAPI extracts it from the URL.
@app.get("/transcribe/{job_id}", response_model=TranscriptionResponse)
async def get_transcription_status(job_id: str):
    """Get the status and results of a transcription job"""
    # Check if the job exists
    if job_id not in transcription_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get the job data and return it
    # The **job syntax "unpacks" the dictionary, so all keys become function arguments
    job = transcription_jobs[job_id]
    return TranscriptionResponse(
        job_id=job_id,
        **job  # Spread operator equivalent - passes all job fields to TranscriptionResponse
    )

# ============================================================================
# DELETE JOB ENDPOINT
# ============================================================================
# DELETE /transcribe/{job_id} - Remove a transcription job from memory
#
# This is useful for cleanup - once the client has the results, they can delete
# the job to free up memory. In production with a database, this would delete
# the database record.
@app.delete("/transcribe/{job_id}")
async def delete_transcription_job(job_id: str):
    """Delete a completed transcription job"""
    if job_id not in transcription_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    # Remove the job from our in-memory dictionary
    del transcription_jobs[job_id]
    return {"message": "Job deleted successfully"}

# ============================================================================
# MODELS INFORMATION ENDPOINT
# ============================================================================
# GET /models - Get information about available Whisper model sizes
#
# This is a utility endpoint that tells clients what models are available
# and their characteristics (size, speed, accuracy). Useful for documentation
# or if you want to let users choose model size in the future.
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

# ============================================================================
# SIGNAL HANDLERS (GRACEFUL SHUTDOWN)
# ============================================================================
# Signal handlers allow the server to respond gracefully to shutdown requests.
# SIGINT is sent when you press Ctrl+C, SIGTERM is sent by system shutdown scripts.
# Without these handlers, the server might kill background tasks abruptly.
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)  # This triggers the lifespan shutdown logic

# ============================================================================
# SERVER STARTUP (MAIN EXECUTION)
# ============================================================================
# This block only runs when the script is executed directly (python main.py),
# not when it's imported as a module. This is the Python equivalent of
# "if this is the main file being run, start the server."
#
# uvicorn is an ASGI server (like how Node.js needs a server to run Express).
# It handles the low-level HTTP protocol and runs our FastAPI app.
if __name__ == "__main__":
    import uvicorn  # ASGI server for FastAPI

    # Register signal handlers so Ctrl+C triggers graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)   # System termination

    # Start the server
    # - host="0.0.0.0" means listen on all network interfaces (accessible from other devices)
    # - port=8000 is the port the server runs on
    # - app is our FastAPI application instance
    uvicorn.run(app, host="0.0.0.0", port=8000)
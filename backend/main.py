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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Audio Transcription API", version="1.0.0")

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for transcription jobs (use Redis for production)
transcription_jobs: Dict[str, dict] = {}

# Load Whisper model on startup (you can change model size based on your needs)
# Options: tiny, base, small, medium, large-v3
MODEL_SIZE = "base"  # Good balance of speed/accuracy
model = None

class TranscriptionResponse(BaseModel):
    job_id: str
    status: str
    text: Optional[str] = None
    segments: Optional[list] = None
    language: Optional[str] = None
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Load the Whisper model on startup"""
    global model
    logger.info(f"Loading Whisper model: {MODEL_SIZE}")
    model = whisper.load_model(MODEL_SIZE)
    logger.info("Model loaded successfully!")

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
    background_tasks: BackgroundTasks,
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

        # Start background transcription
        background_tasks.add_task(
            transcribe_audio_task,
            job_id,
            temp_file_path,
            language
        )

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
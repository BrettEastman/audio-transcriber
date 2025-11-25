# Audio Transcriber (Browser Edition)

## Overview

- **Web-first experience**: A SvelteKit frontend that accepts uploaded audio and displays AI-generated transcripts with timestamps and metadata.
- **FastAPI backend**: Hosts the transcription queue, exposes REST endpoints, and processes uploads via OpenAI Whisper (or compatible models).
- **Browser focus**: The project ships as a documented web stack—no desktop runtimes—so anyone can clone, run, and contribute via their browser.

## Stack

- Frontend: SvelteKit + Vite, TypeScript, scoped CSS.
- Backend: FastAPI + Whisper/pytorch, Python 3.12.
- Tooling: `start.sh` boots both services together (frontend on 5173, backend on 8000).

## Getting started

### 1. Prerequisites

- `python3.12` (or compatible 3.12.x environment) with `pip`.
- Node.js (tested on v22.x via Volta or nvm) and `npm`.
- Optional: `ffmpeg` if audio formats require transcoding.

### 2. Backend setup (one-time)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- The backend listens on `http://localhost:8000` and exposes `/docs` for OpenAPI.
- Uploads via the frontend stream through `transcriptionStore.uploadFile` with progress callbacks.

### 3. Frontend setup (one-time)

```bash
cd frontend
npm install
```

- The SvelteKit app runs on `http://localhost:5173` and targets the backend API.
- Use `npm run build` → `npm run preview` to test the production build locally.

### 4. Run both together

After completing the one-time setup above, you can start both services with:

```bash
./start.sh
```

- `start.sh` activates the backend venv, boots `main.py`, waits a few seconds, then runs `npm run dev`.
- Press `Ctrl+C` once to stop both servers.

## Troubleshooting

- Permissions errors when running `npm install` usually mean you need a clean Volta/node install.
- If uploads fail, open `backend/main.py` logs for `whisper` errors and verify the frontend is pointing to the correct backend endpoint in `frontend/src/lib/api.ts`.

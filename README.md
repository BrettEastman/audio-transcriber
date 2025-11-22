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

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

- The backend listens on `http://localhost:8000` and exposes `/docs` for OpenAPI.
- Uploads via the frontend stream through `transcriptionStore.uploadFile` with progress callbacks.

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

- The SvelteKit app runs on `http://localhost:5173` and targets the backend API.
- Use `npm run build` → `npm run preview` to test the production build locally.

### 4. Run both together

- Use the repo root helper:

```bash
./start.sh
```

- `start.sh` activates the backend venv, boots `main.py`, waits a few seconds, then runs `npm run dev`.
- Press `Ctrl+C` once to stop both servers.

## Contribution & deployment notes

- Keep the backend S3/Cloud storage credentials out of the repo—use environment variables when you plug in hosting.
- For CI/contribution: run `backend/main.py` (with coverage) and `npm run check` inside `frontend`.
- Build the frontend static assets via `npm run build` and host them behind any static asset server that proxies to the FastAPI API.
- Document new features in this README and refresh `/frontend/src/lib/components` docs as needed.

## Share/Showcase guidance

- To share on LinkedIn or GitHub: highlight the browser-first audio workflow, mention the Svelte store integration, and point contributors to:
  - `frontend/src/lib/api.ts` for upload logic,
  - `frontend/src/lib/stores/transcription.ts` for state management,
  - `backend/main.py` for the transcription pipeline.
- Encourage contributors to add tests or UI polish, then open pull requests with clear changelog entries.

## Troubleshooting

- Permissions errors when running `npm install` usually mean you need a clean Volta/node install.
- If uploads fail, open `backend/main.py` logs for `whisper` errors and verify the frontend uses the right endpoint via the `.env` settings in `frontend/src/lib/api.ts`.



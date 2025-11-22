# Frontend (SvelteKit)

This SvelteKit app powers the browser experience for Audio Transcriber. The UI uploads audio, tracks progress, and renders transcribed segments from the FastAPI backend.

## Getting started

```bash
cd frontend
npm install
npm run dev
```

- The dev server runs on `http://localhost:5173` and proxies workspace API calls to `http://localhost:8000`.
- Keep `frontend/src/lib/api.ts` aligned with `shared/types.ts` when you introduce new payloads.

## Build & preview

```bash
npm run build
npm run preview
```

- Use `npm run preview` to sanity-check the production bundle before sharing it locally.
- Ensure any new assets (icons, fonts) are referenced from `/static` or `/src/lib/assets` so Vite can bundle them.

## QA & linting

```bash
npm run check
npm run check:watch
```

- `svelte-check` enforces typing/contracts for stores, props, and components.
- Run `npm run check` in CI to guard against regressions.

## Recommended workflow

- Run `../start.sh` from the repo root to boot both services. If you prefer to run services individually, start the backend (./backend/main.py) first before running npm run dev
- Refresh `frontend/README.md` instructions after you change the build or dev commands.

For broader execution details, see the repo-level `README.md`.

# Wine in a Million — Frontend (2026)

Vite + React 19 + TypeScript replacement for the original Create React App
client. It is deployed as a **Cloudflare Worker with Static Assets** separate
from the Cloud Run API, so the page itself never cold-starts. The Worker serves
the Vite build and proxies same-origin `/api/*` calls to Cloud Run. The UI calls
the FastAPI backend's `POST /search` endpoint through that proxy, renders ranked
wine cards with a match score, and streams the LLM "sommelier's note".

## Dev

```bash
npm install
cp .env.example .env       # VITE_API_TARGET -> your backend
npm run dev                # http://localhost:5173, proxies /api -> :8000
```

## Build

```bash
npm run build && npm run preview
```

## Cloudflare Workers deploy

The app uses the default same-origin `VITE_API_BASE=/api`.

- local Docker: nginx proxies `/api/*` to the `backend` service
- production: the Cloudflare Worker proxies `/api/*` to Cloud Run

Production deployment is handled by the root Makefile:

```bash
make deploy
```

For local Worker testing:

```bash
npm run dev:worker
```

On load, the app polls `GET /api/health?warm=true` with a short timeout. If
Cloud Run is cold, users see a "Warming the API" indicator while the Worker
wakes the backend container and force-loads the embedding model.

## Notes for the upgrade

- Create React App → **Vite 6** (CRA is deprecated).
- Class components → **function components + hooks**.
- Plain JS → **TypeScript** with a typed API client (`src/api.ts`).
- Material-UI v4 → hand-rolled CSS (swap in MUI v6 / shadcn if preferred).
- The old client never actually called the model; this one does, with proper
  loading and error states.

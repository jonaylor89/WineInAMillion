# Wine in a Million — Frontend (2026)

Vite + React 19 + TypeScript replacement for the original Create React App
client. It calls the FastAPI backend's `POST /search` endpoint, renders ranked
wine cards with a match score, and shows the optional LLM "sommelier's note".

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

## Notes for the upgrade

- Create React App → **Vite 6** (CRA is deprecated).
- Class components → **function components + hooks**.
- Plain JS → **TypeScript** with a typed API client (`src/api.ts`).
- Material-UI v4 → hand-rolled CSS (swap in MUI v6 / shadcn if preferred).
- The old client never actually called the model; this one does, with proper
  loading and error states.

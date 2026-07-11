// Typed client for the FastAPI backend. In dev, Vite proxies /api -> :8000.

export interface Wine {
  title: string | null;
  variety: string | null;
  winery: string | null;
  country: string | null;
  province: string | null;
  price: number | null;
  points: number | null;
  description: string | null;
  similarity: number | null;
}

export interface SearchResponse {
  query: string;
  wines: Wine[];
  recommendation: string | null;
}

export interface ApiHealth {
  status: "ok";
  version: string;
  table_ready: boolean;
  model_ready: boolean;
  llm_configured: boolean;
  embedding_model: string;
}

export type SearchStreamEvent =
  | { type: "status"; message: string }
  | { type: "wines"; wines: Wine[] }
  | { type: "recommendation_delta"; delta: string }
  | { type: "recommendation_error"; message: string }
  | { type: "recommendation_done" }
  | { type: "done" };

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function parseError(res: Response): Promise<Error> {
  const detail = (await res.json().catch(() => null)) as { detail?: string } | null;
  return new Error(detail?.detail ?? `Request failed (${res.status})`);
}

export async function checkApiHealth(timeoutMs = 2500): Promise<ApiHealth> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${BASE}/health?warm=true`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`Health check failed (${res.status})`);
    return res.json();
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function streamSearchWines(
  query: string,
  onEvent: (event: SearchStreamEvent) => void,
  k = 5,
): Promise<void> {
  const res = await fetch(`${BASE}/search/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, k }),
  });

  if (!res.ok) throw await parseError(res);
  if (!res.body) throw new Error("Streaming is not supported by this browser");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.trim()) continue;
      onEvent(JSON.parse(line) as SearchStreamEvent);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    onEvent(JSON.parse(buffer) as SearchStreamEvent);
  }
}

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

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export async function searchWines(
  query: string,
  k = 5,
  explain = true,
): Promise<SearchResponse> {
  const res = await fetch(`${BASE}/search`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, k, explain }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

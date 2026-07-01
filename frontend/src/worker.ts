/// <reference types="@cloudflare/workers-types" />

export interface Env {
  ASSETS: Fetcher;
  API_ORIGIN: string;
}

function apiTarget(request: Request, apiOrigin: string): URL {
  const incoming = new URL(request.url);
  const target = new URL(apiOrigin);
  target.pathname = incoming.pathname.replace(/^\/api/, "") || "/";
  target.search = incoming.search;
  return target;
}

function proxyHeaders(request: Request): Headers {
  const headers = new Headers(request.headers);
  headers.delete("host");
  return headers;
}

async function proxyApi(request: Request, env: Env): Promise<Response> {
  if (!env.API_ORIGIN) {
    return Response.json(
      { detail: "API_ORIGIN is not configured on the Cloudflare Worker." },
      { status: 500 },
    );
  }

  const target = apiTarget(request, env.API_ORIGIN);
  const proxied = new Request(target, {
    method: request.method,
    headers: proxyHeaders(request),
    body: request.body,
    redirect: "manual",
  });

  return fetch(proxied);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/api" || url.pathname.startsWith("/api/")) {
      return proxyApi(request, env);
    }

    return env.ASSETS.fetch(request);
  },
};

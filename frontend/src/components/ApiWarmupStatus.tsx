import { useEffect, useState } from "react";
import { checkApiHealth, type ApiHealth } from "../api";

export type ApiWarmupState =
  | { kind: "checking"; attempt: number; elapsedMs: number }
  | { kind: "warming"; attempt: number; elapsedMs: number; message: string }
  | { kind: "ready"; attempt: number; elapsedMs: number; health: ApiHealth }
  | { kind: "degraded"; attempt: number; elapsedMs: number; health: ApiHealth }
  | { kind: "unavailable"; attempt: number; elapsedMs: number; message: string };

interface Props {
  onReadyChange?: (ready: boolean) => void;
}

function elapsed(startedAt: number) {
  return Date.now() - startedAt;
}

function seconds(ms: number) {
  return Math.max(1, Math.round(ms / 1000));
}

export function ApiWarmupStatus({ onReadyChange }: Props) {
  const [state, setState] = useState<ApiWarmupState>({
    kind: "checking",
    attempt: 0,
    elapsedMs: 0,
  });

  useEffect(() => {
    let cancelled = false;
    let timeout: number | undefined;
    const startedAt = Date.now();

    async function poll(attempt: number) {
      if (cancelled) return;
      setState({ kind: "checking", attempt, elapsedMs: elapsed(startedAt) });

      try {
        const health = await checkApiHealth(5000);
        if (cancelled) return;

        if (health.table_ready && health.model_ready && health.llm_configured) {
          setState({ kind: "ready", attempt, elapsedMs: elapsed(startedAt), health });
          onReadyChange?.(true);
        } else {
          setState({ kind: "degraded", attempt, elapsedMs: elapsed(startedAt), health });
          onReadyChange?.(false);
        }
      } catch (e) {
        if (cancelled) return;
        const message =
          e instanceof DOMException && e.name === "AbortError"
            ? "The API is still waking up. Cloud Run is starting a container and loading the embedding model."
            : "The API is not reachable yet. Retrying…";
        const elapsedMs = elapsed(startedAt);
        const kind = elapsedMs > 90_000 ? "unavailable" : "warming";
        setState({ kind, attempt, elapsedMs, message });
        onReadyChange?.(false);

        const nextDelay = Math.min(1500 + attempt * 750, 5000);
        timeout = window.setTimeout(() => poll(attempt + 1), nextDelay);
      }
    }

    poll(1);
    return () => {
      cancelled = true;
      if (timeout) window.clearTimeout(timeout);
    };
  }, [onReadyChange]);

  if (state.kind === "ready") {
    return (
      <aside className="api-status ready" aria-live="polite">
        <span className="dot" /> API ready · vectors + model loaded · {state.health.embedding_model}
      </aside>
    );
  }

  if (state.kind === "degraded") {
    return (
      <aside className="api-status degraded" aria-live="polite">
        <span className="dot" /> API awake, but configuration is incomplete. Check the LanceDB table and LLM_API_KEY.
      </aside>
    );
  }

  return (
    <aside className={`api-status ${state.kind}`} aria-live="polite">
      <span className="spinner" />
      <div>
        <b>{state.kind === "unavailable" ? "Still waiting for the API" : "Warming the API"}</b>
        <p>
          {state.kind === "checking"
            ? "Checking Cloud Run…"
            : state.message} {" "}
          Attempt {state.attempt} · {seconds(state.elapsedMs)}s elapsed
        </p>
      </div>
    </aside>
  );
}

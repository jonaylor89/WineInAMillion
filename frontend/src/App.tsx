import { useCallback, useState } from "react";
import { streamSearchWines, type SearchResponse } from "./api";
import { ApiWarmupStatus } from "./components/ApiWarmupStatus";
import { SearchBox } from "./components/SearchBox";
import { WineCard } from "./components/WineCard";
import "./App.css";

export default function App() {
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiReady, setApiReady] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);

  const handleReadyChange = useCallback((ready: boolean) => {
    setApiReady(ready);
  }, []);

  async function handleSearch(query: string) {
    setLoading(true);
    setError(null);
    setStreamStatus("Starting search…");
    setResult({ query, wines: [], recommendation: "" });
    try {
      await streamSearchWines(query, (event) => {
        if (event.type === "status") {
          setStreamStatus(event.message);
        }
        if (event.type === "wines") {
          setResult((current) => ({
            query,
            wines: event.wines,
            recommendation: current?.recommendation ?? "",
          }));
        }
        if (event.type === "recommendation_delta") {
          setResult((current) => ({
            query,
            wines: current?.wines ?? [],
            recommendation: `${current?.recommendation ?? ""}${event.delta}`,
          }));
        }
        if (event.type === "recommendation_error") {
          setError(event.message);
          setStreamStatus(null);
        }
        if (event.type === "recommendation_done" || event.type === "done") {
          setStreamStatus(null);
        }
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setResult(null);
    } finally {
      setStreamStatus(null);
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <nav className="topbar" aria-label="Application">
        <a className="brand" href="/" aria-label="Wine in a Million home">
          <span className="brand-mark">W</span>
          <span>Wine in a Million</span>
        </a>
        <div className="topbar-status">
          <ApiWarmupStatus onReadyChange={handleReadyChange} />
        </div>
      </nav>

      <section className={`search-stage ${result ? "search-stage-compact" : ""}`}>
        {!result && (
          <div className="hero-lockup">
            <img
              className="hero-image"
              src="https://cdn.dribbble.com/users/500242/screenshots/4198035/airbnb-wine-toast.gif"
              alt="Animated wine toast"
            />
            <p className="eyebrow">Semantic sommelier</p>
            <h1>What wine should we open?</h1>
            <p className="tagline">
              Ask naturally. We search 130k reviews, cite the closest bottles,
              and stream a concise recommendation.
            </p>
          </div>
        )}

        <SearchBox
          onSearch={handleSearch}
          loading={loading}
          disabled={!apiReady}
          disabledReason="The recommendation API is still warming up."
        />
      </section>

      {error && <p className="error">⚠ {error}</p>}
      {streamStatus && <p className="stream-status">{streamStatus}</p>}

      {result && (
        <section className="answer-layout" aria-live="polite">
          <article className={`answer-card ${loading ? "streaming" : ""}`}>
            <div className="answer-header">
              <p className="section-label">Answer</p>
              <p className="query-chip">{result.query}</p>
            </div>
            {result.recommendation ? (
              <p className="answer-text">{result.recommendation}</p>
            ) : (
              <p className="answer-placeholder">Searching reviews and drafting your answer…</p>
            )}
          </article>

          <aside className="sources-panel" aria-label="Recommended wine sources">
            <div className="sources-header">
              <h2>Sources</h2>
              <span>{result.wines.length || "—"} wines</span>
            </div>
            <div className="results">
              {result.wines.map((wine, i) => (
                <WineCard key={`${wine.title}-${i}`} wine={wine} rank={i + 1} />
              ))}
            </div>
          </aside>
        </section>
      )}
    </main>
  );
}

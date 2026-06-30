import { useState } from "react";
import { searchWines, type SearchResponse } from "./api";
import { SearchBox } from "./components/SearchBox";
import { WineCard } from "./components/WineCard";
import "./App.css";

export default function App() {
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(query: string) {
    setLoading(true);
    setError(null);
    try {
      setResult(await searchWines(query));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <header className="hero">
        <h1>
          Wine <span>in a Million</span>
        </h1>
        <p className="tagline">
          Describe the wine you're after — a mood, a meal, a vibe — and we'll
          find the closest matches from 130k reviews.
        </p>
      </header>

      <SearchBox onSearch={handleSearch} loading={loading} />

      {error && <p className="error">⚠ {error}</p>}

      {result?.recommendation && (
        <section className="sommelier">
          <h2>Sommelier's note</h2>
          <p>{result.recommendation}</p>
        </section>
      )}

      <section className="results">
        {result?.wines.map((wine, i) => (
          <WineCard key={`${wine.title}-${i}`} wine={wine} />
        ))}
      </section>
    </main>
  );
}

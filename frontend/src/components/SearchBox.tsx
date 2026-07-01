import { useState, type FormEvent } from "react";

interface Props {
  onSearch: (query: string) => void;
  loading: boolean;
  disabled?: boolean;
  disabledReason?: string;
}

const EXAMPLES = [
  "bold earthy red for steak night",
  "crisp citrusy white under $20",
  "smooth fruity wine for someone new to wine",
];

export function SearchBox({ onSearch, loading, disabled = false, disabledReason }: Props) {
  const [query, setQuery] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (q && !loading && !disabled) onSearch(q);
  }

  return (
    <form className="searchbox" onSubmit={submit}>
      <label className="search-label" htmlFor="wine-query">
        Ask a wine question
      </label>
      <div className="composer">
        <textarea
          id="wine-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask for a wine by meal, mood, texture, budget, or flavor…"
          rows={3}
        />
        <button className="primary" type="submit" disabled={loading || disabled} aria-label="Search wines">
          {loading ? "…" : "↑"}
        </button>
      </div>
      <div className="examples" aria-label="Example searches">
        {EXAMPLES.map((ex) => (
          <button key={ex} type="button" onClick={() => setQuery(ex)}>
            {ex}
          </button>
        ))}
      </div>
      {disabled && disabledReason && <p className="disabled-note">{disabledReason}</p>}
    </form>
  );
}

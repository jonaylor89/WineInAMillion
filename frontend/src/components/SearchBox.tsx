import { useState, type FormEvent } from "react";

interface Props {
  onSearch: (query: string) => void;
  loading: boolean;
}

const EXAMPLES = [
  "bold earthy red for steak night",
  "crisp citrusy white under $20",
  "smooth fruity wine for someone new to wine",
];

export function SearchBox({ onSearch, loading }: Props) {
  const [query, setQuery] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (q && !loading) onSearch(q);
  }

  return (
    <form className="searchbox" onSubmit={submit}>
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="What are you in the mood for?"
        rows={3}
      />
      <div className="searchbox-row">
        <div className="examples">
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" onClick={() => setQuery(ex)}>
              {ex}
            </button>
          ))}
        </div>
        <button className="primary" type="submit" disabled={loading}>
          {loading ? "Pouring…" : "Find wines"}
        </button>
      </div>
    </form>
  );
}

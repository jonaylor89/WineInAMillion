import type { Wine } from "../api";

export function WineCard({ wine }: { wine: Wine }) {
  const match = wine.similarity != null ? Math.round(wine.similarity * 100) : null;

  return (
    <article className="card">
      <div className="card-head">
        <h3>{wine.title ?? "Unknown wine"}</h3>
        {match != null && <span className="match">{match}% match</span>}
      </div>

      <p className="meta">
        {[wine.variety, wine.winery].filter(Boolean).join(" · ")}
      </p>

      <p className="description">{wine.description}</p>

      <footer className="card-foot">
        <span>{[wine.province, wine.country].filter(Boolean).join(", ")}</span>
        <span className="stats">
          {wine.points != null && <b>{wine.points} pts</b>}
          {wine.price != null && <span> · ${wine.price.toFixed(0)}</span>}
        </span>
      </footer>
    </article>
  );
}

import type { Wine } from "../api";

export function WineCard({ wine, rank }: { wine: Wine; rank: number }) {
  const match = wine.similarity != null ? Math.round(wine.similarity * 100) : null;
  const location = [wine.province, wine.country].filter(Boolean).join(", ");
  const maker = [wine.variety, wine.winery].filter(Boolean).join(" · ");

  return (
    <article className="source-card">
      <div className="source-index">{rank}</div>
      <div className="source-content">
        <div className="source-topline">
          {match != null && <span>{match}% semantic match</span>}
          {wine.points != null && <span>{wine.points} pts</span>}
          {wine.price != null && <span>${wine.price.toFixed(0)}</span>}
        </div>
        <h3>{wine.title ?? "Unknown wine"}</h3>
        {maker && <p className="source-meta">{maker}</p>}
        <p className="source-snippet">{wine.description}</p>
        {location && <p className="source-location">{location}</p>}
      </div>
    </article>
  );
}

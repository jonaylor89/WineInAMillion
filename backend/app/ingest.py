"""Ingestion job: CSV reviews -> embeddings -> LanceDB table on object storage.

This replaces the 2019 two-step SageMaker pipeline (an embeddings training job
that wrote ``embeddings.csv.gz`` to S3, then a separate job that fit a
scikit-learn ``NearestNeighbors`` model). Now it is a single idempotent script:
read the wine reviews, embed the descriptions in batches, and write everything
into one LanceDB table that lives in the bucket.

Usage:
    uv run python -m app.ingest --csv data/winemag-data-130k-v2.csv
    uv run python -m app.ingest --csv data/winemag-data-130k-v2.csv --limit 2000
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd
from tqdm import tqdm

from .config import get_settings
from .embeddings import embed_documents
from .store import build_schema, connect

# Columns we keep from the Kaggle winemag dataset.
_COLUMNS = {
    "title": "title",
    "variety": "variety",
    "winery": "winery",
    "country": "country",
    "province": "province",
    "price": "price",
    "points": "points",
    "description": "description",
}


def load_reviews(csv_path: str, limit: int | None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    available = {src: dst for src, dst in _COLUMNS.items() if src in df.columns}
    df = df[list(available.keys())].rename(columns=available)
    df = df.dropna(subset=["description"]).drop_duplicates(subset=["title", "description"])
    if limit:
        df = df.head(limit)
    return df.reset_index(drop=True)


def to_records(df: pd.DataFrame, batch_size: int) -> list[dict]:
    records: list[dict] = []
    descriptions = df["description"].tolist()
    vectors = []
    for start in tqdm(range(0, len(descriptions), batch_size), desc="embedding"):
        chunk = descriptions[start : start + batch_size]
        vectors.extend(embed_documents(chunk, batch_size=batch_size))

    for row, vector in zip(df.to_dict(orient="records"), vectors, strict=True):
        records.append(
            {
                "vector": vector.tolist(),
                "title": _s(row.get("title")),
                "variety": _s(row.get("variety")),
                "winery": _s(row.get("winery")),
                "country": _s(row.get("country")),
                "province": _s(row.get("province")),
                "price": _f(row.get("price")),
                "points": _i(row.get("points")),
                "description": _s(row.get("description")),
            }
        )
    return records


def _s(v) -> str | None:
    return None if pd.isna(v) else str(v)


def _f(v) -> float | None:
    return None if pd.isna(v) else float(v)


def _i(v) -> int | None:
    return None if pd.isna(v) else int(v)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest wine reviews into LanceDB")
    parser.add_argument("--csv", required=True, help="Path to winemag CSV")
    parser.add_argument("--limit", type=int, default=None, help="Only ingest the first N rows")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Drop and recreate the table instead of appending",
    )
    args = parser.parse_args()

    settings = get_settings()
    print(f"Loading reviews from {args.csv} ...")
    df = load_reviews(args.csv, args.limit)
    print(f"  {len(df):,} reviews after cleaning")

    print(f"Embedding with {settings.embedding_model} ...")
    records = to_records(df, args.batch_size)

    db = connect()
    mode = "overwrite" if args.overwrite else "create"
    existing = settings.lancedb_table in db.table_names()

    if existing and not args.overwrite:
        table = db.open_table(settings.lancedb_table)
        table.add(records)
        print(f"Appended {len(records):,} rows to '{settings.lancedb_table}'")
    else:
        table = db.create_table(
            settings.lancedb_table,
            data=records,
            schema=build_schema(settings.embedding_dim),
            mode=mode,
        )
        print(
            f"Wrote {len(records):,} rows to "
            f"'{settings.lancedb_table}' at {settings.lancedb_uri}"
        )

    print("Done.")


if __name__ == "__main__":
    sys.exit(main())

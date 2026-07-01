"""Ingestion job: CSV reviews -> embeddings -> LanceDB table on object storage.

This replaces the 2019 two-step SageMaker pipeline (an embeddings training job
that wrote ``embeddings.csv.gz`` to S3, then a separate job that fit a
scikit-learn ``NearestNeighbors`` model). Now it is a single idempotent script:
read the wine reviews, embed the descriptions in batches, and write each batch
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


def batch_to_records(df: pd.DataFrame, batch_size: int) -> list[dict]:
    """Embed one dataframe batch and convert it to LanceDB records.

    Important: this intentionally only holds one batch of vectors in memory.
    The previous implementation accumulated all 130k vectors and OOMed at the
    end of the Cloud Run Job before it could write the LanceDB table.
    """
    descriptions = df["description"].tolist()
    vectors = embed_documents(descriptions, batch_size=batch_size)
    records: list[dict] = []

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

    db = connect()
    existing = settings.lancedb_table in db.table_names()
    table = db.open_table(settings.lancedb_table) if existing and not args.overwrite else None
    mode = "overwrite" if args.overwrite else "create"
    written = 0

    print(f"Embedding with {settings.embedding_model} and writing to {settings.lancedb_uri} ...")
    for start in tqdm(range(0, len(df), args.batch_size), desc="embedding+writes"):
        batch_df = df.iloc[start : start + args.batch_size]
        records = batch_to_records(batch_df, args.batch_size)
        if not records:
            continue

        if table is None:
            table = db.create_table(
                settings.lancedb_table,
                data=records,
                schema=build_schema(settings.embedding_dim),
                mode=mode,
            )
        else:
            table.add(records)
        written += len(records)

    print(f"Wrote {written:,} rows to '{settings.lancedb_table}' at {settings.lancedb_uri}")
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())

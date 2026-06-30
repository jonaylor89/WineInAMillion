"""LanceDB access layer.

The whole point of the 2026 rewrite: instead of fitting a scikit-learn
``NearestNeighbors`` model in memory and dumping CSV embeddings to S3, we keep
a LanceDB table *on object storage*. LanceDB does the ANN search directly
against the columnar Lance files in the bucket, so there is no vector-DB server
to run or pay for — just cheap blob storage (MinIO locally, S3/GCS in prod).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import lancedb
import pyarrow as pa

from .config import get_settings


def build_schema(dim: int) -> pa.Schema:
    return pa.schema(
        [
            pa.field("vector", pa.list_(pa.float32(), dim)),
            pa.field("title", pa.string()),
            pa.field("variety", pa.string()),
            pa.field("winery", pa.string()),
            pa.field("country", pa.string()),
            pa.field("province", pa.string()),
            pa.field("price", pa.float64()),
            pa.field("points", pa.int64()),
            pa.field("description", pa.string()),
        ]
    )


@lru_cache
def connect() -> lancedb.DBConnection:
    settings = get_settings()
    return lancedb.connect(
        settings.lancedb_uri,
        storage_options=settings.storage_options(),
    )


def open_table() -> lancedb.table.Table:
    settings = get_settings()
    return connect().open_table(settings.lancedb_table)


def table_exists() -> bool:
    settings = get_settings()
    return settings.lancedb_table in connect().table_names()


def search(vector: list[float], k: int) -> list[dict[str, Any]]:
    """Cosine ANN search returning the k closest wines plus a distance."""
    table = open_table()
    results = (
        table.search(vector)
        .metric("cosine")
        .limit(k)
        .to_list()
    )
    wines: list[dict[str, Any]] = []
    for row in results:
        row.pop("vector", None)
        # LanceDB returns cosine *distance*; convert to a 0..1 similarity.
        distance = row.pop("_distance", None)
        if distance is not None:
            row["similarity"] = round(1.0 - float(distance), 4)
        wines.append(row)
    return wines

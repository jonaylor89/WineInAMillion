#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "kaggle>=1.6.17",
#   "python-dotenv>=1.0.1",
# ]
# ///
"""Download the Wine Reviews Kaggle dataset using uv-managed dependencies.

This script intentionally does not require `pip install kaggle`. `uv run
--script` creates/caches an isolated environment with the Kaggle client and
python-dotenv, then downloads/unzips the dataset.

Configuration is read from the repo root `.env` when present:

    KAGGLE_API_TOKEN=...
    KAGGLE_DATASET=zynicide/wine-reviews
    KAGGLE_OUT_DIR=backend/data

Alternatively, the standard `~/.kaggle/kaggle.json` file works too.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

from dotenv import load_dotenv

EXPECTED_CSV = "winemag-data-130k-v2.csv"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config() -> None:
    load_dotenv(repo_root() / ".env", override=False)


def check_credentials() -> None:
    access_token = Path.home() / ".kaggle" / "access_token"
    legacy_json = Path.home() / ".kaggle" / "kaggle.json"
    has_new_file = access_token.exists()
    has_legacy_file = legacy_json.exists()
    has_new_env = bool(os.getenv("KAGGLE_API_TOKEN"))
    has_legacy_env = bool(os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"))

    for path in (access_token, legacy_json):
        if path.exists():
            # Kaggle warns/fails on overly permissive credentials files.
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    if has_new_file or has_legacy_file or has_new_env or has_legacy_env:
        return

    print(
        "Kaggle credentials not found.\n\n"
        "Create an API token at https://www.kaggle.com/settings/api, then put it in .env:\n\n"
        "  KAGGLE_API_TOKEN=...\n\n"
        "or use Kaggle's local auth flow:\n\n"
        "  uvx --from kaggle kaggle auth login\n\n"
        "Legacy ~/.kaggle/kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY may also work\n"
        "depending on the Kaggle client version.\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


def main() -> int:
    load_config()

    root = repo_root()
    dataset = os.getenv("KAGGLE_DATASET", "zynicide/wine-reviews")
    out_dir = Path(os.getenv("KAGGLE_OUT_DIR", "backend/data"))
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    expected = out_dir / EXPECTED_CSV
    if expected.exists():
        print(f"Dataset already present: {expected}")
        return 0

    check_credentials()

    print(f"Downloading Kaggle dataset '{dataset}' to {out_dir} ...")
    # Import after credential checks; recent Kaggle clients authenticate during import.
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(dataset, path=str(out_dir), unzip=True, quiet=False)

    if not expected.exists():
        print(f"Download finished, but expected CSV was not found: {expected}", file=sys.stderr)
        print("Files downloaded:", file=sys.stderr)
        for path in sorted(out_dir.glob("**/*")):
            if path.is_file():
                print(f"  {path.relative_to(out_dir)}", file=sys.stderr)
        return 1

    print(f"Dataset ready: {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

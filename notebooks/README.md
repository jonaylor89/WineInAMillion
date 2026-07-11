# Notebooks (legacy — 2019)

These are the **original** SageMaker artifacts, kept for reference and for the
blog post's before/after comparison:

- `Wine In A Million.ipynb` — the original walkthrough
- `src/embeddings_script.py` — SageMaker job that embedded reviews and wrote
  `embeddings.csv.gz` to S3
- `src/nn_script.py` — SageMaker job that fit a scikit-learn `NearestNeighbors`
  model over those embeddings

The 2026 rewrite replaces all of this with a single LanceDB table on object
storage plus a FastAPI service. See [`../backend/`](../backend/) and the root
[`README.md`](../README.md).

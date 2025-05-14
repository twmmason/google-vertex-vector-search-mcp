"""
Bootstrap script to create and deploy a Google Vertex AI Vector Search index
from existing embeddings stored in Postgres.

Steps performed:
1. Extract `id, embedding` rows from the `memories` table
2. Save to Parquet and upload to a provided GCS bucket
3. Create a Tree-AH Matching-Engine index
4. Spin up an IndexEndpoint and deploy the index
5. Print VERTEX_INDEX_ID and VERTEX_ENDPOINT_ID lines for your .env

Usage example:
  python create_vertex_index.py \
    --project my-gcp-project \
    --region us-central1 \
    --db-url postgresql://user:pass@host/db \
    --gcs-bucket gs://my-bucket/embeddings \
    --dimensions 768
"""

import argparse
import tempfile
from pathlib import Path

import pandas as pd
from google.cloud import aiplatform
from sqlalchemy import create_engine, text


def extract_embeddings(db_url: str) -> pd.DataFrame:
    engine = create_engine(db_url)
    sql = text(
        "SELECT id::text AS datapoint_id, embedding "
        "FROM memories WHERE embedding IS NOT NULL"
    )
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--region", default="us-central1")
    ap.add_argument("--db-url", required=True)
    ap.add_argument("--gcs-bucket", required=True)
    ap.add_argument("--dimensions", type=int, required=True)
    ap.add_argument("--display-name", default="vertexmemory-index")
    ap.add_argument("--machine-type", default="e2-standard-4")
    args = ap.parse_args()

    aiplatform.init(project=args.project, location=args.region)

    print("→ Extracting embeddings from Postgres …")
    df = extract_embeddings(args.db_url)
    if df.empty:
        raise RuntimeError("No embeddings with vectors found.")

    with tempfile.TemporaryDirectory() as tmp:
        parquet_path = Path(tmp) / "vectors.parquet"
        df.to_parquet(parquet_path, index=False)

        gcs_uri = f"{args.gcs_bucket.rstrip('/')}/vectors.parquet"
        print("→ Uploading vectors to", gcs_uri)
        aiplatform.StorageClient.upload(
            local_path=str(parquet_path),
            gcs_path=gcs_uri,
        )

    print("→ Creating Matching-Engine index (Tree-AH) …")
    index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=args.display_name,
        contents_delta_uri=gcs_uri,
        dimensions=args.dimensions,
        approximate_neighbors_count=100,
    )
    index.wait()
    print("   Index ready:", index.resource_name)

    print("→ Creating endpoint and deploying index …")
    endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=f"{args.display_name}-endpoint"
    )
    endpoint.deploy_index(
        index=index,
        deployed_index_id=f"{args.display_name}-deployed",
        machine_type=args.machine_type,
    )
    print("   Endpoint ready:", endpoint.resource_name)

    print("\n---  Add these lines to your .env  ---")
    print("VERTEX_INDEX_ID=", index.resource_name)
    print("VERTEX_ENDPOINT_ID=", endpoint.resource_name)
    print("--------------------------------------")


if __name__ == "__main__":
    main()
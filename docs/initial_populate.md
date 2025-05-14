Follow these steps to populate Vertex AI Vector Search with your existing embeddings and run the full stack locally.


────────────────────────────────────────────
0.1 Summary
────────────────────────────────────────────
Create GCS bucket & service-account, grant roles, download sa.json
Copy api/.env.example ➜ api/.env; fill VERTEX_* vars and OPENAI_API_KEY
Run python api/scripts/create_vertex_index.py … to extract DB embeddings, upload Parquet, create index + endpoint; copy printed INDEX/ENDPOINT IDs into .env
docker compose build && docker compose up -d starts API (8765) and UI (3000) containers using 
Verify with health-check and UI search.


────────────────────────────────────────────
1  Prerequisites
────────────────────────────────────────────
• gcloud CLI ≥ 466 installed and logged-in  
• A GCP project with Vertex AI and Cloud Storage APIs enabled  
• PostgreSQL accessible from your machine (or Cloud SQL Auth Proxy)  
• Docker Desktop (or Podman)  

────────────────────────────────────────────
2  Prepare a bucket & service account
────────────────────────────────────────────
# set convenience variables
PROJECT_ID=my-project
REGION=us-central1
BUCKET=$PROJECT_ID-vertex-embeddings

# create bucket
gsutil mb -l $REGION gs://$BUCKET

# create service-account and grant roles
gcloud iam service-accounts create vertex-vector-sa
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:vertex-vector-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/aiplatform.user
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:vertex-vector-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin

# download key
gcloud iam service-accounts keys create sa.json \
  --iam-account=vertex-vector-sa@$PROJECT_ID.iam.gserviceaccount.com

────────────────────────────────────────────
3  Create .env
────────────────────────────────────────────
cp api/.env.example api/.env
# edit api/.env
VERTEX_PROJECT=$PROJECT_ID
VERTEX_REGION=$REGION
VERTEX_SA_JSON=$(pwd)/sa.json
OPENAI_API_KEY=<your key>
# leave INDEX / ENDPOINT lines empty for now

────────────────────────────────────────────
4  Create & deploy the index
────────────────────────────────────────────
# activate virtual env (or rely on system Python)
python -m pip install -r api/requirements.txt psycopg2-binary pandas sqlalchemy

python api/scripts/create_vertex_index.py \
  --project $PROJECT_ID \
  --region  $REGION \
  --db-url  postgresql://USER:PASSWORD@HOST/DBNAME \
  --gcs-bucket gs://$BUCKET \
  --dimensions 768

When the script finishes it prints:

VERTEX_INDEX_ID=projects/.../indexes/123456789
VERTEX_ENDPOINT_ID=projects/.../indexEndpoints/987654321

Copy those two lines into api/.env.

────────────────────────────────────────────
5  Build & start the stack
────────────────────────────────────────────
docker compose build
docker compose up -d

The API is now at http://localhost:8765 and the Next.js UI at http://localhost:3000.  
Both containers inherit your .env via docker-compose; the MCP server will connect to Vertex AI using the service-account JSON you provided.

────────────────────────────────────────────
6  Verify
────────────────────────────────────────────
curl http://localhost:8765/health            # FastAPI health-check  
curl http://localhost:8765/memories?page=1   # confirm memories returned  
Open the UI and perform a search; results should come from Vertex AI.

────────────────────────────────────────────
Troubleshooting
────────────────────────────────────────────
• “403 PERMISSION_DENIED”: ensure the SA has `Vertex AI User` and `Storage Object Viewer`.  
• “No deployed indexes”: confirm you copied the endpoint ID and that `create_vertex_index.py` finished without error.  
• Latency issues: deploy the Docker host in the same region as your Vertex endpoint or use Cloud Run / GKE in production.

You are now running the migrated system locally with Google Vertex AI Vector Search.
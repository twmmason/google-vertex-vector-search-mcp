# Migration Plan – Google Cloud Vertex AI ➜ Google Vertex AI Vector Search  
_Last updated: 2025-05-14_

## 0. Purpose
Replace all Google Cloud Vertex AI / Qdrant / self-hosted vector-store logic with fully-managed **Google Vertex AI Vector Search** while preserving MCP-server semantics for clients.

---

## 1. Reference Material
* Vertex Vector Search Overview – https://cloud.google.com/vertex-ai/docs/vector-search/overview  
* Quickstart – https://cloud.google.com/vertex-ai/docs/vector-search/quickstart  
* Python SDK (`google-cloud-aiplatform==2.*`) docs – https://cloud.google.com/python/docs/reference/aiplatform/latest  
* ScaNN design – https://arxiv.org/abs/2008.03474  

---

## 2. Inventory of Google Cloud Vertex AI-specific Surface Area (search files `Google Cloud Vertex AI`)
| Layer | Files / Artifacts | Notes |
|-------|------------------|-------|
| **Docker** | `docker-compose.yml`, `api/Dockerfile`, `ui/Dockerfile` | Service `Google Cloud Vertex AI_store` (Qdrant) & images tagged `Google Cloud Vertex AI/*` |
| **Python API** | `api/app/utils/memory.py` (`from Google Cloud Vertex AI import Memory`, host=Google Cloud Vertex AI_store), `api/app/mcp_server.py` (server name), `api/requirements.txt` (`Google Cloud Vertex AIai`, `mcp[cli]`) | Direct SDK import + connection config |
| **Database seed** | Alembic migration inserts Google Cloud Vertex AI IDs | Will remain unaffected |
| **UI** | Strings in React pages (filter options, docs links) | Minor text edits |
| **Docs** | `docs/overview.mdx`, `docs/quickstart.mdx` reference Google Cloud Vertex AI repo | Need rewrite |

---

## 3. Target Architecture with Vertex AI

```mermaid
flowchart LR
  subgraph Google Cloud
    A[Index] -->|Deploy| B[IndexEndpoint]
  end
  C[MCP Server (FastAPI)] -- gcloud-auth --> B
  D[Postgres] --> C
  E[Next.js UI] --> C
```

Key points  
* Vector storage + serving is **fully managed** by Vertex; no container needed.  
* MCP Server authenticates with _service-account JSON_ via **ADC** (Application Default Credentials) or explicit credentials file.  
* All ingestion & query operations routed through Python SDK `vertex_ai.preview.matching_engine`.  

---

## 4. API Mapping

| Google Cloud Vertex AI (Qdrant)                      | Vertex Vector Search                              | Notes |
|-----------------------------------|---------------------------------------------------|-------|
| `Memory(vector, metadata)` insert | `UpsertDatapoints(datapoints=[Datapoint(...)] )`   | Vertex supports batch ≤ 100 vectors (adjust loops) |
| `search(vector, top_k, filter)`   | `find_neighbors(queries=[v], num_neighbors=k, filter="...")` | Filters: SQL-like string |
| **distance** (Cosine by default)  | `DistanceMeasureType.COSINE_DISTANCE`             | Choose per-index |
| Collection/host/port env vars     | **index_name** & **endpoint_name** (GCP resource IDs) | Region-scoped |
| Qdrant shard replica scaling      | Vertex auto-scales via `machine_type`, `min_replica_count` | |

---

## 5. Migration Steps (chronological)

1. **Prep GCP**  
   a. Enable Vertex AI API in desired region (e.g. `europe-west4`).  
   b. Create service account with `Vertex AI Administrator` & `Storage Object Viewer`.  
   c. Provision GCS bucket `gs://$PROJECT-vertexmemory-embeddings` (object versioning on).  

2. **Dependencies**  
   * Remove `Google Cloud Vertex AIai` and `qdrant-client`.  
   * Add `google-cloud-aiplatform>=2.19.0` (latest LTS).  
   * Pin `google-auth`, `grpcio` as required by SDK.  

3. **Docker / Compose**  
   * Delete `Google Cloud Vertex AI_store` service.  
   * Update `api/Dockerfile` base image to `python:3.11-slim` and install `google-cloud-aiplatform`.  
   * Re-tag images (`vertexmemory-mcp` ➜ `vertex-memory-mcp`).  

4. **Python Code Refactor**

| Task | File(s) | Action |
|------|---------|--------|
| Init Vertex client | `api/app/config.py` | Add `aiplatform.init(project, location, credentials_file)` |
| Abstraction | `api/app/utils/memory.py` | Replace `from Google Cloud Vertex AI import Memory` with wrapper around Vertex Datapoints; implement `VectorIndexClient` class with `upsert`, `query`, `delete` |
| Server name | `api/app/mcp_server.py` | `mcp = FastMCP("vertex-vector-mcp-server")` |
| Config env | `.env.example` | Add `VERTEX_PROJECT`, `VERTEX_REGION`, `VERTEX_INDEX_ID`, `VERTEX_ENDPOINT_ID`, `VERTEX_SA_JSON` |

5. **Implement Wrapper Class**

```python
from google.cloud import aiplatform

class VertexVectorClient:
    def __init__(self, index_id: str, endpoint_id: str, project: str, region: str):
        aiplatform.init(project=project, location=region)
        self.index = aiplatform.MatchingEngineIndex(index_name=index_id)
        self.endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_id)

    def upsert(self, vectors, ids, metadata):
        datapoints = [
            aiplatform.MatchingEngineIndexDatapoint(
                datapoint_id=i, feature_vector=v, restricts=[...]
            )
            for i, v in zip(ids, vectors)
        ]
        self.index.upsert_datapoints(datapoints)

    def query(self, vector, k=10, filter_str=""):
        response = self.endpoint.find_neighbors(
            deployed_index_id=self.endpoint.deployed_indexes[0].id,
            queries=[vector],
            num_neighbors=k,
            filter=filter_str,
        )
        return response
```

6. **Sample Index Bootstrap Script** (`scripts/create_index.py`)  
   * Reads embeddings from Postgres → writes parquet to GCS → calls `MatchingEngineIndex.create_tree_ah_index`.  
   * Outputs resource IDs to `.env`.  

7. **Unit & Integration Tests**  
   * Mock Vertex client locally with `unittest.mock`.  
   * Record latency & recall on staging GCP project.  

8. **Docs Update**  
   * Rewrite `/docs/overview.mdx` & `/docs/quickstart.mdx` with Vertex instructions (gcloud auth, index creation, env vars).  
   * Add **architecture diagram** & **cost estimate** section.  

9. **CI/CD**  
   * Update GitHub Actions: run `pip install google-cloud-aiplatform`, set `GOOGLE_APPLICATION_CREDENTIALS`.  

10. **Cleanup**  
    * Remove Google Cloud Vertex AI references (`search_files 'Google Cloud Vertex AI'` should yield zero).  
    * Delete Qdrant volumes from Compose.  

---

## 6. Known Gaps / Blockers

| Category | Risk | Mitigation |
|----------|------|------------|
| **Filter parity** | Google Cloud Vertex AI allowed nested JSON filter; Vertex expects SQL-like string. Complex filters may need rewrite. | Add helper that converts dict→SQL string with limited operators. |
| **Vector dimension** | Existing Google Cloud Vertex AI vectors must match `dimensions` defined at Vertex index creation. | Validate dim in bootstrap script. |
| **Batch limits** | Vertex hard-caps 100 vectors / realtime upsert. | Chunk larger ingest batches. |
| **Latency budget** | Cross-region calls add latency. | Deploy index in same region as compute (Cloud Run / GKE if used). |
| **Cost estimation** | Vertex bills per replica-hour. Mis-configured scaling can spike cost. | Use `min_replica_count=1`, autoscale, monitor first month. |
| **Quota** | 30 QPS default per endpoint. | File support ticket for increase if needed. |

---

## 7. Success Criteria

* All API tests (`pytest`) pass with Vertex backend.  
* `docker-compose up` no longer starts `Google Cloud Vertex AI_store`.  
* End-to-end memory creation & semantic search returns expected results matching baseline quality.  
* `search_files 'Google Cloud Vertex AI'` returns **0** occurrences.  
* Documentation guides a fresh user from Google account → deployed index → running UI in ≤ 20 minutes.  

---

## 8. Timeline & Owners

| Phase | Duration | Owner |
|-------|----------|-------|
| Discovery & PoC | 2 d | @backend |
| Code migration | 3 d | @backend |
| Docs & UI tweaks | 1 d | @docs |
| QA & cost tuning | 2 d | @qa |
| Prod rollout | 0.5 d | @devops |

Target completion: **T + 9 working days**.

---

## 9. Checklist

- [ ] Delete Google Cloud Vertex AI references  
- [ ] Add Vertex client wrapper  
- [ ] Environment variables & secrets in 1Password / Secret Manager  
- [ ] Create initial index & deploy endpoint (Terraform later)  
- [ ] Update README / docs  
- [ ] Pass CI tests  
- [ ] Cost alert set at 80 USD/month  

---

### Appendix A – Command Snippets

```bash
# Enable APIs & create service account
gcloud services enable aiplatform.googleapis.com
gcloud iam service-accounts create vertex-vector-sa
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:vertex-vector-sa@$PROJECT.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Build & deploy local stack
docker compose build api ui
docker compose up -d
```

_End of document_
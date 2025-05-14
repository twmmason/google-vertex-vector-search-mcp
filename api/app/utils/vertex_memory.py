import os
from typing import List, Sequence

from google.cloud import aiplatform

# from google.cloud.aiplatform import (
#     MatchingEngineIndex,
#     MatchingEngineIndexEndpoint,
#     MatchingEngineIndexDatapoint,
# )


DEFAULT_ENDPOINT_MACHINE_TYPE = "e2-standard-4"


class VertexVectorClient:
    """
    Thin wrapper around Google Vertex AI Vector Search (Matching Engine) that mimics
    the subset of operations used by the previous Google Cloud Vertex AI Memory client.
    """

    def __init__(
        self,
        project: str | None = None,
        region: str | None = None,
        index_id: str | None = None,
        endpoint_id: str | None = None,
        credentials_path: str | None = None,
    ):
        self.project = project or os.getenv("VERTEX_PROJECT")
        self.region = region or os.getenv("VERTEX_REGION", "us-central1")
        self.credentials_path = credentials_path or os.getenv("VERTEX_SA_JSON")

        if not self.project:
            raise ValueError("VERTEX_PROJECT environment variable not set")

        # Initialise Vertex SDK
        aiplatform.init(
            project=self.project,
            location=self.region,
            credentials_path=self.credentials_path or None,
        )

        # Resolve index / endpoint resource names
        self.index_name = index_id or os.getenv("VERTEX_INDEX_ID")
        self.endpoint_name = endpoint_id or os.getenv("VERTEX_ENDPOINT_ID")

        if not self.index_name or not self.endpoint_name:
            raise ValueError("VERTEX_INDEX_ID and VERTEX_ENDPOINT_ID must be provided")

        self.index = aiplatform.MatchingEngineIndexMatchingEngineIndex(index_name=self.index_name)
        self.endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=self.endpoint_name)

        # Assume first deployed index
        self._deployed_index_id = (
            self.endpoint.deployed_indexes[0].id
            if self.endpoint.deployed_indexes
            else None
        )
        if not self._deployed_index_id:
            raise RuntimeError(
                "Index is not deployed to endpoint. Deploy via console or script first."
            )

    # --------------------------------------------------------------------- #
    # Public API (compatibility with previous Google Cloud Vertex AI client)
    # --------------------------------------------------------------------- #

    def upsert(
        self,
        embeddings: Sequence[list[float]],
        ids: Sequence[str],
        metadata: Sequence[dict] | None = None,
        batch_size: int = 100,
    ):
        """
        Upsert datapoints into the index.
        Vertex hard-caps 100 datapoints per request => chunk accordingly.
        """
        if len(embeddings) != len(ids):
            raise ValueError("Embeddings and ids length mismatch")

        meta = metadata or [{} for _ in ids]

        for offset in range(0, len(ids), batch_size):
            batch_embeddings = embeddings[offset : offset + batch_size]
            batch_ids = ids[offset : offset + batch_size]
            batch_meta = meta[offset : offset + batch_size]

            datapoints = [
                aiplatform.MatchingEngineIndexDatapoint(
                    datapoint_id=did,
                    feature_vector=emb,
                    restricts=[],  # metadata filters via endpoint not supported here.
                    crowding_tag=None,
                )
                for did, emb in zip(batch_ids, batch_embeddings, strict=True)
            ]
            # Attach metadata to restricts later when filterable fields supported
            self.index.upsert_datapoints(datapoints=datapoints)

    def query(
        self,
        embedding: list[float],
        k: int = 10,
        filter_str: str | None = None,
    ):
        """
        Perform nearest neighbor search.
        """
        response = self.endpoint.find_neighbors(
            deployed_index_id=self._deployed_index_id,
            queries=[embedding],
            num_neighbors=k,
            filter=filter_str or "",
        )
        # Flatten structured response -> list[dict]
        neighbors = []
        if response and response.nearest_neighbors:
            for neighbor in response.nearest_neighbors[0].neighbors:
                neighbors.append(
                    {
                        "id": neighbor.datapoint.datapoint_id,
                        "distance": neighbor.distance,
                        "metadata": neighbor.datapoint.restricts,
                    }
                )
        return neighbors
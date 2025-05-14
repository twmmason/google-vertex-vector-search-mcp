"""
Utility wrapping a singleton VertexVectorClient for interacting with
Google Vertex AI Vector Search. Replaces the previous Google Cloud Vertex AI Memory client.
"""

import os
from functools import lru_cache

from app.utils.vertex_memory import VertexVectorClient


@lru_cache
def get_memory_client() -> VertexVectorClient:
    """
    Lazily initialise and return a VertexVectorClient.

    Environment variables expected:
      - VERTEX_PROJECT         (GCP project ID)            [required]
      - VERTEX_REGION          (Vertex region)             [default: us-central1]
      - VERTEX_INDEX_ID        (resource name or full path)
      - VERTEX_ENDPOINT_ID     (resource name or full path)
      - VERTEX_SA_JSON         (optional path to service-account JSON)
    """
    return VertexVectorClient()


def get_default_user_id() -> str:
    """Return the default user identifier used throughout the system."""
    return os.getenv("USER", "default_user")

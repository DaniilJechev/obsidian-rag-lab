"""Sparse BM25 retrieval against a Qdrant named vector slot."""

from collections.abc import Mapping

from qdrant_client import QdrantClient
from qdrant_client.models import Document

from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
)
from rag_based_on_obsidian.retrieval.progress import logger
from rag_based_on_obsidian.retrieval.qdrant_results import (
    BM25_MODEL_NAME,
    SPARSE_VECTOR_NAME,
    build_payload_filter,
    point_to_retrieved_chunk,
)


class QdrantSparseRetriever:
    """Search the BM25 sparse slot of one versioned Qdrant collection."""

    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        chunking_version: str,
        bm25_avg_len: float,
        bm25_model: str = BM25_MODEL_NAME,
        vector_name: str = SPARSE_VECTOR_NAME,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        if not chunking_version.strip():
            raise ValueError("chunking_version must not be empty")
        if bm25_avg_len <= 0:
            raise ValueError("bm25_avg_len must be positive")
        self.client = client
        self.collection_name = collection_name
        self.chunking_version = chunking_version
        self.bm25_avg_len = bm25_avg_len
        self.bm25_model = bm25_model
        self.vector_name = vector_name

    def search(
        self,
        query: str,
        *,
        top_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Return ranked lexical matches from the Qdrant sparse index."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        merged_filters = dict(filters or {})
        merged_filters.setdefault("chunking_version", self.chunking_version)
        logger.info(
            "stage=qdrant_sparse_query collection=%s top_k=%s using=%s",
            self.collection_name,
            top_k,
            self.vector_name,
        )
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=Document(
                text=query,
                model=self.bm25_model,
                options={"avg_len": self.bm25_avg_len},
            ),
            using=self.vector_name,
            query_filter=build_payload_filter(merged_filters),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        points = getattr(response, "points", response)
        logger.info("stage=qdrant_sparse_query_done hits=%s", len(points))
        return [
            point_to_retrieved_chunk(
                point,
                rank=rank,
                method=RetrievalMethod.BM25,
            )
            for rank, point in enumerate(points, start=1)
        ]

"""Dense Qdrant retrieval using the existing embedding provider contract."""

from collections.abc import Mapping

from qdrant_client import QdrantClient

from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingProvider,
    EmbeddingVector,
)
from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
)
from rag_based_on_obsidian.retrieval.progress import logger
from rag_based_on_obsidian.retrieval.qdrant_results import (
    DENSE_VECTOR_NAME,
    build_payload_filter,
    point_to_retrieved_chunk,
)


class QdrantDenseRetriever:
    """Search one versioned Qdrant collection and map payloads to chunks."""

    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        provider: EmbeddingProvider,
        vector_name: str = DENSE_VECTOR_NAME,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        self.client = client
        self.collection_name = collection_name
        self.provider = provider
        self.vector_name = vector_name

    def search(
        self,
        query: str,
        *,
        top_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Embed one query and execute dense search."""
        logger.info("stage=embed_query collection=%s", self.collection_name)
        vector = self.provider.embed_query(query)
        logger.info(
            "stage=embed_query_done dimension=%s",
            len(vector),
        )
        return self.search_vector(
            vector,
            top_k=top_k,
            filters=filters,
        )

    def search_vector(
        self,
        vector: EmbeddingVector,
        *,
        top_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Search with a precomputed query vector for hybrid fan-out."""
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        expected_dimension = self.provider.metadata.dimension
        if len(vector) != expected_dimension:
            raise ValueError(
                f"query vector dimension mismatch: expected "
                f"{expected_dimension}, got {len(vector)}"
            )
        logger.info(
            "stage=qdrant_query_points collection=%s top_k=%s using=%s",
            self.collection_name,
            top_k,
            self.vector_name,
        )
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=list(vector),
            using=self.vector_name,
            query_filter=build_payload_filter(filters),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        points = getattr(response, "points", response)
        logger.info("stage=qdrant_query_points_done hits=%s", len(points))
        return [
            point_to_retrieved_chunk(
                point,
                rank=rank,
                method=RetrievalMethod.DENSE,
            )
            for rank, point in enumerate(points, start=1)
        ]

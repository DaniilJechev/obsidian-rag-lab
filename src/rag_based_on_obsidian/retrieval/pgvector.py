"""Dense retrieval against the experimental pgvector table."""

import sys
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.engine import Engine
from tqdm import tqdm

from rag_based_on_obsidian.db.pgvector_schema import (
    DEFAULT_PGVECTOR_TABLE,
    chunk_embeddings_table,
)
from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingProvider,
    EmbeddingVector,
)
from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
)
from rag_based_on_obsidian.retrieval.progress import logger
from rag_based_on_obsidian.vector_store.pgvector_sink import (
    _register_vector_on_engine,
)

_FILTER_COLUMNS = {
    "source_path",
    "note_id",
    "chunk_id",
    "chunking_version",
}


class PgvectorDenseRetriever:
    """Search one index generation with SQL cosine distance."""

    def __init__(
        self,
        engine: Engine,
        *,
        index_generation: str,
        provider: EmbeddingProvider,
        table_name: str = DEFAULT_PGVECTOR_TABLE,
    ) -> None:
        if not index_generation.strip():
            raise ValueError("index_generation must not be empty")
        if not table_name.strip():
            raise ValueError("table_name must not be empty")
        self.engine = engine
        self.index_generation = index_generation
        self.provider = provider
        self.table_name = table_name
        self._table = chunk_embeddings_table(
            provider.metadata.dimension,
            table_name=table_name,
        )
        _register_vector_on_engine(engine)

    def search(
        self,
        query: str,
        *,
        top_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Embed one query and execute dense SQL search."""
        filter_keys = ",".join(sorted(filters or {})) or "none"
        stages = tqdm(
            total=2,
            desc="pgvector search",
            unit="stage",
            file=sys.stderr,
            disable=None,
        )
        try:
            logger.info(
                "stage=embed_query index_generation=%s table=%s filters=%s",
                self.index_generation,
                self.table_name,
                filter_keys,
            )
            vector = self.provider.embed_query(query)
            logger.info("stage=embed_query_done dimension=%s", len(vector))
            stages.set_postfix_str("embed_query")
            stages.update(1)
            results = self.search_vector(
                vector,
                top_k=top_k,
                filters=filters,
            )
            stages.set_postfix_str("sql_query")
            stages.update(1)
            return results
        finally:
            stages.close()

    def search_vector(
        self,
        vector: EmbeddingVector,
        *,
        top_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Search with a precomputed query vector."""
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        expected_dimension = self.provider.metadata.dimension
        if len(vector) != expected_dimension:
            raise ValueError(
                "query vector dimension mismatch: expected "
                f"{expected_dimension}, got {len(vector)}"
            )
        statement = _search_statement(
            self._table,
            vector=list(vector),
            index_generation=self.index_generation,
            top_k=top_k,
            filters=filters,
        )
        logger.info(
            "stage=pgvector_query index_generation=%s table=%s top_k=%s",
            self.index_generation,
            self.table_name,
            top_k,
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        logger.info("stage=pgvector_query_done hits=%s", len(rows))
        return [
            _row_to_retrieved_chunk(row, rank=rank)
            for rank, row in enumerate(rows, start=1)
        ]


def _search_statement(
    table: object,
    *,
    vector: list[float],
    index_generation: str,
    top_k: int,
    filters: Mapping[str, object] | None,
) -> object:
    distance = table.c.embedding.cosine_distance(vector)
    statement = select(
        table.c.chunk_id,
        table.c.text,
        table.c.chunking_version,
        table.c.point_key,
        table.c.note_id,
        table.c.chunk_index,
        table.c.section_title,
        table.c.section_level,
        table.c.section_path,
        table.c.source_path,
        table.c.start_offset,
        table.c.end_offset,
        distance.label("distance"),
    ).where(table.c.index_generation == index_generation)
    for key, value in (filters or {}).items():
        if key not in _FILTER_COLUMNS:
            raise TypeError(f"unsupported pgvector filter: {key}")
        if not isinstance(value, str | int | float | bool):
            raise TypeError("pgvector filters must contain scalar values")
        statement = statement.where(getattr(table.c, key) == value)
    return statement.order_by(distance).limit(top_k)


def _row_to_retrieved_chunk(row: Mapping[str, object], *, rank: int) -> RetrievedChunk:
    distance = row["distance"]
    if not isinstance(distance, int | float):
        raise TypeError("pgvector distance must be numeric")
    similarity = 1.0 - float(distance)
    raw_chunk_id = row["chunk_id"]
    text = row["text"]
    chunking_version = row["chunking_version"]
    point_key = row["point_key"]
    if not isinstance(raw_chunk_id, int) or isinstance(raw_chunk_id, bool):
        raise TypeError("pgvector chunk_id must be an integer")
    if not isinstance(text, str):
        raise TypeError("pgvector text must be a string")
    if not isinstance(chunking_version, str):
        raise TypeError("pgvector chunking_version must be a string")
    if not isinstance(point_key, str):
        raise TypeError("pgvector point_key must be a string")
    metadata = {
        "point_key": point_key,
        "chunk_id": raw_chunk_id,
        "note_id": row.get("note_id"),
        "chunk_index": row.get("chunk_index"),
        "chunking_version": chunking_version,
        "text": text,
        "section_title": row.get("section_title"),
        "section_level": row.get("section_level"),
        "section_path": row.get("section_path"),
        "source_path": row.get("source_path"),
        "start_offset": row.get("start_offset"),
        "end_offset": row.get("end_offset"),
    }
    return RetrievedChunk(
        chunk_id=raw_chunk_id,
        text=text,
        score=similarity,
        retrieval_method=RetrievalMethod.PGVECTOR,
        metadata=metadata,
        chunking_version=chunking_version,
        rank=rank,
        point_key=point_key,
        dense_score=similarity,
    )

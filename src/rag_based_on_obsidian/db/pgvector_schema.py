"""SQLAlchemy table for the experimental pgvector dense store."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    SmallInteger,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

DEFAULT_PGVECTOR_TABLE = "chunk_embeddings_pgvector"


def chunk_embeddings_table(
    vector_size: int,
    *,
    table_name: str = DEFAULT_PGVECTOR_TABLE,
    metadata: MetaData | None = None,
) -> Table:
    """Return the versioned dense-embedding table for one vector dimension."""
    if vector_size <= 0:
        raise ValueError("vector_size must be positive")
    if not table_name.strip():
        raise ValueError("table_name must not be empty")
    return Table(
        table_name,
        metadata if metadata is not None else MetaData(),
        Column("index_generation", Text, nullable=False),
        Column("point_key", Text, nullable=False),
        Column("chunk_id", BigInteger, nullable=False),
        Column("note_id", BigInteger, nullable=False),
        Column("chunk_index", Integer, nullable=False),
        Column("chunking_version", Text, nullable=False),
        Column("text", Text, nullable=False),
        Column("section_title", Text, nullable=True),
        Column("section_level", SmallInteger, nullable=True),
        Column("section_path", JSONB, nullable=False, server_default="[]"),
        Column("source_path", Text, nullable=True),
        Column("start_offset", Integer, nullable=True),
        Column("end_offset", Integer, nullable=True),
        Column("vector_dimension", Integer, nullable=False),
        Column("embedding", Vector(vector_size), nullable=False),
        PrimaryKeyConstraint(
            "index_generation",
            "point_key",
            name=f"pk_{table_name}_generation_point",
        ),
    )

"""Validated YAML-backed chunking policy contract."""

from pydantic import BaseModel, Field, model_validator


class ChunkingPolicy(BaseModel):
    """Configuration contract shared by future structural chunkers."""

    name: str = Field(min_length=1)
    chunk_size: int = Field(gt=0)
    chunk_overlap: int = Field(ge=0)
    separators: list[str] = Field(min_length=1)
    include_heading_context: bool = True
    preserve_code_blocks: bool = True
    preserve_list_blocks: bool = True
    preserve_table_blocks: bool = True

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingPolicy":
        """Prevent overlap from consuming the whole chunk budget."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if any(not separator for separator in self.separators):
            raise ValueError("separators must not contain empty strings")
        return self

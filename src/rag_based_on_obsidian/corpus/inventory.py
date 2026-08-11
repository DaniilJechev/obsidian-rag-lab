"""Build corpus inventory from the existing discovery and parser layers."""

from datetime import UTC, datetime

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.inventory_entities import (
    CorpusInventory,
    InventorySummary,
    TokenizerMetadata,
)
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file
from rag_based_on_obsidian.corpus.statistics import calculate_document_statistics
from rag_based_on_obsidian.corpus.word_tokenizer import (
    WORD_TOKENIZER_NAME,
    WORD_TOKENIZER_VERSION,
)


def build_corpus_inventory(
    discovered_files: tuple[DiscoveredFile, ...] | list[DiscoveredFile],
    allowed_directories: tuple[str, ...] = ("DLS1", "DLS2"),
    generated_at: str | None = None,
) -> CorpusInventory:
    """Parse discovered files and aggregate their inventory statistics."""

    document_statistics = []
    failed_documents = 0

    for discovered_file in sorted(
        discovered_files,
        key=lambda item: item.relative_path.as_posix(),
    ):
        try:
            parsed_document = parse_markdown_file(discovered_file)
        except (OSError, TypeError, ValueError):
            failed_documents += 1
            continue
        document_statistics.append(
            calculate_document_statistics(parsed_document)
        )

    file_sizes = [
        statistics.file_size_bytes for statistics in document_statistics
    ]
    documents_with_anomalies = sum(
        bool(statistics.anomalies) for statistics in document_statistics
    )
    documents_total = len(discovered_files)
    summary = InventorySummary(
        documents_total=documents_total,
        documents_parsed=len(document_statistics),
        documents_failed=failed_documents,
        mean_file_size_bytes=_mean_or_zero(file_sizes),
        median_file_size_bytes=_median_or_zero(file_sizes),
        documents_with_anomalies=documents_with_anomalies,
        anomaly_rate=_ratio(documents_with_anomalies, documents_total),
    )
    tokenizer = TokenizerMetadata(
        name=WORD_TOKENIZER_NAME,
        tokenizer_type="word",
        library_name="project-defined",
        library_version=WORD_TOKENIZER_VERSION,
    )
    return CorpusInventory(
        schema_version="1.0",
        generated_at=generated_at or datetime.now(UTC).isoformat(),
        allowed_directories=allowed_directories,
        tokenizer_baselines=(tokenizer,),
        summary=summary,
        documents=tuple(document_statistics),
    )


def _mean_or_zero(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median_or_zero(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0

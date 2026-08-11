"""Build corpus inventory from the existing discovery and parser layers."""

from collections.abc import Iterable
from datetime import UTC, datetime

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.inventory_entities import (
    CorpusInventory,
    DocumentStatistics,
    DuplicateGroup,
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
    show_progress: bool = True,
) -> CorpusInventory:
    """Parse files and aggregate statistics, optionally showing progress."""

    document_statistics = []
    ordered_files = sorted(
        discovered_files,
        key=lambda item: item.relative_path.as_posix(),
    )

    for discovered_file in _progress_iterator(ordered_files, show_progress):
        try:
            parsed_document = parse_markdown_file(discovered_file)
        except (OSError, TypeError, ValueError) as error:
            document_statistics.append(
                DocumentStatistics(
                    source=discovered_file,
                    analysis_text="",
                    file_size_bytes=_safe_file_size(discovered_file),
                    character_count=0,
                    word_count=0,
                    parse_status="failed",
                    anomalies=(_anomaly_for_error(error),),
                    error_type=type(error).__name__,
                )
            )
            continue
        document_statistics.append(
            calculate_document_statistics(parsed_document)
        )

    parsed_statistics = [
        statistics
        for statistics in document_statistics
        if statistics.parse_status == "ok"
    ]
    file_sizes = [
        statistics.file_size_bytes for statistics in parsed_statistics
    ]
    documents_with_anomalies = sum(
        bool(statistics.anomalies) for statistics in document_statistics
    )
    duplicate_groups = _duplicate_groups(parsed_statistics)
    documents_total = len(document_statistics)
    summary = InventorySummary(
        documents_total=documents_total,
        documents_parsed=len(parsed_statistics),
        documents_failed=documents_total - len(parsed_statistics),
        mean_file_size_bytes=_mean_or_zero(file_sizes),
        median_file_size_bytes=_median_or_zero(file_sizes),
        documents_with_anomalies=documents_with_anomalies,
        anomaly_rate=_ratio(documents_with_anomalies, documents_total),
        duplicate_groups=len(duplicate_groups),
        duplicate_documents=sum(
            len(group.relative_paths) for group in duplicate_groups
        ),
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
        duplicate_groups=tuple(duplicate_groups),
    )


def _progress_iterator(
    discovered_files: list[DiscoveredFile],
    show_progress: bool,
) -> Iterable[DiscoveredFile]:
    """Wrap files with tqdm when requested, preserving a dependency fallback."""

    if not show_progress:
        return discovered_files
    try:
        from tqdm import tqdm
    except ImportError:
        return discovered_files
    return tqdm(
        discovered_files,
        desc="Building corpus inventory",
        unit="file",
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


def _safe_file_size(discovered_file: DiscoveredFile) -> int:
    try:
        return discovered_file.absolute_path.stat().st_size
    except OSError:
        return 0


def _anomaly_for_error(error: Exception) -> str:
    if isinstance(error, (TypeError, ValueError)):
        return "malformed_frontmatter"
    return "read_error"


def _duplicate_groups(
    documents: list[DocumentStatistics],
) -> list[DuplicateGroup]:
    by_hash: dict[str, list[str]] = {}
    for document in documents:
        if document.content_hash is None:
            continue
        by_hash.setdefault(document.content_hash, []).append(
            document.source.relative_path.as_posix()
        )
    return [
        DuplicateGroup(content_hash=content_hash, relative_paths=tuple(paths))
        for content_hash, paths in sorted(by_hash.items())
        if len(paths) > 1
    ]

"""Immutable contracts for corpus inventory and exploratory statistics."""

from dataclasses import dataclass

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile


@dataclass(frozen=True)
class TokenizerMetadata:
    """Describe one tokenizer baseline used for inventory statistics."""

    name: str
    tokenizer_type: str
    library_name: str
    library_version: str
    model_name: str | None = None
    model_version: str | None = None
    parameters: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class TokenCount:
    """Token count produced by one named tokenizer baseline."""

    tokenizer_name: str
    count: float


@dataclass(frozen=True)
class HeadingStatistics:
    """Length statistics for one heading level and section projection."""

    level: int | None
    view: str
    section_count: int
    mean_word_count: float
    median_word_count: float
    mean_token_counts: tuple[TokenCount, ...] = ()
    median_token_counts: tuple[TokenCount, ...] = ()


@dataclass(frozen=True)
class LanguageStatistics:
    """Language classification counts for one document or corpus."""

    russian_word_count: int
    english_word_count: int
    mixed_or_other_word_count: int
    unknown_word_count: int

    @property
    def classified_word_count(self) -> int:
        """Return words assigned to Russian, English, or mixed/other."""

        return (
            self.russian_word_count
            + self.english_word_count
            + self.mixed_or_other_word_count
        )

    @property
    def russian_ratio(self) -> float:
        """Return the Russian share among classified words."""

        return _safe_ratio(self.russian_word_count, self.classified_word_count)

    @property
    def english_ratio(self) -> float:
        """Return the English share among classified words."""

        return _safe_ratio(self.english_word_count, self.classified_word_count)

    @property
    def russian_to_english_ratio(self) -> float | None:
        """Return RU/EN ratio, or ``None`` when no English words exist."""

        if self.english_word_count == 0:
            return None
        return self.russian_word_count / self.english_word_count


@dataclass(frozen=True)
class DocumentStatistics:
    """Inventory statistics for one discovered Markdown document."""

    source: DiscoveredFile
    analysis_text: str
    file_size_bytes: int
    character_count: int
    word_count: int
    token_counts: tuple[TokenCount, ...] = ()
    heading_statistics: tuple[HeadingStatistics, ...] = ()
    language_statistics: LanguageStatistics = LanguageStatistics(0, 0, 0, 0)
    parse_status: str = "ok"
    anomalies: tuple[str, ...] = ()
    content_hash: str | None = None
    error_type: str | None = None


@dataclass(frozen=True)
class DuplicateGroup:
    """Documents that have byte-identical UTF-8 source content."""

    content_hash: str
    relative_paths: tuple[str, ...]


@dataclass(frozen=True)
class InventorySummary:
    """Aggregate counts and file-size statistics for a corpus."""

    documents_total: int
    documents_parsed: int
    documents_failed: int
    mean_file_size_bytes: float
    median_file_size_bytes: float
    documents_with_anomalies: int
    anomaly_rate: float
    duplicate_groups: int = 0
    duplicate_documents: int = 0


@dataclass(frozen=True)
class CorpusInventory:
    """Top-level inventory contract before JSON serialization."""

    schema_version: str
    generated_at: str
    allowed_directories: tuple[str, ...]
    tokenizer_baselines: tuple[TokenizerMetadata, ...]
    summary: InventorySummary
    documents: tuple[DocumentStatistics, ...] = ()
    duplicate_groups: tuple[DuplicateGroup, ...] = ()


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return a ratio without exposing division-by-zero to callers."""

    if denominator == 0:
        return 0.0
    return numerator / denominator

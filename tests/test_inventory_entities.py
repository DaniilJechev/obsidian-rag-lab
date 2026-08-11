from pathlib import Path, PurePosixPath

import pytest

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.inventory_entities import (
    CorpusInventory,
    DocumentStatistics,
    HeadingStatistics,
    InventorySummary,
    LanguageStatistics,
    TokenCount,
    TokenizerMetadata,
)
from rag_based_on_obsidian.corpus.word_tokenizer import tokenize_words


@pytest.fixture
def discovered_file() -> DiscoveredFile:
    return DiscoveredFile(
        absolute_path=Path("C:/vault/DLS2/Encoder.md"),
        relative_path=PurePosixPath("DLS2/Encoder.md"),
    )


def test_language_statistics_calculate_ratios() -> None:
    statistics = LanguageStatistics(
        russian_word_count=3,
        english_word_count=1,
        mixed_or_other_word_count=1,
        unknown_word_count=2,
    )

    assert statistics.classified_word_count == 5
    assert statistics.russian_ratio == pytest.approx(0.6)
    assert statistics.english_ratio == pytest.approx(0.2)
    assert statistics.russian_to_english_ratio == pytest.approx(3.0)


def test_language_statistics_handle_zero_english_words() -> None:
    statistics = LanguageStatistics(2, 0, 0, 0)

    assert statistics.russian_ratio == 1.0
    assert statistics.english_ratio == 0.0
    assert statistics.russian_to_english_ratio is None


def test_word_tokenizer_keeps_hyphenated_terms_and_ignores_delimiters() -> None:
    text = "BERT-модель uses n_layers=12. [[Encoder]] 42 https://example.com"

    assert tokenize_words(text) == (
        "BERT-модель",
        "uses",
        "Encoder",
    )


def test_inventory_contract_composes_immutable_entities(
    discovered_file: DiscoveredFile,
) -> None:
    tokenizer = TokenizerMetadata(
        name="regex_word_tokenizer",
        tokenizer_type="word",
        library_name="project-defined",
        library_version="1",
    )
    heading = HeadingStatistics(
        level=2,
        view="direct_body",
        section_count=1,
        mean_word_count=12.0,
        median_word_count=12.0,
        mean_token_counts=(TokenCount("regex_word_tokenizer", 12),),
        median_token_counts=(TokenCount("regex_word_tokenizer", 12),),
    )
    document = DocumentStatistics(
        source=discovered_file,
        analysis_text="BERT-модель uses attention.",
        file_size_bytes=256,
        character_count=240,
        word_count=12,
        token_counts=(TokenCount("regex_word_tokenizer", 12),),
        heading_statistics=(heading,),
        language_statistics=LanguageStatistics(8, 3, 1, 0),
        content_hash="abc123",
    )
    summary = InventorySummary(
        documents_total=1,
        documents_parsed=1,
        documents_failed=0,
        mean_file_size_bytes=256.0,
        median_file_size_bytes=256.0,
        documents_with_anomalies=0,
        anomaly_rate=0.0,
    )
    inventory = CorpusInventory(
        schema_version="1.0",
        generated_at="2026-08-11T00:00:00Z",
        allowed_directories=("DLS1", "DLS2"),
        tokenizer_baselines=(tokenizer,),
        summary=summary,
        documents=(document,),
    )

    assert inventory.documents[0].source.relative_path == PurePosixPath(
        "DLS2/Encoder.md"
    )
    assert inventory.documents[0].heading_statistics[0].level == 2
    assert inventory.tokenizer_baselines[0].name == "regex_word_tokenizer"
    with pytest.raises(AttributeError):
        inventory.schema_version = "2.0"

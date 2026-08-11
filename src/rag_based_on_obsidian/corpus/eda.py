"""Create chunking-oriented visual EDA from a corpus inventory artifact."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

LEVEL_NAMES = {None: "pre-heading", **{level: f"H{level}" for level in range(1, 7)}}


def load_inventory(path: Path) -> dict[str, Any]:
    """Load a previously generated inventory artifact."""

    return json.loads(path.read_text(encoding="utf-8"))


def _ok_documents(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        document
        for document in inventory.get("documents", [])
        if document.get("parse_status") == "ok"
    ]


def _values(documents: Iterable[dict[str, Any]], field: str) -> list[float]:
    return [float(document[field]) for document in documents if field in document]


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _number(value: float) -> str:
    return f"{value:.2f}" if value % 1 else str(int(value))


def _stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0,
            "median": 0,
            "std": 0,
            "p25": 0,
            "p75": 0,
            "p90": 0,
            "p95": 0,
        }
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": mean(values),
        "median": median(values),
        "std": stdev(values) if len(values) > 1 else 0.0,
        "p25": _percentile(values, 25),
        "p75": _percentile(values, 75),
        "p90": _percentile(values, 90),
        "p95": _percentile(values, 95),
    }


def _language_counts(documents: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for document in documents:
        language = document.get("language_statistics", {})
        counts["Russian"] += language.get("russian_word_count", 0)
        counts["English"] += language.get("english_word_count", 0)
        counts["Mixed/other"] += language.get("mixed_or_other_word_count", 0)
        counts["Unknown"] += language.get("unknown_word_count", 0)
    return dict(counts)


def _duplicate_groups(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    return inventory.get("duplicate_groups", [])


def _progress_iterator(items: list[str], show_progress: bool) -> Iterable[str]:
    if not show_progress:
        return items
    try:
        from tqdm import tqdm
    except ImportError:
        return items
    return tqdm(items, desc="Creating EDA figures", unit="figure")


def _clear_output_directory(output_directory: Path) -> None:
    """Remove all generated contents before creating a fresh EDA run."""

    if not output_directory.exists():
        return
    for item in output_directory.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()


def _level_key(level: Any) -> int | None:
    return None if level is None else int(level)


def _paragraph_groups(
    documents: Iterable[dict[str, Any]],
) -> dict[int | None, list[dict[str, Any]]]:
    groups: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        for block in document.get("paragraph_blocks", []):
            groups[_level_key(block.get("level"))].append(block)
    return groups


def _paragraph_metrics(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    if not blocks:
        return {}
    metrics: dict[str, Any] = {"count": len(blocks)}
    for field in ("word_count", "token_count", "character_count", "byte_count"):
        metrics[field] = _stats([float(block.get(field, 0)) for block in blocks])
    empty_count = sum(block.get("word_count", 0) == 0 for block in blocks)
    metrics["empty_count"] = empty_count
    metrics["empty_rate"] = empty_count / len(blocks)
    word_total = sum(block.get("word_count", 0) for block in blocks)
    token_total = sum(block.get("token_count", 0) for block in blocks)
    metrics["token_word_ratio"] = token_total / word_total if word_total else 0.0
    for language in (
        "russian_word_count",
        "english_word_count",
        "mixed_or_other_word_count",
        "unknown_word_count",
    ):
        metrics[language] = sum(block.get(language, 0) for block in blocks)
    classified = sum(
        metrics[name]
        for name in (
            "russian_word_count",
            "english_word_count",
            "mixed_or_other_word_count",
        )
    )
    metrics["russian_ratio"] = (
        metrics["russian_word_count"] / classified if classified else 0.0
    )
    metrics["english_ratio"] = (
        metrics["english_word_count"] / classified if classified else 0.0
    )
    for field in (
        "wikilink_count",
        "image_embed_count",
        "code_block_count",
        "list_item_count",
        "blockquote_line_count",
    ):
        metrics[field] = sum(block.get(field, 0) for block in blocks)
    metrics["word_threshold_rates"] = {
        str(threshold): sum(
            block.get("word_count", 0) > threshold for block in blocks
        )
        / len(blocks)
        for threshold in (256, 512, 1024)
    }
    return metrics


def _paragraph_rows(inventory: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    groups = _paragraph_groups(_ok_documents(inventory))
    rows: list[tuple[str, dict[str, Any]]] = []
    for level in (None, 1, 2, 3, 4, 5, 6):
        if groups.get(level):
            rows.append((LEVEL_NAMES[level], _paragraph_metrics(groups[level])))
    all_blocks = [block for blocks in groups.values() for block in blocks]
    if all_blocks:
        rows.append(("all_levels", _paragraph_metrics(all_blocks)))
    return rows


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["Нет данных."]
    separator = ["---"] * len(headers)
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
        *["| " + " | ".join(row) + " |" for row in rows],
    ]


def _render_duplicate_lines(groups: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for index, group in enumerate(groups, start=1):
        lines.append(f"Group {index} — hash {group['content_hash'][:12]}...")
        lines.extend(f"  - {path}" for path in group["relative_paths"])
    return lines or ["No duplicate groups"]


def _section_rows(documents: Iterable[dict[str, Any]]) -> list[list[str]]:
    grouped: dict[tuple[Any, str], list[float]] = defaultdict(list)
    for document in documents:
        for item in document.get("heading_statistics", []):
            key = (_level_key(item.get("level")), item["view"])
            grouped[key].extend(
                [item.get("mean_word_count", 0), item.get("median_word_count", 0)]
            )
    rows = []
    for (level, view), values in sorted(
        grouped.items(), key=lambda item: (item[0][0] is not None, item[0][0] or 0, item[0][1])
    ):
        rows.append(
            [
                LEVEL_NAMES[level],
                view,
                _number(len(values) / 2),
                _number(values[0]),
                _number(values[1]),
            ]
        )
    return rows


def _distribution_rows(values: list[float], unit: str) -> list[list[str]]:
    """Render the numeric source table for a distribution figure."""

    metrics = _stats(values)
    return [
        [name, _number(float(metrics[name])), unit]
        for name in (
            "count",
            "min",
            "mean",
            "median",
            "p25",
            "p75",
            "p90",
            "p95",
            "max",
            "std",
        )
    ]


def _directory_rows(documents: Iterable[dict[str, Any]]) -> list[list[str]]:
    """Aggregate file-size and word-count metrics by top-level directory."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        relative_path = document.get("source", {}).get("relative_path", "")
        directory = relative_path.split("/", maxsplit=1)[0] or "unknown"
        grouped[directory].append(document)
    rows = []
    for directory, directory_documents in sorted(grouped.items()):
        sizes = _values(directory_documents, "file_size_bytes")
        words = _values(directory_documents, "word_count")
        rows.append(
            [
                directory,
                str(len(directory_documents)),
                _number(_stats(sizes)["median"]),
                _number(_stats(sizes)["p95"]),
                _number(_stats(words)["median"]),
                _number(_stats(words)["p95"]),
            ]
        )
    return rows


def _figure_text(
    figure_path: Path,
    documents: list[dict[str, Any]],
) -> list[str]:
    """Return a description and numeric table for one figure."""

    name = figure_path.stem
    image = f"![{name.replace('_', ' ').title()}]({figure_path.name})"
    if name == "document_file_size_distribution":
        return [
            "### Document file-size distribution",
            "",
            (
                "Гистограмма распределения размеров Markdown-файлов. Таблица содержит "
                "точные значения для median и percentile markers."
            ),
            "",
            image,
            "",
            *_table(
                ["Statistic", "Value", "Unit"],
                _distribution_rows(_values(documents, "file_size_bytes"), "bytes"),
            ),
        ]
    if name == "document_word_count_distribution":
        return [
            "### Document word-count distribution",
            "",
            (
                "Распределение количества слов в документах. P90/P95 показывают "
                "длинный хвост для document-level splitting."
            ),
            "",
            image,
            "",
            *_table(
                ["Statistic", "Value", "Unit"],
                _distribution_rows(_values(documents, "word_count"), "words"),
            ),
        ]
    if name == "document_size_vs_word_count":
        rows = [
            [
                document.get("source", {}).get("relative_path", ""),
                _number(float(document.get("file_size_bytes", 0))),
                _number(float(document.get("word_count", 0))),
            ]
            for document in documents
        ]
        return [
            "### Document size versus word count",
            "",
            (
                "Связь физического размера файла и количества слов. Таблица "
                "позволяет анализировать каждую точку без чтения PNG."
            ),
            "",
            image,
            "",
            *_table(["Document", "Bytes", "Words"], rows),
        ]
    if name == "document_heading_section_length_by_level":
        return [
            "### Heading section length by level",
            "",
            (
                "Средняя длина heading sections по уровням и projections "
                "`direct_body`/`full_span`."
            ),
            "",
            image,
            "",
            *_table(
                ["Level", "View", "Sections", "Mean words", "Median words"],
                _section_rows(documents),
            ),
        ]
    if name == "paragraph_length_distribution":
        blocks = [
            block
            for block_group in _paragraph_groups(documents).values()
            for block in block_group
        ]
        values = [float(block.get("word_count", 0)) for block in blocks]
        return [
            "### Paragraph length distribution",
            "",
            "Распределение количества слов в paragraph blocks по всему корпусу.",
            "",
            image,
            "",
            *_table(
                ["Statistic", "Value", "Unit"],
                _distribution_rows(values, "words"),
            ),
        ]
    if name == "paragraph_length_by_heading_level":
        rows = []
        for level, metrics in _paragraph_rows({"documents": documents}):
            words = metrics["word_count"]
            rows.append(
                [
                    level,
                    str(metrics["count"]),
                    _number(words["median"]),
                    _number(words["mean"]),
                    _number(words["p90"]),
                    _number(words["p95"]),
                ]
            )
        return [
            "### Paragraph length by heading level",
            "",
            "Boxplot сравнивает paragraph blocks внутри присутствующих уровней.",
            "",
            image,
            "",
            *_table(
                ["Level", "Blocks", "Median words", "Mean words", "P90", "P95"],
                rows,
            ),
        ]
    if name == "directory_comparison_file_size":
        return [
            "### File-size comparison by directory",
            "",
            (
                "Сравнение размеров документов в верхнеуровневых каталогах, "
                "например DLS1 и DLS2."
            ),
            "",
            image,
            "",
            *_table(
                [
                    "Directory",
                    "Documents",
                    "Median bytes",
                    "P95 bytes",
                    "Median words",
                    "P95 words",
                ],
                _directory_rows(documents),
            ),
        ]
    return [image]


def write_eda_markdown(
    inventory: dict[str, Any],
    figure_paths: list[Path],
    markdown_path: Path,
) -> None:
    """Write a thematic Markdown report with images and numeric tables."""

    summary = inventory.get("summary", {})
    documents = _ok_documents(inventory)
    languages = _language_counts(documents)
    anomalies = Counter(
        anomaly
        for document in inventory.get("documents", [])
        for anomaly in document.get("anomalies", [])
    )
    lines = [
        "# Obsidian RAG Corpus EDA",
        "",
        "## Corpus overview",
        "",
        f"- Documents: {summary.get('documents_total', 0)}",
        f"- Parsed: {summary.get('documents_parsed', 0)}",
        f"- Failed: {summary.get('documents_failed', 0)}",
        f"- Mean file size: {_number(summary.get('mean_file_size_bytes', 0))} bytes",
        f"- Median file size: {_number(summary.get('median_file_size_bytes', 0))} bytes",
        f"- Duplicate groups: {summary.get('duplicate_groups', 0)}",
        f"- Duplicate documents: {summary.get('duplicate_documents', 0)}",
        "",
        "## Document distributions",
        "",
    ]
    for figure_path in figure_paths:
        lines.extend(_figure_text(figure_path, documents))
        lines.append("")
    lines.extend(["## Language composition", ""])
    language_total = sum(languages.values())
    language_rows = [
        [name, str(count), f"{count / language_total:.2%}" if language_total else "0.00%"]
        for name, count in languages.items()
        if count or name in ("Russian", "English")
    ]
    lines.extend(_table(["Language", "Words", "Share"], language_rows))
    lines.extend(["", "## Heading and paragraph analysis", ""])
    lines.extend(
        _table(
            ["Level", "View", "Sections", "Mean words", "Median words"],
            _section_rows(documents),
        )
    )
    lines.extend(["", "### Paragraph blocks", ""])
    paragraph_rows = []
    for level, metrics in _paragraph_rows(inventory):
        words = metrics["word_count"]
        tokens = metrics["token_count"]
        paragraph_rows.append(
            [
                level,
                str(metrics["count"]),
                str(metrics["empty_count"]),
                f"{metrics['empty_rate']:.2%}",
                _number(words["median"]),
                _number(words["mean"]),
                _number(words["p90"]),
                _number(words["p95"]),
                _number(tokens["median"]),
                f"{metrics['token_word_ratio']:.2f}",
                str(metrics["wikilink_count"]),
                str(metrics["image_embed_count"]),
                str(metrics["code_block_count"]),
                str(metrics["list_item_count"]),
                str(metrics["blockquote_line_count"]),
            ]
        )
    lines.extend(
        _table(
            [
                "Level", "Count", "Empty", "Empty rate", "Median words",
                "Mean words", "P90 words", "P95 words", "Median tokens",
                "Token/word", "Wikilinks", "Images", "Code", "List items", "Quotes",
            ],
            paragraph_rows,
        )
    )
    lines.extend(["", "## Duplicates", "", *_render_duplicate_lines(_duplicate_groups(inventory))])
    lines.extend(["", "## Anomalies", ""])
    anomaly_rows = [
        [name, str(count), f"{count / len(inventory.get('documents', [])):.2%}"]
        for name, count in sorted(anomalies.items())
    ]
    lines.extend(_table(["Anomaly", "Count", "Share"], anomaly_rows))
    lines.extend(
        [
            "",
            "## Chunking implications",
            "",
            "- Использовать heading-aware boundaries, но не считать всю секцию одним chunk.",
            "- Проверять p90/p95 paragraph length перед выбором recursive splitting.",
            "- Короткие соседние paragraphs можно объединять с сохранением heading metadata.",
            "- Code-, link- и image-heavy blocks требуют отдельной политики chunking.",
            "",
        ]
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def create_eda_figures(
    inventory: dict[str, Any],
    output_directory: Path,
    *,
    show_progress: bool = True,
) -> list[Path]:
    """Create informative, semantically named PNG figures."""

    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError as error:
        raise RuntimeError(
            "EDA graphics require matplotlib and seaborn. "
            "Install them manually with: uv add --dev matplotlib seaborn"
        ) from error
    sns.set_theme(style="whitegrid", context="notebook")
    output_directory.mkdir(parents=True, exist_ok=True)
    _clear_output_directory(output_directory)
    documents = _ok_documents(inventory)
    file_sizes = _values(documents, "file_size_bytes")
    word_counts = _values(documents, "word_count")
    paragraph_groups = _paragraph_groups(documents)
    chart_names = ["document_file_size_distribution", "document_word_count_distribution"]
    if file_sizes and word_counts:
        chart_names.append("document_size_vs_word_count")
    if any(paragraph_groups.values()):
        chart_names.extend(
            ["document_heading_section_length_by_level", "paragraph_length_distribution",
             "paragraph_length_by_heading_level"]
        )
    if len({document.get("source", {}).get("relative_path", "").split("/")[0] for document in documents}) > 1:
        chart_names.append("directory_comparison_file_size")
    paths: list[Path] = []
    for chart_name in _progress_iterator(chart_names, show_progress):
        figure, axis = plt.subplots(figsize=(10, 6), constrained_layout=True)
        if chart_name == "document_file_size_distribution":
            if file_sizes:
                sns.histplot(
                    file_sizes,
                    kde=True,
                    ax=axis,
                    color="#2563eb",
                    label="Documents",
                )
                axis.axvline(median(file_sizes), color="#dc2626", label="Median")
            else:
                axis.text(0.5, 0.5, "Нет данных", ha="center", va="center")
            axis.set(title="Document file-size distribution", xlabel="Bytes", ylabel="Documents")
            if file_sizes:
                axis.legend()
        elif chart_name == "document_word_count_distribution":
            if word_counts:
                sns.histplot(
                    word_counts,
                    kde=True,
                    ax=axis,
                    color="#059669",
                    label="Documents",
                )
                axis.axvline(median(word_counts), color="#dc2626", label="Median")
                axis.axvline(
                    _percentile(word_counts, 95),
                    color="#7c3aed",
                    label="P95",
                )
            else:
                axis.text(0.5, 0.5, "Нет данных", ha="center", va="center")
            axis.set(title="Document word-count distribution", xlabel="Words", ylabel="Documents")
            if word_counts:
                axis.legend()
        elif chart_name == "document_size_vs_word_count":
            sns.scatterplot(x=file_sizes, y=word_counts, ax=axis, color="#0891b2", label="Document")
            axis.set(title="Document size versus word count", xlabel="Bytes", ylabel="Words")
            axis.legend()
        elif chart_name == "document_heading_section_length_by_level":
            rows = _section_rows(documents)
            axis.bar([f"{row[0]} {row[1]}" for row in rows], [float(row[3]) for row in rows], label="Mean words")
            axis.set(title="Heading section length by level and view", ylabel="Mean words")
            axis.tick_params(axis="x", rotation=45)
            axis.legend()
        elif chart_name == "paragraph_length_distribution":
            values = [block.get("word_count", 0) for blocks in paragraph_groups.values() for block in blocks]
            sns.histplot(values, kde=True, ax=axis, color="#f59e0b", label="Paragraphs")
            axis.axvline(median(values), color="#dc2626", label="Median")
            axis.set(title="Paragraph word-count distribution", xlabel="Words", ylabel="Paragraphs")
            axis.legend()
        elif chart_name == "paragraph_length_by_heading_level":
            labels, values = [], []
            for level in (None, 1, 2, 3, 4, 5, 6):
                if paragraph_groups.get(level):
                    labels.append(LEVEL_NAMES[level])
                    values.append([block.get("word_count", 0) for block in paragraph_groups[level]])
            axis.boxplot(values, tick_labels=labels, showfliers=False)
            axis.set(title="Paragraph lengths by heading level", xlabel="Heading level", ylabel="Words")
        else:
            directories: dict[str, list[float]] = defaultdict(list)
            for document in documents:
                path = document.get("source", {}).get("relative_path", "")
                directories[path.split("/")[0]].append(float(document.get("file_size_bytes", 0)))
            axis.boxplot(
                list(directories.values()),
                tick_labels=list(directories),
                showfliers=False,
            )
            axis.set(title="File-size comparison by directory", xlabel="Directory", ylabel="Bytes")
        path = output_directory / f"{chart_name}.png"
        figure.savefig(path, dpi=180, bbox_inches="tight")
        plt.close(figure)
        paths.append(path)
    return paths


def print_duplicate_groups(inventory: dict[str, Any]) -> None:
    """Print duplicate groups and their relative paths."""

    print("=== Duplicate files ===")
    print("\n".join(_render_duplicate_lines(_duplicate_groups(inventory))))


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("artifacts/corpus_inventory.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/eda"))
    parser.add_argument("--report", type=Path, default=Path("artifacts/eda/corpus_eda.md"))
    return parser


def main() -> None:
    arguments = build_argument_parser().parse_args()
    inventory = load_inventory(arguments.input)
    figures = create_eda_figures(inventory, arguments.output)
    write_eda_markdown(inventory, figures, arguments.report)
    print_duplicate_groups(inventory)
    print(f"EDA figures directory: {arguments.output}")
    print(f"EDA report: {arguments.report}")


if __name__ == "__main__":
    main()

from rag_based_on_obsidian.eval.context_proxy import (
    context_precision,
    context_recall,
    unique_note_paths,
)


def test_unique_note_paths_keeps_first_occurrence() -> None:
    assert unique_note_paths(
        ["DLS1/A.md", "DLS1/B.md", "DLS1/A.md", " DLS1/C.md "]
    ) == ("DLS1/A.md", "DLS1/B.md", "DLS1/C.md")


def test_context_precision_is_average_precision_of_gold_notes() -> None:
    packed = ["DLS1/A.md", "DLS1/noise.md", "DLS1/B.md"]
    gold = ["DLS1/A.md", "DLS1/B.md"]
    # hit@1=1/1, miss, hit@3=2/3 → mean(1.0, 2/3)
    assert context_precision(packed, gold) == (1.0 + 2 / 3) / 2


def test_context_precision_zero_when_no_gold_in_packed() -> None:
    assert context_precision(["DLS1/other.md"], ["DLS1/A.md"]) == 0.0


def test_context_recall_is_fraction_of_gold_notes_found() -> None:
    packed = ["DLS1/A.md", "DLS1/A.md", "DLS1/noise.md"]
    gold = ["DLS1/A.md", "DLS1/B.md", "DLS1/C.md"]
    assert context_recall(packed, gold) == 1 / 3

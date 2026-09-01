"""Score gold items against an explicit ranked-note list."""

from collections.abc import Mapping, Sequence

from rag_based_on_obsidian.eval.contracts import GoldItem, QuestionMetrics
from rag_based_on_obsidian.eval.metrics import score_question


def score_path_rankings(
    items: Sequence[GoldItem],
    rankings: Mapping[str, Sequence[str]],
    *,
    k: int,
) -> list[QuestionMetrics]:
    """Score each gold item using ranked relative_path values."""
    results: list[QuestionMetrics] = []
    for item in items:
        predicted = tuple(rankings.get(item.item_id, ()))
        results.append(
            score_question(
                item_id=item.item_id,
                predicted=predicted,
                relevant=item.relevant_note_paths,
                k=k,
            )
        )
    return results

from pathlib import Path

import yaml

from rag_based_on_obsidian.eval.human_review import (
    load_human_sample_ids,
    write_human_review,
)


def test_sprint22_sample_has_ten_gold_ids() -> None:
    path = Path("evals/human/sprint22_sample.yaml")
    ids = load_human_sample_ids(path)
    assert len(ids) == 10
    assert "q008" not in ids
    assert ids == (
        "q001",
        "q002",
        "q003",
        "q004",
        "q005",
        "q006",
        "q007",
        "q009",
        "q010",
        "q011",
    )


def test_write_human_review_keeps_sample_order_and_marks_missing(
    tmp_path: Path,
) -> None:
    review_path = tmp_path / "review.yaml"
    artifacts = [
        {
            "item_id": "q002",
            "question": "second?",
            "answer": "second answer",
            "refused": False,
            "skip_reason": None,
            "contexts": [{"chunk_id": 2, "note_path": "B.md", "text": "b"}],
            "faithfulness": 0.2,
            "answer_relevancy": 0.3,
        },
        {
            "item_id": "q001",
            "question": "first?",
            "answer": "first answer",
            "refused": False,
            "skip_reason": None,
            "contexts": [{"chunk_id": 1, "note_path": "A.md", "text": "a"}],
            "faithfulness": 0.9,
            "answer_relevancy": 0.8,
        },
    ]
    written = write_human_review(review_path, artifacts, ("q001", "q008", "q002"))
    assert written == 2
    payload = yaml.safe_load(review_path.read_text(encoding="utf-8"))
    ids = [item["id"] for item in payload["items"]]
    assert ids == ["q001", "q008", "q002"]
    assert payload["items"][0]["answer"] == "first answer"
    assert payload["items"][0]["contexts"][0]["text"] == "a"
    assert payload["items"][1]["missing"] is True
    assert payload["items"][2]["question"] == "second?"

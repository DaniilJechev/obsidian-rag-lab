from rag_based_on_obsidian.eval.contracts import GoldItem, LiveGoldItem
from rag_based_on_obsidian.eval.postgres_loader import (
    UnresolvedEvalNoteIdsError,
    bind_live_gold_items,
    stored_eval_item_from_mapping,
)
from rag_based_on_obsidian.eval.retrieval.live_runner import run_live_eval
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk


def _chunk(note_id: int, rank: int, path: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=rank,
        text="body",
        score=1.0,
        retrieval_method=RetrievalMethod.DENSE,
        metadata={"note_id": note_id, "source_path": path},
        chunking_version="v1",
        rank=rank,
        point_key=f"key-{rank}",
    )


def test_run_live_eval_collapses_and_scores_by_note_id() -> None:
    item = LiveGoldItem(
        item_id="q001",
        eval_item_id=11,
        question="What is dropout?",
        relevant_note_ids=(10, 20),
        relevant_note_paths=("DLS1/a.md", "DLS2/b.md"),
        dataset_version="phase7-note-level-v1",
    )
    queries: list[str] = []

    def retrieve(query: str) -> list[RetrievedChunk]:
        queries.append(query)
        return [
            _chunk(10, 1, "DLS1/a.md"),
            _chunk(10, 2, "DLS1/a.md"),
            _chunk(30, 3, "DLS1/noise.md"),
        ]

    results, artifacts = run_live_eval([item], retrieve, k=10)

    assert queries == ["What is dropout?"]
    assert results[0].skipped is False
    assert results[0].k == 10
    assert results[0].hit == 1.0
    assert results[0].recall == 0.5
    assert artifacts[0]["hits"] == [10]
    assert artifacts[0]["misses"] == [20]
    assert artifacts[0]["predicted_note_ids"] == [10, 30]


def test_run_live_eval_skips_chunks_without_note_id() -> None:
    item = LiveGoldItem(
        item_id="q002",
        eval_item_id=12,
        question="broken payload",
        relevant_note_ids=(10,),
        relevant_note_paths=("DLS1/a.md",),
        dataset_version="phase7-note-level-v1",
    )
    chunk = RetrievedChunk(
        chunk_id=1,
        text="body",
        score=1.0,
        retrieval_method=RetrievalMethod.BM25,
        metadata={},
        chunking_version="v1",
        rank=1,
        point_key="key-1",
    )

    results, artifacts = run_live_eval([item], lambda _query: [chunk], k=10)

    assert results[0].skipped is True
    assert results[0].skip_reason is not None
    assert artifacts[0]["skipped"] is True


def test_stored_eval_item_from_mapping_parses_json_ids() -> None:
    item = stored_eval_item_from_mapping(
        {
            "eval_item_id": 7,
            "question": "What is nDCG?",
            "corpus_scope": "DLS1+DLS2",
            "relevant_note_ids": [4, 8],
            "dataset_version": "phase7-note-level-v1",
        }
    )

    assert item.eval_item_id == 7
    assert item.relevant_note_ids == (4, 8)


def test_bind_live_gold_items_uses_yaml_id_and_paths() -> None:
    stored = stored_eval_item_from_mapping(
        {
            "eval_item_id": 7,
            "question": "What is nDCG?",
            "corpus_scope": "DLS1+DLS2",
            "relevant_note_ids": [4],
            "dataset_version": "phase7-note-level-v1",
        }
    )
    yaml_item = GoldItem(
        item_id="q009",
        question="What is nDCG?",
        corpus_scope="DLS1+DLS2",
        relevant_note_paths=("DLS1/nDCG.md",),
        dataset_version="phase7-note-level-v1",
        source_directory="DLS1",
    )

    bound = bind_live_gold_items(
        [stored],
        {"DLS1/nDCG.md": 4},
        [yaml_item],
    )

    assert bound[0].item_id == "q009"
    assert bound[0].relevant_note_paths == ("DLS1/nDCG.md",)


def test_bind_live_gold_items_rejects_missing_note_ids() -> None:
    stored = stored_eval_item_from_mapping(
        {
            "eval_item_id": 7,
            "question": "What is nDCG?",
            "corpus_scope": "DLS1+DLS2",
            "relevant_note_ids": [99],
            "dataset_version": "phase7-note-level-v1",
        }
    )
    try:
        bind_live_gold_items([stored], {"DLS1/nDCG.md": 4})
    except UnresolvedEvalNoteIdsError as exc:
        assert exc.missing_ids == (99,)
    else:
        raise AssertionError("missing note ids must fail")

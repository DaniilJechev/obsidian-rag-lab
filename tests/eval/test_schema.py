from rag_based_on_obsidian.db.schema import eval_items


def test_eval_items_table_matches_phase2_contract() -> None:
    column_names = {column.name for column in eval_items.columns}

    assert column_names == {
        "eval_item_id",
        "question",
        "corpus_scope",
        "relevant_note_ids",
        "relevant_chunk_ids",
        "dataset_version",
        "created_at",
    }
    constraint_names = {constraint.name for constraint in eval_items.constraints}
    assert "uq_eval_items_dataset_question" in constraint_names

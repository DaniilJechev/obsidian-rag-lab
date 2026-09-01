from rag_based_on_obsidian.eval.ragas.ragas_import import (
    import_ragas,
    install_vertexai_import_stubs,
)


def test_import_ragas_after_vertex_stubs() -> None:
    install_vertexai_import_stubs()
    ragas = import_ragas()
    assert ragas.__name__ == "ragas"
    from ragas.metrics import answer_relevancy, faithfulness

    assert faithfulness is not None
    assert answer_relevancy is not None

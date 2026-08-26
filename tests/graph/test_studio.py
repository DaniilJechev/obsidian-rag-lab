"""Studio entrypoint: stub graph compiles without live services."""

from rag_based_on_obsidian.lang_graph.studio import graph


def test_studio_stub_factory_compiles() -> None:
    app = graph()
    assert app is not None
    assert hasattr(app, "ainvoke")

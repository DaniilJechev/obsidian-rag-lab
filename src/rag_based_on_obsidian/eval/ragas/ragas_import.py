"""Import ragas 0.4.3 without pulling Google Vertex.

ragas.llms.base still does a hard import of ChatVertexAI from
langchain_community.chat_models.vertexai. That module was removed in
langchain-community 0.4.x, so ``import ragas`` crashes even if we never
call Vertex. We stub the missing names before importing ragas.

Do not install langchain-google-vertexai just to make the import work.
Do not downgrade langchain-core.
"""

from __future__ import annotations

import sys
import types
from typing import Any


def install_vertexai_import_stubs() -> None:
    """Register dummy Vertex classes so ragas can import on modern LangChain."""
    _stub_module(
        "langchain_community.chat_models.vertexai",
        ChatVertexAI=_MissingVertexModel,
    )
    _stub_module(
        "langchain_community.llms.vertexai",
        VertexAI=_MissingVertexModel,
    )


def import_ragas() -> Any:
    """Import the ragas package after Vertex stubs are in place."""
    install_vertexai_import_stubs()
    import ragas

    return ragas


class _MissingVertexModel:
    """Placeholder matching ragas' optional Vertex class names."""


def _stub_module(fullname: str, **attributes: object) -> None:
    existing = sys.modules.get(fullname)
    if existing is not None:
        for name, value in attributes.items():
            if not hasattr(existing, name):
                setattr(existing, name, value)
        return
    module = types.ModuleType(fullname)
    for name, value in attributes.items():
        setattr(module, name, value)
    sys.modules[fullname] = module
    parent_name, _, child = fullname.rpartition(".")
    parent = sys.modules.get(parent_name)
    if parent is not None:
        setattr(parent, child, module)

from pathlib import Path, PurePosixPath

from rag_based_on_obsidian.chunking.policy import ChunkingPolicy
from rag_based_on_obsidian.chunking.recursive import chunk_section_tree
from rag_based_on_obsidian.chunking.section_tree import build_section_tree
from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file


def build_tree(tmp_path: Path, content: str):
    path = tmp_path / "DLS1" / "note.md"
    path.parent.mkdir()
    path.write_text(content, encoding="utf-8")
    parsed = parse_markdown_file(
        DiscoveredFile(
            absolute_path=path,
            relative_path=PurePosixPath("DLS1/note.md"),
        )
    )
    return build_section_tree(
        parsed,
        note_id=7,
        source_content_hash="hash:note",
        parser_version="parser-v1",
    ), content


def test_recursive_chunker_preserves_context_and_provenance(tmp_path: Path) -> None:
    tree, source_text = build_tree(
        tmp_path,
        "# Retrieval\n\nVector search finds similar chunks.",
    )
    policy = ChunkingPolicy(
        name="test",
        chunk_size=100,
        chunk_overlap=10,
        separators=["\n\n", "\n", " "],
    )

    chunks = chunk_section_tree(
        tree,
        source_text=source_text,
        policy=policy,
        chunking_version="chunk-v1",
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.text.startswith("# Retrieval")
    assert source_text[chunk.start_offset : chunk.end_offset].startswith("# Retrieval")
    assert chunk.note_id == 7
    assert chunk.section_path == ("Retrieval",)
    assert chunk.chunking_version == "chunk-v1"
    assert chunk.word_count > 0
    assert chunk.token_count >= chunk.word_count


def test_oversized_sections_split_deterministically_with_heading_context(
    tmp_path: Path,
) -> None:
    content = (
        "# Retrieval\n\n"
        "Vector search finds similar chunks and ranks candidates carefully. "
        "Metadata filters narrow the search space. "
        "The final context is sent to the answer generator."
    )
    tree, source_text = build_tree(tmp_path, content)
    policy = ChunkingPolicy(
        name="small",
        chunk_size=12,
        chunk_overlap=3,
        separators=["\n\n", "\n", " "],
    )

    first = chunk_section_tree(
        tree,
        source_text=source_text,
        policy=policy,
        chunking_version="chunk-v1",
    )
    second = chunk_section_tree(
        tree,
        source_text=source_text,
        policy=policy,
        chunking_version="chunk-v1",
    )

    assert len(first) > 1
    assert first == second
    assert all(chunk.text.startswith("# Retrieval") for chunk in first)
    assert all(chunk.chunking_version == "chunk-v1" for chunk in first)


def test_small_code_block_is_not_split_when_policy_preserves_it(tmp_path: Path) -> None:
    content = (
        "# Python\n\n"
        "Introductory explanation before the example.\n\n"
        "```python\n"
        "result = model.encode(text)\n"
        "print(result)\n"
        "```\n\n"
        "Closing explanation after the example."
    )
    tree, source_text = build_tree(tmp_path, content)
    policy = ChunkingPolicy(
        name="code",
        chunk_size=20,
        chunk_overlap=0,
        separators=["\n\n", "\n", " "],
        preserve_code_blocks=True,
    )

    chunks = chunk_section_tree(
        tree,
        source_text=source_text,
        policy=policy,
        chunking_version="chunk-v1",
    )

    code = "```python\nresult = model.encode(text)\nprint(result)\n```"
    assert any(code in chunk.text for chunk in chunks)

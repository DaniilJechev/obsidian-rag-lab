"""Budget retrieved chunks into a prompt the LLM can cite."""

from dataclasses import dataclass
from pathlib import Path

from rag_based_on_obsidian.llm.contracts import LLMMessage
from rag_based_on_obsidian.retrieval.contracts import RetrievedChunk

SYSTEM_PROMPT = (
    "You answer questions about an Obsidian ML/NLP vault. 1) Use only the provided "
    "chunks. 2) Cite notes as [[note title]] in the answer. 3) Return a JSON object "
    "with keys: answer (string), citations (array of {chunk_id, note_path}), "
    "confidence (number 0 to 1). 4) Do not invent chunk ids. If the chunks do "
    "not contain the answer, still return JSON with a short honest answer and "
    "low confidence."
)


@dataclass(frozen=True)
class PackedChunk:
    """One chunk after token-budget trimming, ready for the prompt."""

    chunk_id: int
    note_path: str
    text: str
    score: float


def estimate_tokens(text: str) -> int:
    """Approximate tokens without a model-specific tokenizer (~4 chars)."""
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, (len(stripped) + 3) // 4)


def note_path_from_chunk(chunk: RetrievedChunk) -> str:
    """Read Qdrant payload ``source_path``, or a stable fallback."""
    raw = chunk.metadata.get("source_path")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return f"chunk-{chunk.chunk_id}"


def note_title(note_path: str) -> str:
    """Obsidian wikilink target: file stem without directories."""
    stem = Path(note_path).stem
    return stem if stem else note_path


def should_refuse(
    chunks: list[RetrievedChunk],
    *,
    min_retrieval_score: float,
) -> str | None:
    """Return a refusal reason, or None when generation may proceed."""
    if not chunks:
        return "no retrieved context"
    best = max(chunk.score for chunk in chunks)
    if best < min_retrieval_score:
        return "retrieved context is below the score threshold"
    return None


def pack_chunks(
    chunks: list[RetrievedChunk],
    *,
    max_context_tokens: int,
) -> list[PackedChunk]:
    """Keep prefix of the ranking that fits the context budget."""
    packed: list[PackedChunk] = []
    used = 0
    for chunk in chunks:
        note_path = note_path_from_chunk(chunk)
        text = chunk.text.strip()
        tokens = estimate_tokens(text)
        if packed and used + tokens > max_context_tokens:
            break
        if not packed and tokens > max_context_tokens:
            char_budget = max_context_tokens * 4
            text = text[:char_budget].rstrip()
            tokens = estimate_tokens(text)
        packed.append(
            PackedChunk(
                chunk_id=chunk.chunk_id,
                note_path=note_path,
                text=text,
                score=chunk.score,
            )
        )
        used += tokens
    return packed


def build_messages(query: str, packed: list[PackedChunk]) -> list[LLMMessage]:
    """System + user messages with numbered chunks the model can cite."""
    blocks: list[str] = [f"Question: {query.strip()}", "", "Chunks:"]
    for item in packed:
        title = note_title(item.note_path)
        blocks.append(
            f"[chunk_id={item.chunk_id} note_path={item.note_path} "
            f"title={title}]\n{item.text}"
        )
    return [
        LLMMessage(role="system", content=SYSTEM_PROMPT),
        LLMMessage(role="user", content="\n".join(blocks)),
    ]

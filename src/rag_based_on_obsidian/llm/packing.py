"""Budget retrieved chunks into a prompt the LLM can cite."""

from dataclasses import dataclass
from pathlib import Path

from rag_based_on_obsidian.llm.contracts import LLMMessage
from rag_based_on_obsidian.retrieval.contracts import RetrievedChunk

SYSTEM_PROMPT = (
    "You answer questions about an Obsidian ML/NLP vault.\n"
    "Rules:\n"
    "1) Use only the provided chunks.\n"
    "2) Cite notes as [[note title]] inside the answer string.\n"
    "3) Reply with ONE JSON object and nothing else: no markdown fences, "
    "no preamble, no trailing text.\n"
    "4) Required keys: answer (string), citations (array of objects with "
    "integer chunk_id and string note_path copied from the chunk headers), "
    "confidence (number from 0 to 1 = how sure you are the answer is "
    "supported by the chunks).\n"
    "5) Do not invent chunk ids. If chunks are insufficient, still return "
    "JSON with a short honest answer and low confidence.\n"
    "6) Keep answer concise (a few short paragraphs max). Prefer plain text "
    "over long lecture-style lists.\n"
    "7) JSON escaping is mandatory. Inside answer, use \\n for newlines. "
    "Never write a single backslash before a letter: sequences like "
    "\\approx, \\ge, \\int, \\log, \\sim are invalid JSON and will fail "
    "parsing. For math write ASCII words (approx, >=, integral, log, ~) "
    "or Unicode symbols (≈, ≥) with no backslashes. Do not use LaTeX "
    "backslash commands.\n"
    "8) Always finish a complete JSON object: close all quotes and braces, "
    "and always include citations and confidence before stopping.\n"
    "\n"
    "Example of a valid reply (shape only; invent nothing beyond chunks):\n"
    '{"answer":"RoPE rotates query/key vectors by position. See [[RoPE]].",'
    '"citations":[{"chunk_id":2046,"note_path":"DLS2/RoPE.md"}],'
    '"confidence":0.9}'
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

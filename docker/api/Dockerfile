FROM python:3.12-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_HTTP_TIMEOUT=600
ENV UV_CONCURRENT_DOWNLOADS=4
ENV HF_HOME=/models/hf
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY configs ./configs

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uvicorn", "rag_based_on_obsidian.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

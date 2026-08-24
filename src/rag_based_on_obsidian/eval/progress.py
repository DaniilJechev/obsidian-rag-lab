"""Stderr stage logs for eval CLI operations."""

from __future__ import annotations

import logging
import sys
from time import perf_counter

from tqdm import tqdm

LOGGER_NAME = "rag.eval"
logger = logging.getLogger(LOGGER_NAME)


def configure_eval_logging() -> None:
    """Send eval-stage messages to stderr, keeping JSON results on stdout."""
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [eval] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def eval_tqdm(*, total: int, desc: str, unit: str) -> tqdm:
    """Progress bar on stderr. Disabled when stderr is not a TTY (pytest)."""
    return tqdm(
        total=total,
        desc=desc,
        unit=unit,
        file=sys.stderr,
        dynamic_ncols=True,
        disable=not sys.stderr.isatty(),
    )


class EvalProgress:
    """Record named stages so the user can see load-gold is not stuck."""

    def __init__(self) -> None:
        self._started_at = perf_counter()
        self._last_at = self._started_at
        self.stage_seconds: dict[str, float] = {}

    def mark(self, stage: str, **details: object) -> None:
        """Log one completed stage and store its duration in seconds."""
        now = perf_counter()
        elapsed = now - self._last_at
        self.stage_seconds[stage] = elapsed
        self._last_at = now
        extra = "".join(f" {key}={value}" for key, value in details.items())
        logger.info(
            "stage=%s elapsed_s=%.3f total_s=%.3f%s",
            stage,
            elapsed,
            now - self._started_at,
            extra,
        )

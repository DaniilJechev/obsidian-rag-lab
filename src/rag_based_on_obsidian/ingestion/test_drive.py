"""Production-like local test-drive entry point for Sprint 6."""

from dataclasses import dataclass
from time import perf_counter

from sqlalchemy import create_engine, select
from tqdm import tqdm

from rag_based_on_obsidian.config import load_config
from rag_based_on_obsidian.corpus.discovery import discover_markdown_files
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.db.schema import ingestion_runs
from rag_based_on_obsidian.ingestion.operational_audit import (
    ConsistencyReport,
    RunMetrics,
    audit_run_consistency,
    calculate_run_metrics,
)
from rag_based_on_obsidian.ingestion.orchestrator import run_ingestion


@dataclass(frozen=True)
class TestDriveResult:
    """Observed result of one production-like ingestion run."""

    __test__ = False

    run_id: int
    discovered_files: int
    elapsed_seconds: float
    metrics: RunMetrics
    consistency: ConsistencyReport

    def __str__(self) -> str:
        """Render a formatted human-readable production-like report."""
        counters = self.metrics.counters
        consistency_status = "PASS" if self.consistency.passed else "FAIL"
        duration = self.metrics.duration_seconds
        duration_text = (
            f"{duration:.3f}s" if duration is not None else "unfinished"
        )
        return "\n".join(
            (
                "",
                "=== Sprint 6: Production-like ingestion ===",
                f"run_id:             {self.run_id}",
                f"discovered_files:   {self.discovered_files}",
                f"elapsed_seconds:    {self.elapsed_seconds:.3f}",
                "",
                "--- Counters ---",
                f"total:               {counters.total}",
                f"new:                 {counters.new}",
                f"changed:             {counters.changed}",
                f"unchanged:           {counters.unchanged}",
                f"stale:               {counters.stale}",
                f"failed:              {counters.failed}",
                "",
                "--- Metrics ---",
                f"database_duration:   {duration_text}",
                f"success_rate:        {self.metrics.success_rate:.2%}",
                "",
                "--- Consistency ---",
                f"status:              {consistency_status}",
                f"notes_in_scope:      {self.consistency.notes_in_scope}",
                f"states_in_run:       {self.consistency.states_in_run}",
                f"duplicate_paths:     {self.consistency.duplicate_note_paths}",
                f"duplicate_states:    {self.consistency.duplicate_note_run_states}",
                f"orphan_note_states:  {self.consistency.orphan_note_states}",
                f"orphan_run_states:   {self.consistency.orphan_run_states}",
                f"orphan_index_states: {self.consistency.orphan_index_states}",
                "",
            )
        )


def run_local_test_drive() -> TestDriveResult:
    """Run the configured DLS1+DLS2 corpus and audit its persisted state."""
    config = load_config()
    discovered_files = discover_markdown_files(
        config.vault_root,
        config.allowed_corpus_directories,
    )
    corpus_scope = ",".join(config.allowed_corpus_directories)
    engine = create_engine(load_database_url())
    started = perf_counter()
    try:
        with engine.connect() as connection:
            progress = tqdm(
                total=len(discovered_files),
                desc="Ingesting DLS1+DLS2",
                unit="file",
            )
            run_ingestion(
                connection,
                discovered_files,
                corpus_scope=corpus_scope,
                progress_callback=lambda current, _total, path: _update_progress(
                    progress,
                    current,
                    path,
                ),
            )
            progress.close()
            run_id = connection.execute(
                select(ingestion_runs.c.run_id)
                .where(ingestion_runs.c.corpus_scope == corpus_scope)
                .order_by(ingestion_runs.c.run_id.desc())
                .limit(1)
            ).scalar_one()
            metrics = calculate_run_metrics(connection, run_id)
            consistency = audit_run_consistency(
                connection,
                run_id,
                corpus_scope=corpus_scope,
            )
        return TestDriveResult(
            run_id=run_id,
            discovered_files=len(discovered_files),
            elapsed_seconds=perf_counter() - started,
            metrics=metrics,
            consistency=consistency,
        )
    finally:
        engine.dispose()


def _update_progress(progress: tqdm, current: int, path: str) -> None:
    """Advance the progress bar and show the current relative path."""
    progress.update(current - progress.n)
    progress.set_postfix_str(path, refresh=False)


def main() -> None:
    """Run the local test drive and print its formatted report."""
    print(run_local_test_drive())


if __name__ == "__main__":
    main()


__all__ = ["TestDriveResult", "run_local_test_drive"]

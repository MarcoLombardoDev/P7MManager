# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""The execution queue: a list of files, worked through by a pool of threads.

Kept free of Qt on purpose. The queue reports what happens by calling a
listener, and the interface turns those calls into rows on a table — which
means the whole of this module is testable without a display, and the command
line uses the same code path the window does.

The work is I/O and hashing, so threads are the right tool: cancelling is
cooperative and checked between files, never mid-write, so a cancelled run
leaves no partial output.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass, field
from enum import Enum
from itertools import count
from pathlib import Path

from .analyzer import Outcome, analyse
from .extractor import ExtractionResult, ExtractionSettings, extract

__all__ = ["JobState", "Job", "QueueEvent", "JobQueue", "DEFAULT_WORKERS"]

DEFAULT_WORKERS = 4
MAX_WORKERS = 16


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    WARNING = "warning"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_final(self) -> bool:
        return self is not JobState.PENDING and self is not JobState.RUNNING


@dataclass
class Job:
    """One file in the queue, and whatever is known about it so far."""

    id: int
    path: Path
    size: int = 0
    state: JobState = JobState.PENDING
    message: str = ""
    result: ExtractionResult | None = None

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def output_path(self) -> Path | None:
        return self.result.output_path if self.result else None

    @property
    def signature_count(self) -> int:
        return self.result.analysis.signature_count if self.result else 0

    @property
    def signers(self) -> str:
        if not self.result:
            return ""
        names = [signer.display_name for signer in self.result.analysis.signers]
        if not names:
            return ""
        first = names[0]
        return first if len(names) == 1 else f"{first} (+{len(names) - 1})"


@dataclass
class QueueEvent:
    """Something the queue did, handed to the listener as it happens."""

    kind: str                    # added | cleared | started | job | progress | finished
    job: Job | None = None
    done: int = 0
    total: int = 0
    cancelled: bool = False
    jobs: list[Job] = field(default_factory=list)


Listener = Callable[[QueueEvent], None]


class JobQueue:
    """A queue of containers to analyse or extract.

    The listener is called from worker threads. Interfaces are expected to
    hand the event to their own loop rather than touching widgets directly.
    """

    def __init__(self, listener: Listener | None = None, workers: int = DEFAULT_WORKERS):
        self._listener = listener
        self._workers = max(1, min(int(workers), MAX_WORKERS))
        self._jobs: list[Job] = []
        self._ids = count(1)
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._running = threading.Event()
        self._executor: ThreadPoolExecutor | None = None
        self._futures: list[Future] = []
        self._done = 0

    # -- composition --------------------------------------------------
    @property
    def jobs(self) -> list[Job]:
        with self._lock:
            return list(self._jobs)

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    @property
    def workers(self) -> int:
        return self._workers

    def set_workers(self, workers: int) -> None:
        self._workers = max(1, min(int(workers), MAX_WORKERS))

    def add(self, paths: Iterable[str | Path]) -> list[Job]:
        """Add files, ignoring ones already queued. Returns the new jobs."""
        added: list[Job] = []
        with self._lock:
            known = {job.path.resolve() if job.path.exists() else job.path
                     for job in self._jobs}
            for item in paths:
                path = Path(item)
                key = path.resolve() if path.exists() else path
                if key in known:
                    continue
                known.add(key)
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                job = Job(id=next(self._ids), path=path, size=size)
                self._jobs.append(job)
                added.append(job)
        if added:
            self._emit(QueueEvent(kind="added", jobs=added, total=len(self._jobs)))
        return added

    def remove(self, job_ids: Iterable[int]) -> None:
        """Drop jobs that are not currently being worked on."""
        targets = set(job_ids)
        with self._lock:
            self._jobs = [
                job for job in self._jobs
                if job.id not in targets or job.state is JobState.RUNNING
            ]
        self._emit(QueueEvent(kind="cleared", jobs=self.jobs, total=len(self._jobs)))

    def clear(self, completed_only: bool = False) -> None:
        with self._lock:
            if completed_only:
                self._jobs = [job for job in self._jobs if not job.state.is_final]
            else:
                self._jobs = [job for job in self._jobs if job.state is JobState.RUNNING]
        self._emit(QueueEvent(kind="cleared", jobs=self.jobs, total=len(self._jobs)))

    def reset_states(self) -> None:
        """Put finished jobs back to pending so the queue can be run again."""
        with self._lock:
            for job in self._jobs:
                if job.state.is_final:
                    job.state = JobState.PENDING
                    job.message = ""
                    job.result = None

    # -- running ------------------------------------------------------
    def start(self, settings: ExtractionSettings | None = None, rerun: bool = False) -> bool:
        """Begin processing pending jobs. Returns False if already running."""
        if self._running.is_set():
            return False
        if rerun:
            self.reset_states()
        pending = [job for job in self.jobs if job.state is JobState.PENDING]
        if not pending:
            return False

        settings = settings or ExtractionSettings()
        self._cancel.clear()
        self._running.set()
        self._done = 0
        total = len(pending)
        self._emit(QueueEvent(kind="started", total=total))

        self._executor = ThreadPoolExecutor(
            max_workers=self._workers, thread_name_prefix="p7m"
        )
        self._futures = [
            self._executor.submit(self._run_job, job, settings, total) for job in pending
        ]
        threading.Thread(
            target=self._await_completion, args=(total,), name="p7m-queue", daemon=True
        ).start()
        return True

    def cancel(self) -> None:
        """Ask the queue to stop; jobs not yet started are marked cancelled."""
        if not self._running.is_set():
            return
        self._cancel.set()
        for future in self._futures:
            future.cancel()

    def wait(self, timeout: float | None = None) -> bool:
        """Block until the current run finishes. Mostly for tests and the CLI."""
        deadline = threading.Event()

        def watcher() -> None:
            while self._running.is_set():
                deadline.wait(0.02)
            deadline.set()

        if not self._running.is_set():
            return True
        threading.Thread(target=watcher, daemon=True).start()
        return deadline.wait(timeout)

    # -- internals ----------------------------------------------------
    def _run_job(self, job: Job, settings: ExtractionSettings, total: int) -> None:
        if self._cancel.is_set():
            job.state = JobState.CANCELLED
            job.message = "cancelled"
            self._finish_job(job, total)
            return

        job.state = JobState.RUNNING
        self._emit(QueueEvent(kind="job", job=job))
        try:
            if settings.analyse_only:
                analysis = analyse(job.path, verify=settings.verify)
                result = ExtractionResult(
                    analysis=analysis,
                    analysis_only=True,
                    message=analysis.summary,
                    warnings=list(analysis.warnings),
                )
            else:
                result = extract(job.path, settings)
            job.result = result
            job.message = result.message
            job.state = {
                Outcome.OK: JobState.DONE,
                Outcome.WARNING: JobState.WARNING,
                Outcome.ERROR: JobState.FAILED,
            }[result.outcome]
            if result.skipped:
                job.state = JobState.SKIPPED
        except Exception as exc:  # pragma: no cover - the queue must never die
            job.state = JobState.FAILED
            job.message = f"unexpected error: {exc}"
        self._finish_job(job, total)

    def _finish_job(self, job: Job, total: int) -> None:
        with self._lock:
            self._done += 1
            done = self._done
        self._emit(QueueEvent(kind="job", job=job))
        self._emit(QueueEvent(kind="progress", job=job, done=done, total=total))

    def _await_completion(self, total: int) -> None:
        for future in self._futures:
            try:
                future.result()
            except Exception:  # pragma: no cover - already handled per job
                continue
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
        cancelled = self._cancel.is_set()
        with self._lock:
            for job in self._jobs:
                if job.state is JobState.PENDING and cancelled:
                    job.state = JobState.CANCELLED
                    job.message = "cancelled"
        self._running.clear()
        self._emit(
            QueueEvent(kind="finished", done=self._done, total=total, cancelled=cancelled)
        )

    def _emit(self, event: QueueEvent) -> None:
        if self._listener is None:
            return
        with suppress(Exception):  # a bad listener must never stop the work
            self._listener(event)

    # -- reporting ----------------------------------------------------
    def counts(self) -> dict[str, int]:
        tally = {state.value: 0 for state in JobState}
        for job in self.jobs:
            tally[job.state.value] += 1
        return tally

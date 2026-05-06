"""In-process job runner for Sprecher."""

import asyncio
import threading
from typing import Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from jobs.models import JobStatus


class RunnerState(Enum):
    """Job runner states."""
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"


@dataclass
class Job:
    """Internal job representation."""
    id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    state: JobStatus = JobStatus.QUEUED
    result: Any = None
    error: Optional[Exception] = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class JobRunner:
    """
    Singleton in-process job runner using asyncio.

    Similar to WeirDing's JobRunner pattern.
    """

    _instance: Optional["JobRunner"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, concurrency: int = 1):
        """Initialize job runner."""
        self._concurrency = concurrency
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._state = RunnerState.IDLE
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    @classmethod
    def get_instance(cls, concurrency: int = 1) -> "JobRunner":
        """Get singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(concurrency)
            return cls._instance

    def start(self) -> None:
        """Start the job runner in a background thread."""
        if self._state != RunnerState.IDLE:
            return

        self._state = RunnerState.RUNNING
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        """Run the asyncio event loop in background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._process_jobs())

    async def _process_jobs(self) -> None:
        """Process jobs from queue."""
        while self._state == RunnerState.RUNNING:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._execute_job(job)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # Log error but continue processing
                print(f"Job error: {e}")

    async def _execute_job(self, job: Job) -> None:
        """Execute a single job."""
        job.state = JobStatus.RUNNING
        try:
            result = await asyncio.to_thread(job.func, *job.args, **job.kwargs)
            job.result = result
            job.state = JobStatus.COMPLETED
        except Exception as e:
            job.error = e
            job.state = JobStatus.FAILED

    async def enqueue(self, func: Callable, *args, **kwargs) -> Job:
        """
        Enqueue a job for async execution.

        Returns a Job object with id for tracking.
        """
        job_id = f"job_{id(func)}_{len(args)}"
        job = Job(id=job_id, func=func, args=args, kwargs=kwargs)
        await self._queue.put(job)
        return job

    def enqueue_sync(self, func: Callable, *args, **kwargs) -> Any:
        """
        Enqueue a job and wait for result (synchronous interface).

        Used from sync contexts like FastAPI routes with run_in_executor.
        """
        if self._loop is None or not self._loop.is_running():
            # Need to run in the existing loop
            future = asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(
                    self.enqueue(func, *args, **kwargs),
                    self._loop
                )
            )
            return future.result(timeout=300)
        else:
            # Already in async context
            return asyncio.create_task(self.enqueue(func, *args, **kwargs))

    def get_status(self, job_id: str) -> Optional[JobStatus]:
        """Get status of a job by ID."""
        # For simplicity, jobs are not stored after completion
        return None

    def stop(self) -> None:
        """Stop the job runner."""
        self._state = RunnerState.STOPPING
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)


# Global singleton
_runner: Optional[JobRunner] = None


def get_job_runner() -> JobRunner:
    """Get the global job runner singleton."""
    global _runner
    if _runner is None:
        _runner = JobRunner.get_instance()
        _runner.start()
    return _runner
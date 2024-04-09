import asyncio
import dataclasses
import logging
import typing

import aiojobs

import lib.utils.aiojobs.jobs as utils_aiojobs_jobs

logger = logging.getLogger(__name__)

AioJobsScheduler = aiojobs.Scheduler


@dataclasses.dataclass
class Settings:
    limit: int | None
    pending_limit: int | None
    close_timeout: float | None


class SchedulerProtocol(typing.Protocol):
    class DisposeError(Exception): ...

    @classmethod
    def from_settings(cls, settings: Settings) -> typing.Self: ...

    def defer_jobs(self, *jobs: utils_aiojobs_jobs.JobProtocol) -> None: ...

    async def spawn_deferred_jobs(self) -> None: ...

    async def spawn_job(self, job: utils_aiojobs_jobs.JobProtocol) -> None: ...

    async def dispose(self) -> None:
        """
        :raises DisposeError when unable to close aiojobs.Scheduler.
        """
        ...


class Scheduler(SchedulerProtocol):
    def __init__(self, aiojobs_scheduler: AioJobsScheduler) -> None:
        self._aiojobs_scheduler = aiojobs_scheduler
        self._prepared_jobs: list[utils_aiojobs_jobs.JobProtocol] = []

    @classmethod
    def from_settings(cls, settings: Settings) -> typing.Self:
        pending_limit = settings.pending_limit
        if pending_limit is None:
            pending_limit = 0

        return cls(
            aiojobs_scheduler=AioJobsScheduler(
                exception_handler=None,
                limit=settings.limit,
                pending_limit=pending_limit,
                close_timeout=settings.close_timeout,
            ),
        )

    def defer_jobs(self, *jobs: utils_aiojobs_jobs.JobProtocol) -> None:
        self._prepared_jobs.extend(jobs)

    async def spawn_deferred_jobs(self) -> None:
        logger.info("Prepared jobs are starting")

        while self._prepared_jobs:
            job = self._prepared_jobs.pop()
            await self.spawn_job(job)

        logger.info("Prepared jobs were successfully started")

    async def spawn_job(self, job: utils_aiojobs_jobs.JobProtocol) -> None:
        logger.info("Spawning job %r", job.name)
        await self._aiojobs_scheduler.spawn(job.process())

    async def dispose(self) -> None:
        try:
            await self._aiojobs_scheduler.close()
        except asyncio.CancelledError:
            # See: https://github.com/aio-libs/aiojobs/issues/252
            pass
        except Exception as unexpected_error:
            raise self.DisposeError from unexpected_error

    @property
    def is_empty(self) -> bool:
        return len(self._aiojobs_scheduler) == 0


__all__ = [
    "Scheduler",
    "SchedulerProtocol",
    "Settings",
]

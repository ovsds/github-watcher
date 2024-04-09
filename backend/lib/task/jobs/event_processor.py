import logging

import lib.task.base as task_base
import lib.task.jobs.models as task_job_models
import lib.task.repositories as task_repositories
import lib.utils.aiojobs as aiojobs_utils

logger = logging.getLogger(__name__)

DELAY_TIMEOUT = 0
RETRY_TIMEOUT = 1


class EventProcessorJob(aiojobs_utils.RepeatableJob):
    def __init__(
        self,
        job_id: int,
        max_retries: int,
        queue_repository: task_repositories.QueueRepositoryProtocol,
    ):
        self._id = job_id
        self._max_retries = max_retries
        self._queue_repository = queue_repository

        super().__init__(
            logger=logger,
            delay_timeout=DELAY_TIMEOUT,
            retry_timeout=RETRY_TIMEOUT,
        )

    @property
    def name(self) -> str:
        return f"{super().name}({self._id})"

    async def _process(self) -> None:
        try:
            async with self._queue_repository.acquire(topic=task_repositories.Topic.EVENT_JOB) as event_job:
                assert isinstance(event_job, task_job_models.EventJob)
                logger.debug("Processing EventJob(%s)", event_job.id)
                try:
                    await self._process_event(event_job=event_job)
                except Exception:
                    logger.error("EventJob(%s) has failed", event_job.id)
                    if event_job.retry_count + 1 < self._max_retries:
                        await self._queue_repository.push(
                            topic=task_repositories.Topic.EVENT_JOB,
                            item=event_job.copy_retry(),
                            validate_not_closed=False,
                        )
                    else:
                        logger.error("EventJob(%s) has reached max retries", event_job.id)
                        await self._queue_repository.push(
                            topic=task_repositories.Topic.FAILED_EVENT_JOB,
                            item=event_job,
                        )
                    await self._queue_repository.consume(topic=task_repositories.Topic.EVENT_JOB, item=event_job)
                    raise
                else:
                    await self._queue_repository.consume(topic=task_repositories.Topic.EVENT_JOB, item=event_job)
                    logger.debug("EventJob(%s) has been processed", event_job.id)
        except task_repositories.QueueRepositoryProtocol.TopicFinished:
            logger.debug("Event queue is closed, finishing job")
            self.finish()

    async def _process_event(self, event_job: task_job_models.EventJob) -> None:
        event_processor = task_base.action_processor_factory(
            config=event_job.action,
        )
        try:
            await event_processor.process(event=event_job.event)
        finally:
            await event_processor.dispose()


__all__ = [
    "EventProcessorJob",
]

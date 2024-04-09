import logging

import lib.task.jobs.models as task_job_models
import lib.task.repositories as task_repositories
import lib.utils.aiojobs as aiojobs_utils

logger = logging.getLogger(__name__)

DELAY_TIMEOUT = 0
RETRY_TIMEOUT = 1


class TaskProcessorJob(aiojobs_utils.RepeatableJob):
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
            async with self._queue_repository.acquire(topic=task_repositories.Topic.TASK_JOB) as task_job:
                assert isinstance(task_job, task_job_models.TaskJob)
                logging.debug("Processing TaskJob(%s)", task_job.id)
                try:
                    await self._process_task(task_job=task_job)
                except Exception:
                    logger.error("TaskJob(%s) has failed", task_job.id)
                    if task_job.retry_count + 1 < self._max_retries:
                        await self._queue_repository.push(
                            topic=task_repositories.Topic.TASK_JOB,
                            item=task_job.copy_retry(),
                            validate_not_closed=False,
                        )
                    else:
                        logger.error("TaskJob(%s) has reached max retries", task_job.id)
                        await self._queue_repository.push(
                            topic=task_repositories.Topic.FAILED_TASK_JOB,
                            item=task_job,
                        )
                    await self._queue_repository.consume(topic=task_repositories.Topic.TASK_JOB, item=task_job)
                    raise
                else:
                    await self._queue_repository.consume(topic=task_repositories.Topic.TASK_JOB, item=task_job)
                    logger.debug("TaskJob(%s) has been processed", task_job.id)
        except task_repositories.QueueRepositoryProtocol.TopicFinished:
            logger.debug("Task queue is closed, finishing job")
            await self._queue_repository.close_topic(topic=task_repositories.Topic.TRIGGER_JOB)
            self.finish()

    async def _process_task(self, task_job: task_job_models.TaskJob) -> None:
        task = task_job.task
        for trigger in task.triggers:
            await self._queue_repository.push(
                topic=task_repositories.Topic.TRIGGER_JOB,
                item=task_job_models.TriggerJob(
                    id=f"{task.id}/{trigger.id}",
                    task_id=task.id,
                    trigger=trigger,
                    actions=task.actions,
                ),
            )


__all__ = [
    "TaskProcessorJob",
]

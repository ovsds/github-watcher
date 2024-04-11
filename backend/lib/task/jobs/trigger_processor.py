import logging

import lib.task.base as task_base
import lib.task.jobs.models as task_job_models
import lib.task.repositories as task_repositories
import lib.utils.aiojobs as aiojobs_utils

logger = logging.getLogger(__name__)

DELAY_TIMEOUT = 0
RETRY_TIMEOUT = 1


class TriggerProcessorJob(aiojobs_utils.RepeatableJob):
    def __init__(
        self,
        job_id: int,
        max_retries: int,
        queue_repository: task_repositories.QueueRepositoryProtocol,
        state_repository: task_repositories.StateRepositoryProtocol,
    ):
        self._id = job_id
        self._max_retries = max_retries
        self._queue_repository = queue_repository
        self._state_repository = state_repository

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
            async with self._queue_repository.acquire(topic=task_repositories.JobTopic.TRIGGER) as trigger_job:
                assert isinstance(trigger_job, task_job_models.TriggerJob)
                logger.debug("Processing TriggerJob(%s)", trigger_job.id)
                try:
                    await self._process_trigger(trigger_job=trigger_job)
                except Exception:
                    logger.exception("Error processing TriggerJob(%s)", trigger_job.id)
                    if trigger_job.retry_count + 1 < self._max_retries:
                        await self._queue_repository.push(
                            topic=task_repositories.JobTopic.TRIGGER,
                            item=trigger_job.copy_retry(),
                            validate_not_closed=False,
                        )
                    else:
                        logger.error("TriggerJob(%s) has reached max retries", trigger_job.id)
                        await self._queue_repository.push(
                            topic=task_repositories.JobTopic.FAILED_TRIGGER,
                            item=trigger_job,
                        )
                    await self._queue_repository.consume(topic=task_repositories.JobTopic.TRIGGER, item=trigger_job)
                    raise
                else:
                    await self._queue_repository.consume(topic=task_repositories.JobTopic.TRIGGER, item=trigger_job)
                    logger.info("TriggerJob(%s) has been processed", trigger_job.id)
        except task_repositories.QueueRepositoryProtocol.TopicFinished:
            logger.debug("Trigger queue is closed, finishing job")
            await self._queue_repository.close_topic(topic=task_repositories.JobTopic.EVENT)
            self.finish()

    async def _process_trigger(self, trigger_job: task_job_models.TriggerJob) -> None:
        task_id = trigger_job.task_id
        trigger = trigger_job.trigger

        state = await self._state_repository.get_state(path=f"tasks/{task_id}/triggers/{trigger.id}")

        trigger_processor = task_base.trigger_processor_factory(
            config=trigger_job.trigger,
            state=state,
        )
        try:
            async for raw_event in trigger_processor.produce_events():
                for action in trigger_job.actions:
                    event_job = task_job_models.EventJob(
                        id=f"{task_id}/{trigger.id}/{action.id}/{raw_event.id}",
                        event=raw_event,
                        action=action,
                    )
                    await self._queue_repository.push(
                        topic=task_repositories.JobTopic.EVENT,
                        item=event_job,
                    )
                    logger.info("EventJob(%s) was spawned", event_job.id)
        finally:
            await trigger_processor.dispose()


__all__ = [
    "TriggerProcessorJob",
]

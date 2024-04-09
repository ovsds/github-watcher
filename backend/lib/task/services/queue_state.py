import enum
import logging

import lib.task.jobs as task_jobs
import lib.task.repositories as task_repositories
import lib.utils.json as json_utils


class JobProcessorQueueStateMode(str, enum.Enum):
    PRESERVE = "preserve"
    RESTART = "restart"
    RESTART_ALL = "restart_all"
    NONE = "none"


logger = logging.getLogger(__name__)


class QueueStateService:
    def __init__(
        self,
        queue_repository: task_repositories.QueueRepositoryProtocol,
        state_repository: task_repositories.StateRepositoryProtocol,
        task_queue_mode: JobProcessorQueueStateMode,
        trigger_queue_mode: JobProcessorQueueStateMode,
        event_queue_mode: JobProcessorQueueStateMode,
    ):
        self._queue_repository = queue_repository
        self._state_repository = state_repository
        self._task_queue_mode = task_queue_mode
        self._trigger_queue_mode = trigger_queue_mode
        self._event_queue_mode = event_queue_mode

    async def dump(self) -> None:
        if self._task_queue_mode != JobProcessorQueueStateMode.NONE:
            await self._dump_topic(topic=task_repositories.Topic.TASK_JOB)
            await self._dump_topic(topic=task_repositories.Topic.FAILED_TASK_JOB)

        if self._trigger_queue_mode != JobProcessorQueueStateMode.NONE:
            await self._dump_topic(topic=task_repositories.Topic.TRIGGER_JOB)
            await self._dump_topic(topic=task_repositories.Topic.FAILED_TRIGGER_JOB)

        if self._event_queue_mode != JobProcessorQueueStateMode.NONE:
            await self._dump_topic(topic=task_repositories.Topic.EVENT_JOB)
            await self._dump_topic(topic=task_repositories.Topic.FAILED_EVENT_JOB)

    async def load(self):
        await self._load_job_topics(
            queue_mode=self._task_queue_mode,
            topic=task_repositories.Topic.TASK_JOB,
            failed_topic=task_repositories.Topic.FAILED_TASK_JOB,
            model=task_jobs.TaskJob,
        )

        await self._load_job_topics(
            queue_mode=self._trigger_queue_mode,
            topic=task_repositories.Topic.TRIGGER_JOB,
            failed_topic=task_repositories.Topic.FAILED_TRIGGER_JOB,
            model=task_jobs.TriggerJob,
        )

        await self._load_job_topics(
            queue_mode=self._event_queue_mode,
            topic=task_repositories.Topic.EVENT_JOB,
            failed_topic=task_repositories.Topic.FAILED_EVENT_JOB,
            model=task_jobs.EventJob,
        )

    def _get_default_state_path(self, topic: task_repositories.Topic) -> str:
        return f"topics/{topic.value}"

    async def _dump_topic(
        self,
        topic: task_repositories.Topic,
        state_path: str | None = None,
    ) -> None:
        state_path = state_path or self._get_default_state_path(topic)

        logger.info("Dumping Topic(%s) to State(%s)", topic, state_path)
        await self._queue_repository.close_topic(topic)

        jobs: list[json_utils.JsonSerializableDict] = []
        while not self._queue_repository.is_topic_finished(topic):

            async with self._queue_repository.acquire(topic) as job:
                jobs.append(job.dump())
                await self._queue_repository.consume(topic, job)

        if len(jobs) == 0:
            return

        await self._state_repository.set(state_path, {"jobs": jobs})
        logger.info("%s jobs dumped to Topic(%s)", len(jobs), topic)

    async def _load_job_topics(
        self,
        queue_mode: JobProcessorQueueStateMode,
        topic: task_repositories.Topic,
        failed_topic: task_repositories.Topic,
        model: type[task_jobs.BaseJob],
    ):
        if queue_mode == JobProcessorQueueStateMode.PRESERVE:
            await self._load_topic(topic=topic, model=model)
            await self._load_topic(topic=failed_topic, model=model)
        elif queue_mode == JobProcessorQueueStateMode.RESTART:
            await self._load_topic(topic=topic, model=model, reset_retry_count=True)
            await self._load_topic(topic=failed_topic, model=model)
        elif queue_mode == JobProcessorQueueStateMode.RESTART_ALL:
            await self._load_topic(topic=topic, model=model, reset_retry_count=True)
            await self._load_topic(
                topic=topic,
                model=model,
                reset_retry_count=True,
                state_path=self._get_default_state_path(topic=failed_topic),
            )

    async def _load_topic(
        self,
        topic: task_repositories.Topic,
        model: type[task_jobs.BaseJob],
        state_path: str | None = None,
        reset_retry_count: bool = False,
    ) -> None:
        state_path = state_path or self._get_default_state_path(topic)

        logger.info("Loading Topic(%s) from State(%s)", topic, state_path)

        state = await self._state_repository.get(state_path)
        if state is None:
            return

        assert isinstance(state, dict)
        assert "jobs" in state

        raw_jobs = state["jobs"]
        assert isinstance(raw_jobs, list)

        for raw_job in raw_jobs:
            assert isinstance(raw_job, dict)
            job = model.load(raw_job, reset_retry_count=reset_retry_count)
            await self._queue_repository.push(topic=topic, item=job)

        logger.info("%s jobs loaded to Topic(%s)", len(raw_jobs), topic)


__all__ = [
    "JobProcessorQueueStateMode",
    "QueueStateService",
]

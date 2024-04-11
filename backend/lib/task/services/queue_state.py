import enum
import logging

import lib.task.jobs as task_jobs
import lib.task.repositories as task_repositories
import lib.utils.json as json_utils


class JobProcessorQueueStateMode(str, enum.Enum):
    PRESERVE = "preserve"
    RESTART = "restart"
    IGNORE = "ignore"


logger = logging.getLogger(__name__)


class QueueStateService:
    def __init__(
        self,
        queue_repository: task_repositories.QueueRepositoryProtocol,
        state_repository: task_repositories.StateRepositoryProtocol,
        job_topic: task_repositories.JobTopic,
        failed_job_topic: task_repositories.JobTopic,
        job_model: type[task_jobs.BaseJob],
        queue_mode: JobProcessorQueueStateMode,
        failed_queue_mode: JobProcessorQueueStateMode,
    ):
        self._queue_repository = queue_repository
        self._state_repository = state_repository

        self._job_topic = job_topic
        self._failed_job_topic = failed_job_topic
        self._job_model = job_model
        self._queue_mode = queue_mode
        self._failed_queue_mode = failed_queue_mode

    async def dump(self) -> None:
        await self._dump_topic(topic=self._job_topic)
        await self._dump_topic(topic=self._failed_job_topic)

    async def load(self):
        if self._queue_mode == JobProcessorQueueStateMode.PRESERVE:
            await self._load_topic(topic=self._job_topic)
        elif self._queue_mode == JobProcessorQueueStateMode.RESTART:
            await self._load_topic(topic=self._job_topic, reset_retry_count=True)
        elif self._queue_mode == JobProcessorQueueStateMode.IGNORE:
            logger.info("Ignoring Topic(%s) state", self._job_topic)

        if self._failed_queue_mode == JobProcessorQueueStateMode.PRESERVE:
            await self._load_topic(topic=self._failed_job_topic)
        elif self._failed_queue_mode == JobProcessorQueueStateMode.RESTART:
            await self._load_topic(
                topic=self._failed_job_topic,
                reset_retry_count=True,
                state_path=self._get_default_state_path(topic=self._job_topic),
            )
        elif self._failed_queue_mode == JobProcessorQueueStateMode.IGNORE:
            logger.info("Ignoring Topic(%s) state", self._failed_job_topic)

    def _get_default_state_path(self, topic: task_repositories.JobTopic) -> str:
        return f"topics/{topic.value}"

    async def _dump_topic(
        self,
        topic: task_repositories.JobTopic,
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
            logger.info("No jobs to dump from Topic(%s)", topic)
            await self._state_repository.clear(state_path)
            return

        await self._state_repository.set(state_path, {"jobs": jobs})
        logger.info("%s jobs dumped from Topic(%s)", len(jobs), topic)

    async def _load_topic(
        self,
        topic: task_repositories.JobTopic,
        state_path: str | None = None,
        reset_retry_count: bool = False,
    ) -> None:
        state_path = state_path or self._get_default_state_path(topic)

        logger.info("Loading Topic(%s) from State(%s)", topic, state_path)

        state = await self._state_repository.get(state_path)
        if state is None:
            logger.info("State(%s) not found", state_path)
            return

        assert isinstance(state, dict)
        assert "jobs" in state

        raw_jobs = state["jobs"]
        assert isinstance(raw_jobs, list)

        for raw_job in raw_jobs:
            assert isinstance(raw_job, dict)
            job = self._job_model.load(raw_job, reset_retry_count=reset_retry_count)
            await self._queue_repository.push(topic=topic, item=job)

        logger.info("%s jobs loaded to Topic(%s)", len(raw_jobs), topic)


__all__ = [
    "JobProcessorQueueStateMode",
    "QueueStateService",
]

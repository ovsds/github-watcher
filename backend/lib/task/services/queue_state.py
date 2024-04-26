import enum
import logging
import typing

import lib.task.jobs as task_jobs
import lib.task.repositories as task_repositories
import lib.utils.json as json_utils
import lib.utils.pydantic as pydantic_utils


class JobProcessorQueueStateMode(str, enum.Enum):
    LOAD = "load"
    LOAD_RESTART = "load_restart"
    ACCUMULATE = "accumulate"
    IGNORE = "ignore"


logger = logging.getLogger(__name__)


class TopicState(pydantic_utils.BaseModel):
    jobs: list[task_jobs.BaseJob]

    def to_raw(self) -> json_utils.JsonSerializableDict:
        return {"jobs": [job.to_raw() for job in self.jobs]}

    @classmethod
    def from_raw(
        cls,
        raw: json_utils.JsonSerializableDict | None,
        job_model: type[task_jobs.BaseJob],
        reset_retry_count: bool = False,
    ) -> typing.Self:
        if raw is None:
            return cls(jobs=[])

        assert "jobs" in raw
        assert isinstance(raw["jobs"], list)

        jobs: list[task_jobs.BaseJob] = []

        for raw_job in raw["jobs"]:
            assert isinstance(raw_job, dict)
            job = job_model.from_raw(raw_job, reset_retry_count=reset_retry_count)
            jobs.append(job)

        return cls(jobs=jobs)


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
        if self._queue_mode == JobProcessorQueueStateMode.IGNORE:
            logger.info("Ignoring Topic(%s) state", self._job_topic)
        else:
            await self._dump_topic(
                topic=self._job_topic,
                preserve_previous_state=self._queue_mode == JobProcessorQueueStateMode.ACCUMULATE,
            )

        if self._failed_queue_mode == JobProcessorQueueStateMode.IGNORE:
            logger.info("Ignoring Topic(%s) state", self._failed_job_topic)
        else:
            await self._dump_topic(
                topic=self._failed_job_topic,
                preserve_previous_state=self._queue_mode == JobProcessorQueueStateMode.ACCUMULATE,
            )

    async def load(self):
        if self._queue_mode == JobProcessorQueueStateMode.LOAD:
            await self._load_topic(topic=self._job_topic)
        elif self._queue_mode == JobProcessorQueueStateMode.LOAD_RESTART:
            await self._load_topic(topic=self._job_topic, reset_retry_count=True)
        else:
            logger.info("Ignoring Topic(%s) state", self._job_topic)

        if self._failed_queue_mode == JobProcessorQueueStateMode.LOAD:
            await self._load_topic(topic=self._failed_job_topic)
        if self._failed_queue_mode == JobProcessorQueueStateMode.LOAD_RESTART:
            await self._load_topic(
                topic=self._failed_job_topic,
                reset_retry_count=True,
                state_path=self._get_default_state_path(topic=self._job_topic),
            )
        else:
            logger.info("Ignoring Topic(%s) state", self._failed_job_topic)

    def _get_default_state_path(self, topic: task_repositories.JobTopic) -> str:
        return f"topics/{topic.value}"

    async def _dump_topic(
        self,
        topic: task_repositories.JobTopic,
        state_path: str | None = None,
        preserve_previous_state: bool = False,
    ) -> None:
        state_path = state_path or self._get_default_state_path(topic)

        logger.info("Dumping Topic(%s) to State(%s)", topic, state_path)
        await self._queue_repository.close_topic(topic)

        jobs: list[task_jobs.BaseJob] = []
        while not self._queue_repository.is_topic_finished(topic):
            async with self._queue_repository.acquire(topic) as job:
                assert isinstance(job, self._job_model)
                jobs.append(job)
                await self._queue_repository.consume(topic, job)

        if len(jobs) == 0:
            logger.info("No jobs to dump from Topic(%s)", topic)
            if not preserve_previous_state:
                await self._state_repository.clear(state_path)
            return

        async with self._state_repository.acquire(state_path) as raw_state:
            state = TopicState.from_raw(raw=raw_state, job_model=self._job_model)

            if not preserve_previous_state:
                state.jobs = []
            state.jobs.extend(jobs)

            await self._state_repository.set(state_path, state.to_raw())
            logger.info("%s jobs dumped from Topic(%s)", len(jobs), topic)

    async def _load_topic(
        self,
        topic: task_repositories.JobTopic,
        state_path: str | None = None,
        reset_retry_count: bool = False,
    ) -> None:
        state_path = state_path or self._get_default_state_path(topic)

        logger.info("Loading Topic(%s) from State(%s)", topic, state_path)

        raw_state = await self._state_repository.get(state_path)
        if raw_state is None:
            logger.info("State(%s) not found", state_path)
            return

        state = TopicState.from_raw(raw=raw_state, job_model=self._job_model, reset_retry_count=reset_retry_count)
        for job in state.jobs:
            await self._queue_repository.push(topic, job)

        logger.info("%s jobs loaded to Topic(%s)", len(state.jobs), topic)


__all__ = [
    "JobProcessorQueueStateMode",
    "QueueStateService",
]

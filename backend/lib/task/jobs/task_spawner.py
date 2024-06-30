import datetime
import enum
import logging
import typing

import lib.task.base as task_base
import lib.task.jobs.models as task_jobs_models
import lib.task.protocols as task_protocols
import lib.task.repositories as task_repositories
import lib.utils.aiojobs as aiojobs_utils
import lib.utils.json as json_utils
import lib.utils.pydantic as pydantic_utils

logger = logging.getLogger(__name__)

DELAY_TIMEOUT = 5
RETRY_TIMEOUT = 5


class SpawnResult(enum.Enum):
    SPAWNED = "spawned"
    WAITING = "waiting"
    EXHAUSTED = "exhausted"


class CronTaskState(pydantic_utils.BaseModel):
    last_run: datetime.datetime | None = None

    @classmethod
    def from_raw(cls, raw: json_utils.JsonSerializableDict | None) -> typing.Self:
        if raw is None:
            return cls()

        return cls.model_validate(raw)

    def to_raw(self) -> json_utils.JsonSerializableDict:
        return self.model_dump(mode="json")


class TaskSpawnerJob(aiojobs_utils.RepeatableJob):
    def __init__(
        self,
        config_repository: task_repositories.ConfigRepositoryProtocol,
        queue_repository: task_repositories.QueueRepositoryProtocol,
        state_repository: task_protocols.StateRepositoryProtocol,
    ) -> None:
        self._config_repository = config_repository
        self._queue_repository = queue_repository
        self._state_repository = state_repository

        self._already_spawned_once_per_run_ids: set[str] = set()

        super().__init__(
            logger=logger,
            retry_timeout=RETRY_TIMEOUT,
            delay_timeout=DELAY_TIMEOUT,
        )

    async def _process(self) -> None:
        config = await self._config_repository.get_config()

        exhausted = True

        for task in config.tasks:
            if isinstance(task, task_base.OncePerRunTaskConfig):
                result = await self._process_once_per_run_task(task)
            elif isinstance(task, task_base.CronTaskConfig):
                result = await self._process_cron_task(task)
            else:
                raise ValueError(f"Unknown task type: {task}")

            exhausted &= result == SpawnResult.EXHAUSTED

        if exhausted:
            logger.info("All tasks have been exhausted, closing task topic")
            await self._queue_repository.close_topic(task_repositories.JobTopic.TASK)
            self.finish()

    async def _process_once_per_run_task(self, task: task_base.OncePerRunTaskConfig) -> SpawnResult:
        if task.id in self._already_spawned_once_per_run_ids:
            return SpawnResult.EXHAUSTED

        await self._process_task(task)
        self._already_spawned_once_per_run_ids.add(task.id)
        return SpawnResult.SPAWNED

    async def _process_cron_task(self, task: task_base.CronTaskConfig) -> SpawnResult:
        state_path = f"tasks/{task.id}/state"

        async with self._state_repository.acquire(state_path) as raw_state:
            state = CronTaskState.from_raw(raw_state)

            if not task.is_ready(state.last_run):
                logger.debug("Task(%s) is not ready to run", task.id)
                return SpawnResult.WAITING

            await self._process_task(task)
            state.last_run = datetime.datetime.now()
            await self._state_repository.set(state_path, state.to_raw())
            return SpawnResult.SPAWNED

    async def _process_task(self, task: task_base.BaseTaskConfig) -> None:
        task_job = task_jobs_models.TaskJob(
            id=task.id,
            task=task,
        )
        await self._queue_repository.push(
            topic=task_repositories.JobTopic.TASK,
            item=task_job,
        )


__all__ = [
    "TaskSpawnerJob",
]

import logging

import lib.task.jobs.models as task_jobs_models
import lib.task.repositories as task_repositories
import lib.utils.aiojobs as aiojobs_utils

logger = logging.getLogger(__name__)

MAX_RETRIES = 0
RETRY_TIMEOUT = 1


class TaskSpawnerJob(aiojobs_utils.OneShotJob):
    def __init__(
        self,
        config_repository: task_repositories.ConfigRepositoryProtocol,
        queue_repository: task_repositories.QueueRepositoryProtocol,
    ) -> None:
        self._config_repository = config_repository
        self._queue_repository = queue_repository

        super().__init__(
            logger=logger,
            retry_timeout=RETRY_TIMEOUT,
            max_retries=MAX_RETRIES,
        )

    async def _process(self) -> None:
        config = await self._config_repository.get_config()

        for task in config.tasks:
            await self._queue_repository.push(
                topic=task_repositories.JobTopic.TASK,
                item=task_jobs_models.TaskJob(
                    id=task.id,
                    task=task,
                ),
            )

            logger.debug("Task(%s) was spawned", task.id)

        logger.debug("All tasks have been spawned, closing task topic")
        await self._queue_repository.close_topic(task_repositories.JobTopic.TASK)


__all__ = [
    "TaskSpawnerJob",
]

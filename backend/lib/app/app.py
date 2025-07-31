import asyncio
import dataclasses
import logging
import typing

import lib.app.errors as app_errors
import lib.app.settings as app_settings
import lib.task.jobs as task_jobs
import lib.task.repositories as task_repositories
import lib.task.services as task_services
import lib.utils.aiojobs as aiojobs_utils
import lib.utils.asyncio as asyncio_utils
import lib.utils.lifecycle as lifecycle_utils
import lib.utils.logging as logging_utils

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class Application:
    lifecycle: lifecycle_utils.Lifecycle

    @classmethod
    def from_settings(cls, settings: app_settings.Settings) -> typing.Self:
        log_level = "DEBUG" if settings.app.is_debug else settings.logs.level
        logging_config = logging_utils.create_config(
            log_level=log_level,
            log_format=settings.logs.format,
            loggers={
                "asyncio": logging_utils.LoggerConfig(
                    propagate=False,
                    level=log_level,
                ),
            },
        )
        logging_utils.initialize(config=logging_config)
        logger.info("Logging has been initialized with config: %s", logging_config)

        logger.info("Initializing application")

        lifecycle_main_tasks: list[asyncio.Task[typing.Any]] = []
        lifecycle_startup_callbacks: list[lifecycle_utils.Callback] = []
        lifecycle_shutdown_callbacks: list[lifecycle_utils.Callback] = []

        logger.info("Initializing global dependencies")

        aiojobs_scheduler = aiojobs_utils.Scheduler.from_settings(
            settings=settings.tasks.scheduler.aiojobs_scheduler_settings
        )
        lifecycle_startup_callbacks.append(
            lifecycle_utils.Callback(
                awaitable=aiojobs_scheduler.spawn_deferred_jobs(),
                error_message="Failed to spawn deferred jobs",
                success_message="Deferred jobs have been spawned successfully",
            )
        )
        lifecycle_shutdown_callbacks.append(
            lifecycle_utils.Callback.from_dispose(
                name="aiojobs_scheduler",
                awaitable=aiojobs_scheduler.dispose(),
            )
        )

        logger.info("Initializing clients")

        logger.info("Initializing repositories")

        config_repository = task_repositories.config_repository_factory(settings.tasks.config_backend)
        lifecycle_shutdown_callbacks.append(
            lifecycle_utils.Callback.from_dispose(
                name="config_repository",
                awaitable=config_repository.dispose(),
            )
        )
        logger.info("Config repository has been initialized with type(%s)", settings.tasks.config_backend.type_name)
        queue_repository = task_repositories.queue_repository_factory(settings.tasks.queue_backend)
        lifecycle_shutdown_callbacks.append(
            lifecycle_utils.Callback.from_dispose(
                name="queue_repository",
                awaitable=queue_repository.dispose(),
            )
        )
        logger.info("Queue repository has been initialized with type(%s)", settings.tasks.queue_backend.type_name)
        state_repository = task_repositories.state_repository_factory(settings.tasks.state_backend)
        lifecycle_shutdown_callbacks.append(
            lifecycle_utils.Callback.from_dispose(
                name="state_repository",
                awaitable=state_repository.dispose(),
            )
        )
        logger.info("State repository has been initialized with type(%s)", settings.tasks.state_backend.type_name)

        logger.info("Initializing services")
        task_queue_state_service = task_services.QueueStateService(
            queue_repository=queue_repository,
            state_repository=state_repository,
            job_topic=task_repositories.JobTopic.TASK,
            failed_job_topic=task_repositories.JobTopic.FAILED_TASK,
            job_model=task_jobs.TaskJob,
            queue_mode=settings.tasks.task_processor.queue_state_mode,
            failed_queue_mode=settings.tasks.task_processor.failed_queue_state_mode,
        )
        lifecycle_startup_callbacks.append(
            lifecycle_utils.Callback(
                awaitable=task_queue_state_service.load(),
                error_message="Failed to load Task JobTopic state",
                success_message="Task JobTopic state have been loaded successfully",
            )
        )
        lifecycle_shutdown_callbacks.append(
            lifecycle_utils.Callback.from_dispose(
                name="task_queue_state_service",
                awaitable=task_queue_state_service.dump(),
            )
        )
        trigger_queue_state_service = task_services.QueueStateService(
            queue_repository=queue_repository,
            state_repository=state_repository,
            job_topic=task_repositories.JobTopic.TRIGGER,
            failed_job_topic=task_repositories.JobTopic.FAILED_TRIGGER,
            job_model=task_jobs.TriggerJob,
            queue_mode=settings.tasks.trigger_processor.queue_state_mode,
            failed_queue_mode=settings.tasks.trigger_processor.failed_queue_state_mode,
        )
        lifecycle_startup_callbacks.append(
            lifecycle_utils.Callback(
                awaitable=trigger_queue_state_service.load(),
                error_message="Failed to load Trigger JobTopic state",
                success_message="Trigger JobTopic state have been loaded successfully",
            )
        )
        lifecycle_shutdown_callbacks.append(
            lifecycle_utils.Callback.from_dispose(
                name="trigger_queue_state_service",
                awaitable=trigger_queue_state_service.dump(),
            )
        )
        event_queue_state_service = task_services.QueueStateService(
            queue_repository=queue_repository,
            state_repository=state_repository,
            job_topic=task_repositories.JobTopic.EVENT,
            failed_job_topic=task_repositories.JobTopic.FAILED_EVENT,
            job_model=task_jobs.EventJob,
            queue_mode=settings.tasks.event_processor.queue_state_mode,
            failed_queue_mode=settings.tasks.event_processor.failed_queue_state_mode,
        )
        lifecycle_startup_callbacks.append(
            lifecycle_utils.Callback(
                awaitable=event_queue_state_service.load(),
                error_message="Failed to load Event JobTopic state",
                success_message="Event JobTopic state have been loaded successfully",
            )
        )
        lifecycle_shutdown_callbacks.append(
            lifecycle_utils.Callback.from_dispose(
                name="event_queue_state_service",
                awaitable=event_queue_state_service.dump(),
            )
        )

        logger.info("Initializing jobs")

        aiojobs_scheduler.defer_jobs(
            task_jobs.TaskSpawnerJob(
                config_repository=config_repository,
                queue_repository=queue_repository,
                state_repository=state_repository,
            ),
            *(
                task_jobs.TaskProcessorJob(
                    job_id=job_id,
                    max_retries=settings.tasks.task_processor.max_retries,
                    queue_repository=queue_repository,
                )
                for job_id in range(settings.tasks.task_processor.count)
            ),
            *(
                task_jobs.TriggerProcessorJob(
                    job_id=job_id,
                    max_retries=settings.tasks.trigger_processor.max_retries,
                    queue_repository=queue_repository,
                    state_repository=state_repository,
                )
                for job_id in range(settings.tasks.trigger_processor.count)
            ),
            *(
                task_jobs.EventProcessorJob(
                    job_id=job_id,
                    max_retries=settings.tasks.event_processor.max_retries,
                    queue_repository=queue_repository,
                )
                for job_id in range(settings.tasks.event_processor.count)
            ),
        )

        logger.info("Initializing lifecycle manager")

        async def _start() -> None:
            timer = asyncio_utils.TimeoutTimer(timeout=settings.tasks.scheduler.timeout)

            while not timer.is_expired:
                all_topics_finished = all(
                    queue_repository.is_topic_finished(topic) for topic in task_repositories.JOB_TOPICS
                )
                if aiojobs_scheduler.is_empty and all_topics_finished:
                    break
                await asyncio.sleep(1)
            else:
                logger.warning("Application has timed out and will be stopped prematurely")
                raise app_errors.ApplicationTimeoutError("Application has timed out")

            logger.info("Application has finished successfully")
            failed_topics_empty = all(
                queue_repository.is_topic_empty(topic) for topic in task_repositories.FAILED_JOB_TOPICS
            )
            if not failed_topics_empty:
                logger.warning("Application has finished with failed jobs")
                raise app_errors.ApplicationFailedJobsError("Application has finished with failed jobs")

        lifecycle_main_tasks.append(asyncio.create_task(_start()))

        lifecycle = lifecycle_utils.Lifecycle(
            logger=logger,
            main_tasks=lifecycle_main_tasks,
            startup_callbacks=lifecycle_startup_callbacks,
            shutdown_callbacks=list(reversed(lifecycle_shutdown_callbacks)),
        )

        logger.info("Creating application")
        application = cls(
            lifecycle=lifecycle,
        )

        logger.info("Initializing application finished")

        return application

    async def start(self) -> None:
        try:
            await self.lifecycle.on_startup()
        except lifecycle_utils.Lifecycle.StartupError as start_error:
            logger.error("Application has failed to start")
            raise app_errors.ServerStartError("Application has failed to start, see logs above") from start_error

        logger.info("Application is starting")
        try:
            await self.lifecycle.run()
        except asyncio.CancelledError:
            logger.info("Application has been interrupted")
        except BaseException as unexpected_error:
            logger.exception("Application runtime error")
            raise app_errors.ServerRuntimeError("Application runtime error") from unexpected_error

    async def dispose(self) -> None:
        logger.info("Application is shutting down...")

        try:
            await self.lifecycle.on_shutdown()
        except lifecycle_utils.Lifecycle.ShutdownError as dispose_error:
            logger.error("Application has shut down with errors")
            raise app_errors.DisposeError("Application has shut down with errors, see logs above") from dispose_error

        logger.info("Application has successfully shut down")


__all__ = [
    "Application",
]

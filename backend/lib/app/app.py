import asyncio
import logging
import typing

import lib.app.errors as app_errors
import lib.app.settings as app_settings
import lib.task.jobs as task_jobs
import lib.task.repositories as task_repositories
import lib.task.services as task_services
import lib.utils.aiojobs as aiojobs_utils
import lib.utils.asyncio as asyncio_utils
import lib.utils.lifecycle_manager as lifecycle_manager_utils
import lib.utils.logging as logging_utils

logger = logging.getLogger(__name__)


class Application:
    def __init__(
        self,
        settings: app_settings.Settings,
        lifecycle_manager: lifecycle_manager_utils.LifecycleManager,
        aiojobs_scheduler: aiojobs_utils.Scheduler,
        queue_repository: task_repositories.queue.base.QueueRepositoryProtocol,
    ) -> None:
        self._settings = settings
        self._lifecycle_manager = lifecycle_manager
        self._aiojobs_scheduler = aiojobs_scheduler
        self._queue_repository = queue_repository

    @classmethod
    def from_settings(cls, settings: app_settings.Settings) -> typing.Self:
        # Logging

        logging_utils.initialize(
            config=logging_utils.create_config(
                log_level=settings.logs.level,
                log_format=settings.logs.format,
                loggers={
                    "asyncio": logging_utils.LoggerConfig(
                        propagate=False,
                        level=settings.logs.level,
                    ),
                    "gql.transport.aiohttp": logging_utils.LoggerConfig(
                        propagate=False,
                        level=settings.logs.level if settings.app.debug else "WARNING",
                    ),
                },
            ),
        )

        logger.info("Initializing application")

        aiojobs_scheduler = aiojobs_utils.Scheduler.from_settings(
            settings=settings.tasks.scheduler.aiojobs_scheduler_settings
        )

        # Clients

        logger.info("Initializing clients")

        # Repositories

        logger.info("Initializing repositories")

        config_repository = task_repositories.config_repository_factory(settings.tasks.config_backend)
        logger.info("Config repository has been initialized with type(%s)", settings.tasks.config_backend.type)
        queue_repository = task_repositories.queue_repository_factory(settings.tasks.queue_backend)
        logger.info("Queue repository has been initialized with type(%s)", settings.tasks.queue_backend.type)
        state_repository = task_repositories.state_repository_factory(settings.tasks.state_backend)
        logger.info("State repository has been initialized with type(%s)", settings.tasks.state_backend.type)

        # Services

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
        trigger_queue_state_service = task_services.QueueStateService(
            queue_repository=queue_repository,
            state_repository=state_repository,
            job_topic=task_repositories.JobTopic.TRIGGER,
            failed_job_topic=task_repositories.JobTopic.FAILED_TRIGGER,
            job_model=task_jobs.TriggerJob,
            queue_mode=settings.tasks.trigger_processor.queue_state_mode,
            failed_queue_mode=settings.tasks.trigger_processor.failed_queue_state_mode,
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

        # Jobs

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

        lifecycle_manager = lifecycle_manager_utils.LifecycleManager(logger=logger)

        # Startup
        lifecycle_manager.add_startup_callback(
            callback=lifecycle_manager_utils.StartupCallback(
                callback=task_queue_state_service.load(),
                error_message="Failed to load Task JobTopic state",
                success_message="Task JobTopic state have been loaded successfully",
            )
        )
        lifecycle_manager.add_startup_callback(
            callback=lifecycle_manager_utils.StartupCallback(
                callback=trigger_queue_state_service.load(),
                error_message="Failed to load Trigger JobTopic state",
                success_message="Trigger JobTopic state have been loaded successfully",
            )
        )
        lifecycle_manager.add_startup_callback(
            callback=lifecycle_manager_utils.StartupCallback(
                callback=event_queue_state_service.load(),
                error_message="Failed to load Event JobTopic state",
                success_message="Event JobTopic state have been loaded successfully",
            )
        )

        lifecycle_manager.add_startup_callback(
            callback=lifecycle_manager_utils.StartupCallback(
                callback=aiojobs_scheduler.spawn_deferred_jobs(),
                error_message="Failed to spawn deferred jobs",
                success_message="Deferred jobs have been spawned",
            )
        )
        # Shutdown
        lifecycle_manager.add_shutdown_callback(
            callback=lifecycle_manager_utils.ShutdownCallback.from_disposable_resource(
                name="aiojobs_scheduler",
                dispose_callback=aiojobs_scheduler.dispose(),
            )
        )
        lifecycle_manager.add_shutdown_callback(
            callback=lifecycle_manager_utils.ShutdownCallback(
                callback=task_queue_state_service.dump(),
                error_message="Failed to dump job topic state",
                success_message="Topic jobs state have been dumped successfully",
            )
        )
        lifecycle_manager.add_shutdown_callback(
            callback=lifecycle_manager_utils.ShutdownCallback(
                callback=trigger_queue_state_service.dump(),
                error_message="Failed to dump trigger topic state",
                success_message="Trigger jobs state have been dumped successfully",
            )
        )
        lifecycle_manager.add_shutdown_callback(
            callback=lifecycle_manager_utils.ShutdownCallback(
                callback=event_queue_state_service.dump(),
                error_message="Failed to dump event topic state",
                success_message="Event jobs state have been dumped successfully",
            )
        )
        lifecycle_manager.add_shutdown_callback(
            callback=lifecycle_manager_utils.ShutdownCallback.from_disposable_resource(
                name="config_repository",
                dispose_callback=config_repository.dispose(),
            )
        )
        lifecycle_manager.add_shutdown_callback(
            callback=lifecycle_manager_utils.ShutdownCallback.from_disposable_resource(
                name="queue_repository",
                dispose_callback=queue_repository.dispose(),
            )
        )
        lifecycle_manager.add_shutdown_callback(
            callback=lifecycle_manager_utils.ShutdownCallback.from_disposable_resource(
                name="state_repository",
                dispose_callback=state_repository.dispose(),
            )
        )

        logger.info("Creating application")
        application = cls(
            settings=settings,
            lifecycle_manager=lifecycle_manager,
            aiojobs_scheduler=aiojobs_scheduler,
            queue_repository=queue_repository,
        )

        logger.info("Initializing application finished")

        return application

    async def start(self) -> None:
        try:
            await self._lifecycle_manager.on_startup()
        except lifecycle_manager_utils.LifecycleManager.StartupError as start_error:
            logger.error("Application has failed to start")
            raise app_errors.ServerStartError("Application has failed to start, see logs above") from start_error

        logger.info("Application is starting")
        try:
            await self._start()
        except asyncio.CancelledError:
            logger.info("Application has been interrupted")
        except BaseException as unexpected_error:
            logger.exception("Application runtime error")
            raise app_errors.ServerRuntimeError("Application runtime error") from unexpected_error

    async def _start(self) -> None:
        timer = asyncio_utils.TimeoutTimer(timeout=self._settings.tasks.scheduler.timeout)

        while not timer.is_expired:
            all_topics_finished = all(
                self._queue_repository.is_topic_finished(topic) for topic in task_repositories.JOB_TOPICS
            )
            if self._aiojobs_scheduler.is_empty and all_topics_finished:
                break
            await asyncio.sleep(1)
        else:
            logger.warning("Application has timed out and will be stopped prematurely")
            raise app_errors.ApplicationTimeoutError("Application has timed out")

        logger.info("Application has finished successfully")
        failed_topics_empty = all(
            self._queue_repository.is_topic_empty(topic) for topic in task_repositories.FAILED_JOB_TOPICS
        )
        if not failed_topics_empty:
            logger.warning("Application has finished with failed jobs")
            raise app_errors.ApplicationFailedJobsError("Application has finished with failed jobs")

    async def dispose(self) -> None:
        logger.info("Application is shutting down...")

        try:
            await self._lifecycle_manager.on_shutdown()
        except lifecycle_manager_utils.LifecycleManager.ShutdownError as dispose_error:
            logger.error("Application has shut down with errors")
            raise app_errors.DisposeError("Application has shut down with errors, see logs above") from dispose_error

        logger.info("Application has successfully shut down")


__all__ = [
    "Application",
]

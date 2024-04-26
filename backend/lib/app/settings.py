import os
import typing
import warnings

import pydantic
import pydantic_settings

import lib.task.repositories as task_repositories
import lib.task.services as task_services
import lib.utils.aiojobs as aiojobs_utils
import lib.utils.logging as logging_utils


class AppSettings(pydantic_settings.BaseSettings):
    env: str = "production"
    debug: bool = False

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_debug(self) -> bool:
        if not self.is_development:
            warnings.warn("APP_DEBUG is True in non-development environment", UserWarning)

        return self.debug


class LoggingSettings(pydantic_settings.BaseSettings):
    level: logging_utils.LogLevel = "INFO"
    format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"


class SchedulerSettings(pydantic_settings.BaseSettings):
    limit: int = 100
    pending_limit: int = 0  # 0 means no limit
    timeout: int = 10 * 60  # 10 minutes, 0 means no timeout
    close_timeout: int = 10

    @property
    def aiojobs_scheduler_settings(self) -> aiojobs_utils.Settings:
        return aiojobs_utils.Settings(
            limit=self.limit,
            pending_limit=self.pending_limit,
            close_timeout=self.close_timeout,
        )


class JobProcessorSettings(pydantic_settings.BaseSettings):
    count: int = 5
    max_retries: int = 3
    queue_state_mode: task_services.JobProcessorQueueStateMode = pydantic.Field(
        default=task_services.JobProcessorQueueStateMode.LOAD
    )
    failed_queue_state_mode: task_services.JobProcessorQueueStateMode = pydantic.Field(
        default=task_services.JobProcessorQueueStateMode.ACCUMULATE
    )


class TasksSettings(pydantic_settings.BaseSettings):
    config_backend: typing.Annotated[
        task_repositories.BaseConfigSettings,
        pydantic.BeforeValidator(task_repositories.BaseConfigSettings.factory),
    ] = NotImplemented
    queue_backend: typing.Annotated[
        task_repositories.BaseQueueSettings,
        pydantic.BeforeValidator(task_repositories.BaseQueueSettings.factory),
    ] = NotImplemented
    state_backend: typing.Annotated[
        task_repositories.BaseStateSettings,
        pydantic.BeforeValidator(task_repositories.BaseStateSettings.factory),
    ] = NotImplemented

    scheduler: SchedulerSettings = pydantic.Field(default_factory=SchedulerSettings)
    task_processor: JobProcessorSettings = pydantic.Field(default_factory=JobProcessorSettings)
    trigger_processor: JobProcessorSettings = pydantic.Field(default_factory=JobProcessorSettings)
    event_processor: JobProcessorSettings = pydantic.Field(default_factory=JobProcessorSettings)


class Settings(pydantic_settings.BaseSettings):
    app: AppSettings = pydantic.Field(default_factory=AppSettings)
    logs: LoggingSettings = pydantic.Field(default_factory=LoggingSettings)
    tasks: TasksSettings = pydantic.Field(default_factory=TasksSettings)

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="GITHUB_WATCHER_",
        env_nested_delimiter="__",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[pydantic_settings.BaseSettings],
        init_settings: pydantic_settings.PydanticBaseSettingsSource,
        env_settings: pydantic_settings.PydanticBaseSettingsSource,
        dotenv_settings: pydantic_settings.PydanticBaseSettingsSource,
        file_secret_settings: pydantic_settings.PydanticBaseSettingsSource,
    ) -> tuple[pydantic_settings.PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            pydantic_settings.YamlConfigSettingsSource(
                settings_cls,
                yaml_file=os.environ.get("GITHUB_WATCHER_SETTINGS_YAML", None),
            ),
        )


__all__ = [
    "AppSettings",
    "JobProcessorSettings",
    "LoggingSettings",
    "Settings",
    "TasksSettings",
]

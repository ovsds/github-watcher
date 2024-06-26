import dataclasses
import datetime
import typing
import warnings

import cron_converter
import pydantic

import lib.task.base.action as action_base
import lib.task.base.trigger as trigger_base
import lib.utils.pydantic as pydantic_utils


class BaseTaskConfig(pydantic_utils.BaseModel, pydantic_utils.IDMixinModel):
    triggers: trigger_base.TriggerConfigListPydanticAnnotation
    actions: action_base.ActionConfigListPydanticAnnotation

    @classmethod
    def factory(cls, v: typing.Any, info: pydantic.ValidationInfo) -> "BaseTaskConfig":
        return task_config_factory(v)


class OncePerRunTaskConfig(BaseTaskConfig):
    type: str = "once_per_run"


class CronTaskConfig(BaseTaskConfig):
    type: str = "cron"
    cron: str

    def is_ready(self, last_run: datetime.datetime | None) -> bool:
        if last_run is None:
            return True

        cron = cron_converter.Cron(cron_string=self.cron)
        schedule = cron.schedule(start_date=last_run)

        return schedule.next() <= datetime.datetime.now(tz=last_run.tzinfo)


ConfigT = typing.TypeVar("ConfigT", bound=BaseTaskConfig)


@dataclasses.dataclass
class RegistryRecord(typing.Generic[ConfigT]):
    config_class: type[ConfigT]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {
    "once_per_run": RegistryRecord(config_class=OncePerRunTaskConfig),
    "cron": RegistryRecord(config_class=CronTaskConfig),
}

TaskConfigPydanticAnnotation = typing.Annotated[
    pydantic.SerializeAsAny[BaseTaskConfig],
    pydantic.BeforeValidator(BaseTaskConfig.factory),
]
TaskConfigListPydanticAnnotation = typing.Annotated[
    list[pydantic.SerializeAsAny[BaseTaskConfig]],
    pydantic.BeforeValidator(pydantic_utils.make_list_factory(BaseTaskConfig.factory)),
    pydantic.AfterValidator(pydantic_utils.check_unique_ids),
]


def task_config_factory(data: typing.Any) -> BaseTaskConfig:
    if isinstance(data, BaseTaskConfig):
        return data

    assert isinstance(data, dict)
    if "type" not in data:
        # TODO 1.0.0: remove
        warnings.warn(
            "Task config should have a 'type' field, using `once_per_run` as default value.\nWill break in 1.0.0.",
            FutureWarning,
        )
        data["type"] = "once_per_run"

    config_class = _REGISTRY[data["type"]].config_class
    return config_class.model_validate(data)


__all__ = [
    "BaseTaskConfig",
    "CronTaskConfig",
    "OncePerRunTaskConfig",
    "TaskConfigListPydanticAnnotation",
    "TaskConfigPydanticAnnotation",
]

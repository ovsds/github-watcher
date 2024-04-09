import typing

import pydantic

import lib.task.base as task_base
import lib.utils.json as json_utils
import lib.utils.pydantic as pydantic_utils


class BaseJob(pydantic_utils.BaseModel, pydantic_utils.IDMixinModel):
    retry_count: int = 0

    @property
    def unique_key(self) -> str:
        return f"{self.id}__{self.retry_count}"

    def copy_retry(self) -> typing.Self:
        return self.model_copy(update={"retry_count": self.retry_count + 1})

    def dump(self) -> json_utils.JsonSerializableDict:
        return self.model_dump(mode="json")

    @classmethod
    def load(cls, value: json_utils.JsonSerializableDict, reset_retry_count: bool = False) -> typing.Self:
        if reset_retry_count:
            value["retry_count"] = 0

        return cls.model_validate(obj=value)


class TaskJob(BaseJob):
    task: task_base.TaskConfig


class TriggerJob(BaseJob):
    task_id: str
    trigger: pydantic.SerializeAsAny[task_base.BaseTriggerConfig]
    actions: list[pydantic.SerializeAsAny[task_base.BaseActionConfig]]


class EventJob(BaseJob):
    event: task_base.Event
    action: pydantic.SerializeAsAny[task_base.BaseActionConfig]


__all__ = [
    "BaseJob",
    "EventJob",
    "TaskJob",
    "TriggerJob",
]

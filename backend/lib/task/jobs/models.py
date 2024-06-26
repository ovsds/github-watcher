import typing

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

    def to_raw(self) -> json_utils.JsonSerializableDict:
        return self.model_dump(mode="json")

    @classmethod
    def from_raw(cls, raw: json_utils.JsonSerializableDict, reset_retry_count: bool = False) -> typing.Self:
        if reset_retry_count:
            raw["retry_count"] = 0

        return cls.model_validate(obj=raw)


class TaskJob(BaseJob):
    task: task_base.TaskConfigPydanticAnnotation


class TriggerJob(BaseJob):
    task_id: str
    trigger: task_base.TriggerConfigPydanticAnnotation
    actions: task_base.ActionConfigListPydanticAnnotation


class EventJob(BaseJob):
    event: task_base.Event
    action: task_base.ActionConfigPydanticAnnotation


__all__ = [
    "BaseJob",
    "EventJob",
    "TaskJob",
    "TriggerJob",
]

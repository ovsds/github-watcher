import lib.task.base.task as task_base
import lib.utils.pydantic as pydantic_utils


class RootConfig(pydantic_utils.BaseModel):
    tasks: pydantic_utils.TypedListAnnotation[task_base.BaseTaskConfig]


__all__ = [
    "RootConfig",
]

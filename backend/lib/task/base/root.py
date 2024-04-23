import lib.task.base.task as task_base
import lib.utils.pydantic as pydantic_utils


class RootConfig(pydantic_utils.BaseModel):
    tasks: task_base.TaskConfigListPydanticAnnotation


__all__ = [
    "RootConfig",
]

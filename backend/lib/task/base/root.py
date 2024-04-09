import typing

import pydantic

import lib.task.base.task as task_base
import lib.utils.pydantic as pydantic_utils


class RootConfig(pydantic_utils.BaseModel):
    tasks: typing.Annotated[
        list[task_base.TaskConfig],
        pydantic.AfterValidator(pydantic_utils.check_unique_ids),
    ]


__all__ = [
    "RootConfig",
]

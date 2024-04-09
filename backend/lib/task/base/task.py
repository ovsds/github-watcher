import typing

import pydantic

import lib.task.base.action as action_base
import lib.task.base.trigger as task_trigger_base
import lib.utils.pydantic as pydantic_utils


class TaskConfig(pydantic_utils.BaseModel, pydantic_utils.IDMixinModel):
    triggers: typing.Annotated[
        list[pydantic.SerializeAsAny[task_trigger_base.BaseTriggerConfig]],
        pydantic.BeforeValidator(pydantic_utils.make_list_factory(task_trigger_base.BaseTriggerConfig.factory)),
        pydantic.AfterValidator(pydantic_utils.check_unique_ids),
    ]
    actions: typing.Annotated[
        list[pydantic.SerializeAsAny[action_base.BaseActionConfig]],
        pydantic.BeforeValidator(pydantic_utils.make_list_factory(action_base.BaseActionConfig.factory)),
        pydantic.AfterValidator(pydantic_utils.check_unique_ids),
    ]


__all__ = [
    "TaskConfig",
]

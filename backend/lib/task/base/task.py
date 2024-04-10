import lib.task.base.action as action_base
import lib.task.base.trigger as trigger_base
import lib.utils.pydantic as pydantic_utils


class TaskConfig(pydantic_utils.BaseModel, pydantic_utils.IDMixinModel):
    triggers: trigger_base.TriggerConfigListPydanticAnnotation
    actions: action_base.ActionConfigListPydanticAnnotation


__all__ = [
    "TaskConfig",
]

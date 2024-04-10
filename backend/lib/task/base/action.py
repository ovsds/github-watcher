import abc
import dataclasses
import typing

import pydantic

import lib.task.base.event as task_configs_event
import lib.utils.pydantic as pydantic_utils


class ActionProcessorProtocol(typing.Protocol):
    async def dispose(self) -> None: ...

    async def process(self, event: task_configs_event.Event) -> None: ...


class BaseActionConfig(pydantic_utils.BaseModel, pydantic_utils.IDMixinModel):
    type: str

    @classmethod
    def factory(cls, v: typing.Any, info: pydantic.ValidationInfo) -> "BaseActionConfig":
        return action_config_factory(v)


ActionConfigPydanticAnnotation = typing.Annotated[
    pydantic.SerializeAsAny[BaseActionConfig],
    pydantic.BeforeValidator(BaseActionConfig.factory),
]
ActionConfigListPydanticAnnotation = typing.Annotated[
    list[pydantic.SerializeAsAny[BaseActionConfig]],
    pydantic.BeforeValidator(pydantic_utils.make_list_factory(BaseActionConfig.factory)),
    pydantic.AfterValidator(pydantic_utils.check_unique_ids),
]


ConfigT = typing.TypeVar("ConfigT", bound=BaseActionConfig)


class ActionProcessor(typing.Generic[ConfigT], abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_config(
        cls,
        config: ConfigT,
    ) -> typing.Self: ...

    async def dispose(self) -> None: ...

    @abc.abstractmethod
    async def process(self, event: task_configs_event.Event) -> None: ...


@dataclasses.dataclass
class RegistryRecord(typing.Generic[ConfigT]):
    config_class: type[ConfigT]
    processor_class: type[ActionProcessor[ConfigT]]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {}


def register_action(
    name: str,
    config_class: type[ConfigT],
    processor_class: type[ActionProcessor[ConfigT]],
) -> None:
    _REGISTRY[name] = RegistryRecord(config_class=config_class, processor_class=processor_class)


def action_config_factory(data: typing.Any) -> BaseActionConfig:
    if isinstance(data, BaseActionConfig):
        return data

    assert isinstance(data, dict)
    assert "type" in data

    config_class = _REGISTRY[data["type"]].config_class
    return config_class.model_validate(data)


def action_processor_factory(
    config: BaseActionConfig,
) -> ActionProcessorProtocol:
    processor_class = _REGISTRY[config.type].processor_class
    return processor_class.from_config(config)


__all__ = [
    "ActionConfigListPydanticAnnotation",
    "ActionConfigPydanticAnnotation",
    "ActionProcessor",
    "ActionProcessorProtocol",
    "BaseActionConfig",
    "action_config_factory",
    "action_processor_factory",
    "register_action",
]

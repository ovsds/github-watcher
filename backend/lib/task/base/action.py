import abc
import dataclasses
import typing

import lib.task.base.event as task_configs_event
import lib.utils.pydantic as pydantic_utils


class ActionProcessorProtocol(typing.Protocol):
    async def dispose(self) -> None: ...

    async def process(self, event: task_configs_event.Event) -> None: ...


class BaseActionConfig(pydantic_utils.IDMixinModel, pydantic_utils.TypedBaseModel):
    @classmethod
    def factory(cls, data: typing.Any) -> "BaseActionConfig":
        return action_config_factory(data)


class BaseActionProcessor[ConfigT: BaseActionConfig](abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_config(
        cls,
        config: ConfigT,
    ) -> typing.Self: ...

    async def dispose(self) -> None: ...

    @abc.abstractmethod
    async def process(self, event: task_configs_event.Event) -> None: ...


@dataclasses.dataclass(frozen=True)
class RegistryRecord[ConfigT: BaseActionConfig]:
    config_class: type[ConfigT]
    processor_class: type[BaseActionProcessor[ConfigT]]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {}


def register_action[ConfigT: BaseActionConfig](
    name: str,
    config_class: type[ConfigT],
    processor_class: type[BaseActionProcessor[ConfigT]],
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
    processor_class = _REGISTRY[config.type_name].processor_class
    return processor_class.from_config(config)


__all__ = [
    "ActionProcessorProtocol",
    "BaseActionConfig",
    "BaseActionProcessor",
    "action_config_factory",
    "action_processor_factory",
    "register_action",
]

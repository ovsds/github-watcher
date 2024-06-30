import abc
import dataclasses
import typing

import pydantic

import lib.task.base as task_base
import lib.task.protocols as task_protocols
import lib.utils.pydantic as pydantic_utils


class TriggerProcessorProtocol(typing.Protocol):
    async def produce_events(self) -> typing.AsyncGenerator[task_base.Event, None]: ...

    async def dispose(self) -> None: ...


class BaseTriggerConfig(pydantic_utils.BaseModel, pydantic_utils.IDMixinModel):
    type: str

    @classmethod
    def factory(cls, v: typing.Any, info: pydantic.ValidationInfo) -> "BaseTriggerConfig":
        return trigger_config_factory(v)


TriggerConfigPydanticAnnotation = typing.Annotated[
    pydantic.SerializeAsAny[BaseTriggerConfig],
    pydantic.BeforeValidator(BaseTriggerConfig.factory),
]
TriggerConfigListPydanticAnnotation = typing.Annotated[
    list[pydantic.SerializeAsAny[BaseTriggerConfig]],
    pydantic.BeforeValidator(pydantic_utils.make_list_factory(BaseTriggerConfig.factory)),
    pydantic.AfterValidator(pydantic_utils.check_unique_ids),
]


ConfigT = typing.TypeVar("ConfigT", bound=BaseTriggerConfig)


class TriggerProcessor(typing.Generic[ConfigT], abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_config(
        cls,
        config: ConfigT,
        state: task_protocols.StateProtocol,
    ) -> typing.Self: ...

    async def produce_events(self) -> typing.AsyncGenerator[task_base.Event, None]: ...

    async def dispose(self) -> None: ...


@dataclasses.dataclass
class RegistryRecord(typing.Generic[ConfigT]):
    config_class: type[ConfigT]
    processor_class: type[TriggerProcessor[ConfigT]]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {}


def register_trigger(
    name: str,
    config_class: type[ConfigT],
    processor_class: type[TriggerProcessor[ConfigT]],
) -> None:
    _REGISTRY[name] = RegistryRecord(config_class=config_class, processor_class=processor_class)


def trigger_config_factory(data: typing.Any) -> BaseTriggerConfig:
    if isinstance(data, BaseTriggerConfig):
        return data

    assert isinstance(data, dict)
    assert "type" in data

    config_class = _REGISTRY[data["type"]].config_class
    return config_class.model_validate(data)


def trigger_processor_factory(
    config: BaseTriggerConfig,
    state: task_protocols.StateProtocol,
) -> TriggerProcessorProtocol:
    processor_class = _REGISTRY[config.type].processor_class
    return processor_class.from_config(config=config, state=state)


__all__ = [
    "BaseTriggerConfig",
    "TriggerConfigListPydanticAnnotation",
    "TriggerConfigPydanticAnnotation",
    "TriggerProcessor",
    "TriggerProcessorProtocol",
    "register_trigger",
    "trigger_config_factory",
    "trigger_processor_factory",
]

import abc
import dataclasses
import typing

import pydantic
import pydantic_settings

import lib.task.base as task_base


class ConfigRepositoryProtocol(typing.Protocol):
    async def dispose(self) -> None: ...

    async def get_config(self) -> task_base.RootConfig: ...


class BaseConfigSettings(pydantic_settings.BaseSettings):
    type: typing.Any

    @classmethod
    def factory(cls, v: typing.Any, info: pydantic.ValidationInfo) -> "BaseConfigSettings":
        return config_settings_factory(v)


SettingsT = typing.TypeVar("SettingsT", bound=BaseConfigSettings)


class BaseConfigRepository(typing.Generic[SettingsT], abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_settings(cls, settings: SettingsT) -> typing.Self: ...

    async def dispose(self) -> None: ...

    @abc.abstractmethod
    async def get_config(self) -> task_base.RootConfig: ...


@dataclasses.dataclass
class RegistryRecord(typing.Generic[SettingsT]):
    settings_class: type[SettingsT]
    repository_class: type[BaseConfigRepository[SettingsT]]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {}


def register_config_backend(
    name: str,
    settings_class: type[SettingsT],
    repository_class: type[BaseConfigRepository[SettingsT]],
) -> None:
    _REGISTRY[name] = RegistryRecord(
        settings_class=settings_class,
        repository_class=repository_class,
    )


def config_settings_factory(data: typing.Any) -> BaseConfigSettings:
    assert isinstance(data, dict), "TaskConfigBackendSettings must be a dict"
    assert "type" in data, "TaskConfigBackendSettings must have a 'type' key"
    assert data["type"] in _REGISTRY, f"Unknown TaskConfigBackendSettings type: {data['type']}"

    settings_class = _REGISTRY[data["type"]].settings_class
    return settings_class.model_validate(data)


def config_repository_factory(settings: BaseConfigSettings) -> ConfigRepositoryProtocol:
    repository_class = _REGISTRY[settings.type].repository_class
    return repository_class.from_settings(settings)


__all__ = [
    "BaseConfigRepository",
    "BaseConfigSettings",
    "ConfigRepositoryProtocol",
    "config_repository_factory",
    "config_settings_factory",
    "register_config_backend",
]

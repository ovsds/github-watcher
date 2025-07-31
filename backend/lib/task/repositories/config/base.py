import abc
import dataclasses
import typing

import lib.task.base as task_base
import lib.utils.pydantic as pydantic_utils


class ConfigRepositoryProtocol(typing.Protocol):
    async def dispose(self) -> None: ...

    async def get_config(self) -> task_base.RootConfig: ...


class BaseConfigSettings(pydantic_utils.TypedBaseModel):
    @classmethod
    def factory(cls, data: typing.Any) -> "BaseConfigSettings":
        return config_settings_factory(data)


class BaseConfigRepository[SettingsT: BaseConfigSettings](abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_settings(cls, settings: SettingsT) -> typing.Self: ...

    async def dispose(self) -> None: ...

    @abc.abstractmethod
    async def get_config(self) -> task_base.RootConfig: ...


@dataclasses.dataclass
class RegistryRecord[SettingsT: BaseConfigSettings]:
    settings_class: type[SettingsT]
    repository_class: type[BaseConfigRepository[SettingsT]]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {}


def register_config_backend[SettingsT: BaseConfigSettings](
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
    repository_class = _REGISTRY[settings.type_name].repository_class
    return repository_class.from_settings(settings)


__all__ = [
    "BaseConfigRepository",
    "BaseConfigSettings",
    "ConfigRepositoryProtocol",
    "config_repository_factory",
    "config_settings_factory",
    "register_config_backend",
]

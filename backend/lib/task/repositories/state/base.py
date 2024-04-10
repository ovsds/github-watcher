import abc
import contextlib
import dataclasses
import typing

import pydantic
import pydantic_settings

import lib.utils.json as json_utils

StateData = json_utils.JsonSerializableDict


class StateProtocol(typing.Protocol):
    async def get(self) -> StateData | None: ...

    async def set(self, value: StateData) -> None: ...

    async def clear(self) -> None: ...

    def acquire(self) -> typing.AsyncContextManager[StateData | None]: ...


class StateRepositoryProtocol(typing.Protocol):
    async def dispose(self) -> None: ...

    async def get(self, path: str) -> StateData | None: ...

    async def set(self, path: str, value: StateData) -> None: ...

    async def clear(self, path: str) -> None: ...

    def acquire(self, path: str) -> typing.AsyncContextManager[StateData | None]: ...

    async def get_state(self, path: str) -> StateProtocol: ...


class BaseStateSettings(pydantic_settings.BaseSettings):
    type: typing.Any

    @classmethod
    def factory(cls, v: typing.Any, info: pydantic.ValidationInfo) -> "BaseStateSettings":
        return state_settings_factory(v)


SettingsT = typing.TypeVar("SettingsT", bound=BaseStateSettings)


class State:
    def __init__(self, repository: StateRepositoryProtocol, path: str):
        self._repository = repository
        self._path = path

    async def get(self) -> StateData | None:
        return await self._repository.get(self._path)

    async def set(self, value: StateData) -> None:
        await self._repository.set(self._path, value)

    async def clear(self) -> None:
        await self._repository.clear(self._path)

    @contextlib.asynccontextmanager
    async def acquire(self) -> typing.AsyncIterator[StateData | None]:
        async with self._repository.acquire(self._path) as state:
            yield state


class BaseStateRepository(typing.Generic[SettingsT], abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_settings(cls, settings: SettingsT) -> typing.Self: ...

    async def dispose(self) -> None: ...

    @abc.abstractmethod
    async def get(self, path: str) -> StateData | None: ...

    @abc.abstractmethod
    async def set(self, path: str, value: StateData) -> None: ...

    async def clear(self, path: str) -> None: ...

    @abc.abstractmethod
    def acquire(self, path: str) -> typing.AsyncContextManager[StateData | None]: ...

    async def get_state(self, path: str) -> StateProtocol:
        return State(repository=self, path=path)


@dataclasses.dataclass
class RegistryRecord(typing.Generic[SettingsT]):
    settings_class: type[SettingsT]
    repository_class: type[BaseStateRepository[SettingsT]]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {}


def register_state_backend(
    name: str,
    settings_class: type[SettingsT],
    repository_class: type[BaseStateRepository[SettingsT]],
) -> None:
    _REGISTRY[name] = RegistryRecord(
        settings_class=settings_class,
        repository_class=repository_class,
    )


def state_settings_factory(data: typing.Any) -> BaseStateSettings:
    assert isinstance(data, dict), "TaskStateBackendSettings must be a dict"
    assert "type" in data, "TaskStateBackendSettings must have a 'type' key"
    assert data["type"] in _REGISTRY, f"Unknown TaskStateBackendSettings type: {data['type']}"

    settings_class = _REGISTRY[data["type"]].settings_class
    return settings_class.model_validate(data)


def state_repository_factory(settings: BaseStateSettings) -> StateRepositoryProtocol:
    repository_class = _REGISTRY[settings.type].repository_class
    return repository_class.from_settings(settings)


__all__ = [
    "BaseStateRepository",
    "BaseStateSettings",
    "StateData",
    "StateProtocol",
    "StateRepositoryProtocol",
    "register_state_backend",
    "state_repository_factory",
    "state_settings_factory",
]

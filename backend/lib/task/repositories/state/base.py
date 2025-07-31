import abc
import contextlib
import dataclasses
import typing

import lib.task.protocols as task_protocols
import lib.utils.pydantic as pydantic_utils


class BaseStateSettings(pydantic_utils.TypedBaseModel):
    @classmethod
    def factory(cls, data: typing.Any) -> "BaseStateSettings":
        return state_settings_factory(data)


class State:
    def __init__(self, repository: task_protocols.StateRepositoryProtocol, path: str):
        self._repository = repository
        self._path = path

    async def get(self) -> task_protocols.StateData | None:
        return await self._repository.get(self._path)

    async def set(self, value: task_protocols.StateData) -> None:
        await self._repository.set(self._path, value)

    async def clear(self) -> None:
        await self._repository.clear(self._path)

    @contextlib.asynccontextmanager
    async def acquire(self) -> typing.AsyncIterator[task_protocols.StateData | None]:
        async with self._repository.acquire(self._path) as state:
            yield state


class BaseStateRepository[SettingsT: BaseStateSettings](abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_settings(cls, settings: SettingsT) -> typing.Self: ...

    async def dispose(self) -> None: ...

    @abc.abstractmethod
    async def get(self, path: str) -> task_protocols.StateData | None: ...

    @abc.abstractmethod
    async def set(self, path: str, value: task_protocols.StateData) -> None: ...

    async def clear(self, path: str) -> None: ...

    @abc.abstractmethod
    def acquire(self, path: str) -> typing.AsyncContextManager[task_protocols.StateData | None]: ...

    async def get_state(self, path: str) -> task_protocols.StateProtocol:
        return State(repository=self, path=path)


@dataclasses.dataclass
class RegistryRecord[SettingsT: BaseStateSettings]:
    settings_class: type[SettingsT]
    repository_class: type[BaseStateRepository[SettingsT]]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {}


def register_state_backend[SettingsT: BaseStateSettings](
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


def state_repository_factory(settings: BaseStateSettings) -> task_protocols.StateRepositoryProtocol:
    repository_class = _REGISTRY[settings.type_name].repository_class
    return repository_class.from_settings(settings)


__all__ = [
    "BaseStateRepository",
    "BaseStateSettings",
    "register_state_backend",
    "state_repository_factory",
    "state_settings_factory",
]

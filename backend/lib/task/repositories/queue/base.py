import abc
import dataclasses
import enum
import typing

import pydantic
import pydantic_settings

import lib.utils.json as json_utils


class Topic(str, enum.Enum):
    TASK_JOB = "task_jobs"
    TRIGGER_JOB = "trigger_jobs"
    EVENT_JOB = "events_jobs"

    FAILED_TASK_JOB = "failed_tasks_jobs"
    FAILED_TRIGGER_JOB = "failed_trigger_jobs"
    FAILED_EVENT_JOB = "failed_event_jobs"


ALL_TOPICS = frozenset(topic for topic in Topic)
FAILED_TOPICS = frozenset((Topic.FAILED_TASK_JOB, Topic.FAILED_TRIGGER_JOB, Topic.FAILED_EVENT_JOB))
TOPICS = ALL_TOPICS - FAILED_TOPICS


class QueueItem(typing.Protocol):
    @property
    def unique_key(self) -> typing.Hashable: ...

    def dump(self) -> json_utils.JsonSerializableDict: ...

    @classmethod
    def load(cls, value: json_utils.JsonSerializableDict) -> typing.Self: ...


class QueueRepositoryProtocol(typing.Protocol):
    class TopicClosed(Exception): ...

    class TopicFinished(Exception): ...

    async def dispose(self) -> None: ...

    @property
    def is_finished(self) -> bool: ...

    def is_topic_finished(self, topic: Topic) -> bool: ...

    async def push(self, topic: Topic, item: QueueItem, validate_not_closed: bool = True) -> None:
        """
        :raises TopicClosed: if topic is closed
        """

    def acquire(self, topic: Topic) -> typing.AsyncContextManager[QueueItem]:  # pyright: ignore[reportReturnType]
        """
        :raises TopicFinished: if topic is finished
        """

    async def consume(self, topic: Topic, item: QueueItem) -> None: ...

    async def close_topic(self, topic: Topic) -> None: ...


class BaseQueueSettings(pydantic_settings.BaseSettings):
    type: typing.Any

    @classmethod
    def factory(cls, v: typing.Any, info: pydantic.ValidationInfo) -> "BaseQueueSettings":
        return queue_settings_factory(v)


SettingsT = typing.TypeVar("SettingsT", bound=BaseQueueSettings)


class BaseQueueRepository(typing.Generic[SettingsT], abc.ABC):
    TopicClosed = QueueRepositoryProtocol.TopicClosed
    TopicFinished = QueueRepositoryProtocol.TopicFinished

    @classmethod
    @abc.abstractmethod
    def from_settings(cls, settings: SettingsT) -> typing.Self: ...

    async def dispose(self) -> None: ...

    @property
    @abc.abstractmethod
    def is_finished(self) -> bool: ...

    @abc.abstractmethod
    def is_topic_finished(self, topic: Topic) -> bool: ...

    @abc.abstractmethod
    async def push(self, topic: Topic, item: QueueItem, validate_not_closed: bool = True) -> None: ...

    @abc.abstractmethod
    def acquire(self, topic: Topic) -> typing.AsyncContextManager[QueueItem]: ...

    @abc.abstractmethod
    async def consume(self, topic: Topic, item: QueueItem) -> None: ...

    @abc.abstractmethod
    async def close_topic(self, topic: Topic) -> None: ...


@dataclasses.dataclass
class RegistryRecord(typing.Generic[SettingsT]):
    settings_class: type[SettingsT]
    repository_class: type[BaseQueueRepository[SettingsT]]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {}


def register_queue_backend(
    name: str,
    settings_class: type[SettingsT],
    repository_class: type[BaseQueueRepository[SettingsT]],
) -> None:
    _REGISTRY[name] = RegistryRecord(
        settings_class=settings_class,
        repository_class=repository_class,
    )


def queue_settings_factory(data: typing.Any) -> BaseQueueSettings:
    assert isinstance(data, dict), "QueueSettings must be a dict"
    assert "type" in data, "QueueSettings must have a 'type' key"
    assert data["type"] in _REGISTRY, f"Unknown queue backend type: {data['type']}"

    settings_class = _REGISTRY[data["type"]].settings_class
    return settings_class.parse_obj(data)


def queue_repository_factory(settings: BaseQueueSettings) -> QueueRepositoryProtocol:
    repository_class = _REGISTRY[settings.type].repository_class
    return repository_class.from_settings(settings)


__all__ = [
    "ALL_TOPICS",
    "BaseQueueRepository",
    "BaseQueueSettings",
    "FAILED_TOPICS",
    "QueueItem",
    "QueueRepositoryProtocol",
    "RegistryRecord",
    "TOPICS",
    "Topic",
    "queue_repository_factory",
    "queue_settings_factory",
    "register_queue_backend",
]

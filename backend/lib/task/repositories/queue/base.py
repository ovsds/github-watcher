import abc
import dataclasses
import enum
import typing

import pydantic
import pydantic_settings

import lib.utils.json as json_utils


class JobTopic(str, enum.Enum):
    TASK = "task_jobs"
    TRIGGER = "trigger_jobs"
    EVENT = "events_jobs"

    FAILED_TASK = "failed_tasks_jobs"
    FAILED_TRIGGER = "failed_trigger_jobs"
    FAILED_EVENT = "failed_event_jobs"


ALL_JOB_TOPICS = frozenset(topic for topic in JobTopic)
FAILED_JOB_TOPICS = frozenset((JobTopic.FAILED_TASK, JobTopic.FAILED_TRIGGER, JobTopic.FAILED_EVENT))
JOB_TOPICS = ALL_JOB_TOPICS - FAILED_JOB_TOPICS


class QueueItem(typing.Protocol):
    @property
    def unique_key(self) -> typing.Hashable: ...

    def to_raw(self) -> json_utils.JsonSerializableDict: ...

    @classmethod
    def from_raw(cls, raw: json_utils.JsonSerializableDict) -> typing.Self: ...


class QueueRepositoryProtocol(typing.Protocol):
    class TopicClosed(Exception): ...

    class TopicFinished(Exception): ...

    async def dispose(self) -> None: ...

    @property
    def is_finished(self) -> bool: ...

    def is_topic_finished(self, topic: JobTopic) -> bool: ...

    def is_topic_empty(self, topic: JobTopic) -> bool: ...

    async def push(self, topic: JobTopic, item: QueueItem, validate_not_closed: bool = True) -> None:
        """
        :raises TopicClosed: if topic is closed
        """

    def acquire(self, topic: JobTopic) -> typing.AsyncContextManager[QueueItem]:  # pyright: ignore[reportReturnType]
        """
        :raises TopicFinished: if topic is finished
        """

    async def consume(self, topic: JobTopic, item: QueueItem) -> None: ...

    async def close_topic(self, topic: JobTopic) -> None: ...


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
    def is_topic_finished(self, topic: JobTopic) -> bool: ...

    @abc.abstractmethod
    def is_topic_empty(self, topic: JobTopic) -> bool: ...

    @abc.abstractmethod
    async def push(self, topic: JobTopic, item: QueueItem, validate_not_closed: bool = True) -> None: ...

    @abc.abstractmethod
    def acquire(self, topic: JobTopic) -> typing.AsyncContextManager[QueueItem]: ...

    @abc.abstractmethod
    async def consume(self, topic: JobTopic, item: QueueItem) -> None: ...

    @abc.abstractmethod
    async def close_topic(self, topic: JobTopic) -> None: ...


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
    "ALL_JOB_TOPICS",
    "BaseQueueRepository",
    "BaseQueueSettings",
    "FAILED_JOB_TOPICS",
    "JOB_TOPICS",
    "JobTopic",
    "QueueItem",
    "QueueRepositoryProtocol",
    "RegistryRecord",
    "queue_repository_factory",
    "queue_settings_factory",
    "register_queue_backend",
]

import asyncio
import collections
import contextlib
import logging
import typing

import lib.task.repositories.queue.base as queue_base

logger = logging.getLogger(__name__)


class MemoryQueueSettings(queue_base.BaseQueueSettings):
    type: typing.Literal["memory"]


class Topic[QueueItemT: queue_base.QueueItem](asyncio.Queue[QueueItemT]):
    class TopicClosed(Exception):
        pass

    class TopicFinished(Exception):
        pass

    def __init__(self, maxsize: int = 0):
        self._closed = asyncio.Event()

        self._consumed_items: set[typing.Hashable] = set()
        super().__init__(maxsize=maxsize)

    async def close(self) -> None:
        if self.is_closed:
            return

        self._closed.set()
        asyncio.create_task(self._clean_up())

    async def _clean_up(self) -> None:
        await super().join()

        self._putters: typing.Iterable[  # pyright: ignore[reportUninitializedInstanceVariable]
            asyncio.Future[QueueItemT]
        ]
        for putter in self._putters:
            if not putter.done():
                putter.set_exception(self.TopicClosed)

        self._getters: typing.Iterable[  # pyright: ignore[reportUninitializedInstanceVariable]
            asyncio.Future[QueueItemT]
        ]
        for getter in self._getters:
            if not getter.done():
                getter.set_exception(self.TopicFinished)

    @property
    def is_closed(self) -> bool:
        return self._closed.is_set()

    def _validate_not_closed(self) -> None:
        if self.is_closed:
            raise self.TopicClosed()

    @property
    def is_finished(self) -> bool:
        unfinished_tasks = typing.cast(int, self._unfinished_tasks)  # pyright: ignore[reportAttributeAccessIssue]
        return self._closed.is_set() and unfinished_tasks == 0

    def _validate_not_finished(self) -> None:
        if self.is_finished:
            raise self.TopicFinished()

    async def get(self) -> QueueItemT:
        self._validate_not_finished()
        return await super().get()

    async def put(self, item: QueueItemT, validate_not_closed: bool = True) -> None:
        if validate_not_closed:
            self._validate_not_closed()
        await super().put(item)

    async def consume(self, item: QueueItemT) -> None:
        self._consumed_items.add(item.unique_key)

    @contextlib.asynccontextmanager
    async def acquire(self) -> typing.AsyncIterator[QueueItemT]:
        item = await self.get()

        try:
            yield item
        finally:
            if item.unique_key in self._consumed_items:
                self._consumed_items.remove(item.unique_key)
            else:
                await self.put(item, validate_not_closed=False)
            self.task_done()


class MemoryQueueRepository(queue_base.BaseQueueRepository[MemoryQueueSettings]):
    def __init__(self):
        self._topics: dict[str, Topic[queue_base.QueueItem]] = collections.defaultdict(Topic)

    @classmethod
    def from_settings(cls, settings: MemoryQueueSettings) -> typing.Self:
        return cls()

    @property
    def is_finished(self) -> bool:
        return all(topic.is_finished for topic in self._topics.values())

    def is_topic_finished(self, topic: queue_base.JobTopic) -> bool:
        return self._topics[topic].is_finished

    def is_topic_empty(self, topic: queue_base.JobTopic) -> bool:
        return self._topics[topic].empty()

    @contextlib.contextmanager
    def _wrap_queue_errors(self, topic: queue_base.JobTopic) -> typing.Iterator[None]:
        try:
            yield
        except Topic.TopicClosed as exc:
            raise self.TopicClosed(f"Topic({topic}) is already closed.") from exc
        except Topic.TopicFinished as exc:
            raise self.TopicFinished(f"Topic({topic}) is already finished.") from exc

    async def push(
        self,
        topic: queue_base.JobTopic,
        item: queue_base.QueueItem,
        validate_not_closed: bool = True,
    ) -> None:
        logger.debug("Pushing item to topic %s: %s", topic, item)
        with self._wrap_queue_errors(topic):
            await self._topics[topic].put(item, validate_not_closed=validate_not_closed)

    @contextlib.asynccontextmanager
    async def acquire(self, topic: queue_base.JobTopic) -> typing.AsyncIterator[queue_base.QueueItem]:
        with self._wrap_queue_errors(topic):
            async with self._topics[topic].acquire() as task:
                yield task

    async def consume(self, topic: queue_base.JobTopic, item: queue_base.QueueItem) -> None:
        logger.debug("Consuming item from topic %s: %s", topic, item)
        await self._topics[topic].consume(item)

    async def close_topic(self, topic: queue_base.JobTopic) -> None:
        await self._topics[topic].close()


__all__ = [
    "MemoryQueueRepository",
    "MemoryQueueSettings",
]

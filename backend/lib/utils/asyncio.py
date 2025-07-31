import asyncio
import contextlib
import fcntl
import os
import pathlib
import typing


class GatherIterators[T]:
    def __init__(self, iterators: typing.Iterable[typing.AsyncIterator[T]]) -> None:
        self._iterators: dict[asyncio.Task[T], typing.AsyncIterator[T]] = {}  # {task: iterator}

        for iterator in iterators:
            self._add_iterator(iterator)

    def _add_iterator(self, iterator: typing.AsyncIterator[T]) -> None:
        coroutine = typing.cast(typing.Coroutine[None, None, T], iterator.__anext__())
        task = asyncio.create_task(coroutine)
        self._iterators[task] = iterator

    def _delete_iterator_by_task(self, task: asyncio.Task[T]) -> None:
        del self._iterators[task]

    def _create_next_task(self, task: asyncio.Task[T]) -> None:
        iterator = self._iterators.pop(task)
        self._add_iterator(iterator)

    @property
    def _tasks(self) -> typing.Collection[asyncio.Task[T]]:
        return self._iterators.keys()

    async def __aiter__(self) -> typing.AsyncIterator[T]:
        while self._iterators:
            done, _ = await asyncio.wait(self._tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                try:
                    yield task.result()
                except StopAsyncIteration:
                    self._delete_iterator_by_task(task)
                else:
                    self._create_next_task(task)


class TimeoutTimer:
    def __init__(self, timeout: float = 0):
        self._timeout = timeout
        self._deadline = asyncio.get_event_loop().time() + timeout

    @property
    def is_expired(self):
        if self._timeout == 0:
            return False

        return asyncio.get_event_loop().time() > self._deadline


def _acquire_lock(path: str) -> typing.IO[bytes]:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb+") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
    return file


@contextlib.asynccontextmanager
async def acquire_file_lock(path: str) -> typing.AsyncIterator[None]:
    loop = asyncio.get_running_loop()
    file = await loop.run_in_executor(None, _acquire_lock, path)
    try:
        yield
    finally:
        file.close()
        os.remove(path)


__all__ = [
    "GatherIterators",
    "TimeoutTimer",
    "acquire_file_lock",
]

import asyncio
import contextlib
import fcntl
import os
import pathlib
import typing


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
    "TimeoutTimer",
    "acquire_file_lock",
]

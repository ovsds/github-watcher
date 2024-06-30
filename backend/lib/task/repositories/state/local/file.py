import contextlib
import logging
import pathlib
import typing

import aiofile

import lib.task.protocols as task_protocols
import lib.task.repositories.state.base as state_base
import lib.utils.asyncio as asyncio_utils
import lib.utils.json as json_utils

logger = logging.getLogger(__name__)


class LocalDirStateSettings(state_base.BaseStateSettings):
    type: typing.Literal["local_dir"]
    path: str


class LocalDirStateRepository(state_base.BaseStateRepository[LocalDirStateSettings]):
    def __init__(self, root_path: str):
        self._root_path: pathlib.Path = pathlib.Path(root_path)

    @classmethod
    def from_settings(cls, settings: LocalDirStateSettings) -> typing.Self:
        return cls(root_path=settings.path)

    async def get(self, path: str) -> task_protocols.StateData | None:
        logger.debug("Loading State(%s)", path)
        try:
            async with aiofile.async_open(f"{self._root_path}/{path}.json", "r") as file:
                data = await file.read()
                if data == "":
                    logger.debug("Found empty State(%s)", path)
                    return None

                return json_utils.loads_str(data)
        except FileNotFoundError:
            logger.debug("No State(%s) was found", path)
            return None

    async def set(self, path: str, value: task_protocols.StateData) -> None:
        logger.debug("Saving State(%s)", path)
        self._root_path.joinpath(path).parent.mkdir(parents=True, exist_ok=True)

        async with aiofile.async_open(f"{self._root_path}/{path}.json", "w+") as file:
            await file.write(json_utils.dumps_str(value))

    async def clear(self, path: str) -> None:
        logger.debug("Clearing State(%s)", path)
        try:
            self._root_path.joinpath(f"{path}.json").unlink()
        except FileNotFoundError:
            pass

    @contextlib.asynccontextmanager
    async def acquire(self, path: str) -> typing.AsyncIterator[task_protocols.StateData | None]:
        async with asyncio_utils.acquire_file_lock(f"{self._root_path}/{path}.lock"):
            logger.debug("Acquired lock for State(%s)", path)
            yield await self.get(path)
            logger.debug("Released lock for State(%s)", path)


__all__ = [
    "LocalDirStateRepository",
    "LocalDirStateSettings",
]

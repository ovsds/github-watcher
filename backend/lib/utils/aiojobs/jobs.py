import abc
import asyncio
import logging
import typing


class JobProtocol(typing.Protocol):
    @property
    def name(self) -> str: ...

    async def process(self) -> None: ...


class JobBase(abc.ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abc.abstractmethod
    async def process(self) -> None: ...


class OneShotJob(JobBase):
    def __init__(
        self,
        max_retries: int,
        retry_timeout: float,
        logger: logging.Logger,
    ) -> None:
        self._max_retries = max_retries
        self._retry_timeout = retry_timeout
        self._logger = logger

    async def process(self) -> None:
        retries = 0
        while True:
            try:
                await self._process()
            except asyncio.CancelledError:
                self._logger.info("Job %r has been cancelled", self.name)
                return
            except Exception:
                retries += 1
                if retries >= self._max_retries:
                    self._logger.exception("Job %s exceeded max_retries and will be aborted", self.name)
                    return

                self._logger.exception(
                    "Job %r has crashed, it will be retried after %.1f seconds (retry counter: %s)",
                    self.name,
                    self._retry_timeout,
                    retries,
                )
                await asyncio.sleep(self._retry_timeout)
            else:
                return

    @abc.abstractmethod
    async def _process(self) -> None: ...


class RepeatableJob(JobBase):
    def __init__(
        self,
        delay_timeout: float,
        retry_timeout: float,
        logger: logging.Logger,
    ) -> None:
        self._delay_timeout = delay_timeout
        self._retry_timeout = retry_timeout
        self._logger = logger

        self._finished = False

    async def process(self) -> None:
        while True:
            try:
                await self._process()
            except asyncio.CancelledError:
                self._logger.info("Job %r has been cancelled", self.name)
                return
            except Exception:
                self._logger.exception(
                    "Job %r has been crashed, it will be retried after %.1f seconds",
                    self.name,
                    self._retry_timeout,
                )
                await asyncio.sleep(self._retry_timeout)
            else:
                if self._finished:
                    self._logger.info("Job %r has been finished", self.name)
                    return
                await asyncio.sleep(self._delay_timeout)

    def finish(self) -> None:
        self._finished = True

    @abc.abstractmethod
    async def _process(self) -> None: ...


__all__ = [
    "JobProtocol",
    "OneShotJob",
    "RepeatableJob",
]

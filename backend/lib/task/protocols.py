import typing

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


__all__ = [
    "StateData",
    "StateProtocol",
    "StateRepositoryProtocol",
]

import typing


class ApplicationError(Exception):
    def __init__(self, message: str, *args: typing.Any) -> None:
        super().__init__(*args)
        self.message = message


class DisposeError(ApplicationError):
    pass


class ServerStartError(ApplicationError):
    pass


class ServerRuntimeError(ApplicationError):
    pass


class ApplicationFailedJobsError(ApplicationError):
    pass


class ApplicationTimeoutError(ApplicationError):
    pass


__all__ = [
    "ApplicationError",
    "ApplicationFailedJobsError",
    "ApplicationTimeoutError",
    "DisposeError",
    "ServerRuntimeError",
    "ServerStartError",
]

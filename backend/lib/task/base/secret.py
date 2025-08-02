import abc
import logging
import os
import typing

import lib.utils.logging as logging_utils
import lib.utils.pydantic as pydantic_utils

logger = logging.getLogger(__name__)


class BaseSecretConfig(pydantic_utils.TypedBaseModel):
    @property
    @abc.abstractmethod
    def value(self) -> typing.Any: ...


class PlainSecretConfig(BaseSecretConfig):
    plain_value: str

    @property
    def value(self) -> str:
        return self.plain_value


class EnvSecretConfig(BaseSecretConfig):
    key: str

    @property
    def value(self) -> str:
        value = os.environ[self.key]
        logging_utils.register_secret(value=value, replace_value=f"REPLACED ENV SECRET {self.key}")

        return value


def register_default_plugins() -> None:
    logger.info("Registering default task base secret plugins")
    BaseSecretConfig.register("env", EnvSecretConfig)
    BaseSecretConfig.register("plain", PlainSecretConfig)


__all__ = [
    "BaseSecretConfig",
    "EnvSecretConfig",
]

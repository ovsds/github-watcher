import abc
import dataclasses
import os
import typing

import pydantic

import lib.utils.pydantic as pydantic_utils


class BaseSecretConfig(pydantic_utils.BaseModel):
    type: str

    @classmethod
    def factory(cls, v: typing.Any, info: pydantic.ValidationInfo) -> "BaseSecretConfig[typing.Any]":
        return action_config_factory(v)

    @property
    @abc.abstractmethod
    def value(self) -> typing.Any: ...


ConfigT = typing.TypeVar("ConfigT", bound=BaseSecretConfig)


@dataclasses.dataclass
class RegistryRecord(typing.Generic[ConfigT]):
    config_class: type[ConfigT]


_REGISTRY: dict[str, RegistryRecord[typing.Any]] = {}


def register_secret(
    name: str,
    config_class: type[ConfigT],
) -> None:
    _REGISTRY[name] = RegistryRecord(config_class=config_class)


def action_config_factory(data: typing.Any) -> BaseSecretConfig:
    if isinstance(data, BaseSecretConfig):
        return data

    assert isinstance(data, dict)
    assert "type" in data

    config_class = _REGISTRY[data["type"]].config_class
    return config_class.model_validate(data)


SecretConfigPydanticAnnotation = typing.Annotated[
    pydantic.SerializeAsAny[BaseSecretConfig],
    pydantic.BeforeValidator(action_config_factory),
]


class EnvSecretConfig(BaseSecretConfig):
    key: str

    @property
    def value(self) -> str:
        return os.environ[self.key]


__all__ = [
    "BaseSecretConfig",
    "EnvSecretConfig",
    "SecretConfigPydanticAnnotation",
    "action_config_factory",
    "register_secret",
]

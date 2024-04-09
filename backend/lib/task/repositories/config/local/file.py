import logging
import typing

import aiofile
import yaml

import lib.task.base as task_base
import lib.task.repositories.config.base as config_base

logger = logging.getLogger(__name__)


class YamlFileConfigSettings(config_base.BaseConfigSettings):
    type: typing.Literal["yaml_file"]
    path: str


class YamlFileConfigRepository(config_base.BaseConfigRepository[YamlFileConfigSettings]):
    def __init__(self, path: str):
        self._path = path

    @classmethod
    def from_settings(cls, settings: YamlFileConfigSettings) -> typing.Self:
        return cls(path=settings.path)

    async def get_config(self) -> task_base.RootConfig:
        async with aiofile.async_open(self._path, mode="r") as file:
            raw = await file.read()

        data = yaml.safe_load(raw)
        return task_base.RootConfig.model_validate(data)


__all__ = [
    "YamlFileConfigRepository",
    "YamlFileConfigSettings",
]

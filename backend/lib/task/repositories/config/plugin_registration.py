import logging

import lib.task.repositories.config.base as base
import lib.task.repositories.config.local as local

logger = logging.getLogger(__name__)


def register_default_plugins() -> None:
    logger.info("Registering default config plugins")
    base.register_config_backend(
        name="yaml_file",
        settings_class=local.YamlFileConfigSettings,
        repository_class=local.YamlFileConfigRepository,
    )


__all__ = [
    "register_default_plugins",
]

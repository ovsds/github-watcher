import logging

import lib.task.repositories.state.base as base
import lib.task.repositories.state.local as local

logger = logging.getLogger(__name__)


def register_default_plugins() -> None:
    logger.info("Registering default state plugins")
    base.register_state_backend(
        name="local_dir",
        settings_class=local.LocalDirStateSettings,
        repository_class=local.LocalDirStateRepository,
    )


__all__ = [
    "register_default_plugins",
]

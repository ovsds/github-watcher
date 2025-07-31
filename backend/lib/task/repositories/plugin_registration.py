import logging

import lib.task.repositories.config as config_repositories
import lib.task.repositories.queue as queue_repositories
import lib.task.repositories.state as state_repositories

logger = logging.getLogger(__name__)


def register_default_plugins() -> None:
    logger.info("Registering default task repository plugins")
    config_repositories.register_default_plugins()
    queue_repositories.register_default_plugins()
    state_repositories.register_default_plugins()


__all__ = [
    "register_default_plugins",
]

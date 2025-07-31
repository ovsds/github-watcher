import logging

import lib.task.base.secret as secret

logger = logging.getLogger(__name__)


def register_default_plugins() -> None:
    logger.info("Registering default task base plugins")
    secret.register_default_plugins()


__all__ = [
    "register_default_plugins",
]

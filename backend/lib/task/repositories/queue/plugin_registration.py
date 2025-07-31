import logging

import lib.task.repositories.queue.base as base
import lib.task.repositories.queue.local as local

logger = logging.getLogger(__name__)


def register_default_plugins() -> None:
    logger.info("Registering default queue plugins")
    base.register_queue_backend(
        name="memory",
        settings_class=local.MemoryQueueSettings,
        repository_class=local.MemoryQueueRepository,
    )


__all__ = [
    "register_default_plugins",
]

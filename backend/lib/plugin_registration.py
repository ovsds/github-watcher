import logging

import lib.github.triggers as github_triggers
import lib.task.base as task_base
import lib.task.repositories as task_repositories
import lib.telegram.actions as telegram_actions

logger = logging.getLogger(__name__)


def register_default_plugins() -> None:
    logger.info("Registering default plugins")
    task_repositories.register_default_plugins()
    task_base.register_default_plugins()
    telegram_actions.register_default_plugins()
    github_triggers.register_default_plugins()


__all__ = [
    "register_default_plugins",
]

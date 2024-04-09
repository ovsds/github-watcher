import lib.github.triggers as github_triggers
import lib.task.base as task_base
import lib.task.repositories as task_repositories
import lib.telegram.actions as telegram_actions


def register_plugins() -> None:
    task_repositories.register_config_backend(
        name="yaml_file",
        settings_class=task_repositories.YamlFileConfigSettings,
        repository_class=task_repositories.YamlFileConfigRepository,
    )
    task_repositories.register_queue_backend(
        name="memory",
        settings_class=task_repositories.MemoryQueueSettings,
        repository_class=task_repositories.MemoryQueueRepository,
    )
    task_repositories.register_state_backend(
        name="local_dir",
        settings_class=task_repositories.LocalDirStateSettings,
        repository_class=task_repositories.LocalDirStateRepository,
    )
    task_base.register_secret(
        name="env",
        config_class=task_base.EnvSecretConfig,
    )

    task_base.register_trigger(
        name="github",
        config_class=github_triggers.GithubTriggerConfig,
        processor_class=github_triggers.GithubTriggerProcessor,
    )
    task_base.register_action(
        name="telegram_webhook",
        config_class=telegram_actions.TelegramWebhookActionConfig,
        processor_class=telegram_actions.TelegramWebhookProcessor,
    )


__all__ = [
    "register_plugins",
]

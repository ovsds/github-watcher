import lib.task.base as task_base
import lib.telegram.actions as telegram_actions
import tests.settings as test_settings


def test_config_factory(settings: test_settings.Settings):
    config = task_base.action_config_factory(
        data={
            "id": "test_telegram_webhook",
            "type": "telegram_webhook",
            "chat_id_secret": {
                "type": "env",
                "key": "TELEGRAM_CHAT_ID",
            },
            "token_secret": {
                "type": "env",
                "key": "TELEGRAM_TOKEN",
            },
        },
    )

    assert isinstance(config, telegram_actions.TelegramWebhookActionConfig)

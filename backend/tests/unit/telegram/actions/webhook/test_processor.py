import aiohttp
import pytest
import pytest_mock

import lib.task.base as task_base
import lib.telegram.actions as telegram_actions
import lib.telegram.clients as telegram_clients


@pytest.fixture(name="config")
def config_fixture() -> telegram_actions.TelegramWebhookActionConfig:
    result = task_base.action_config_factory(
        data={
            "id": "test_telegram_webhook",
            "type": "telegram_webhook",
            "chat_id_secret": {
                "type": "plain",
                "plain_value": "1234567890",
            },
            "token_secret": {
                "type": "plain",
                "plain_value": "1234567890",
            },
        },
    )

    assert isinstance(result, telegram_actions.TelegramWebhookActionConfig)
    return result


@pytest.mark.asyncio
async def test_factory(config: telegram_actions.TelegramWebhookActionConfig):
    processor = task_base.action_processor_factory(config=config)

    assert isinstance(processor, telegram_actions.TelegramWebhookProcessor)
    assert processor.config == config
    assert isinstance(processor.aiohttp_client, aiohttp.ClientSession)
    assert isinstance(processor.telegram_client, telegram_clients.RestTelegramClient)
    assert processor.telegram_client.token == config.token_secret.value
    assert processor.telegram_client.aiohttp_client == processor.aiohttp_client

    await processor.dispose()


@pytest.mark.asyncio
async def test_process(
    mocker: pytest_mock.MockerFixture,
    config: telegram_actions.TelegramWebhookActionConfig,
):
    aiohttp_client = mocker.MagicMock(spec=aiohttp.ClientSession)
    telegram_client = mocker.MagicMock(spec=telegram_clients.RestTelegramClient)

    processor = telegram_actions.TelegramWebhookProcessor(
        config=config,
        aiohttp_client=aiohttp_client,
        telegram_client=telegram_client,
    )

    event = task_base.Event(
        id="test_event",
        title="test_title",
        body="test_body",
        url="test_url",
    )

    await processor.process(
        event=event,
    )

    assert telegram_client.send_message.awaited_once_with(
        request=telegram_clients.SendMessageRequest(
            chat_id=config.chat_id_secret.value,
            text="<b>test_title</b>\ntest_body\ntest_url",
        ),
    )

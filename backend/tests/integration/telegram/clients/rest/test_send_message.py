import pytest

import lib.telegram.clients as telegram_clients
import tests.settings as test_settings


@pytest.mark.asyncio
async def test_default(
    telegram_client: telegram_clients.RestTelegramClient,
    settings: test_settings.Settings,
):
    await telegram_client.send_message(
        request=telegram_clients.SendMessageRequest(
            chat_id=settings.telegram_chat_id,
            text="Integration test",
        ),
    )

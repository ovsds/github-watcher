import dataclasses
import logging
import typing

import aiohttp

import lib.task.base as task_base
import lib.telegram.clients as telegram_clients
import lib.utils.pydantic as pydantic_utils

logger = logging.getLogger(__name__)


def trim_string(s: str, max_length: int) -> str:
    return s[:max_length] + "..." if len(s) > max_length else s


class TelegramWebhookActionConfig(task_base.BaseActionConfig):
    chat_id_secret: pydantic_utils.TypedAnnotation[task_base.BaseSecretConfig]
    token_secret: pydantic_utils.TypedAnnotation[task_base.BaseSecretConfig]
    max_message_title_length: int = 100
    max_message_body_length: int = 500


@dataclasses.dataclass(frozen=True)
class TelegramWebhookProcessor(task_base.BaseActionProcessor[TelegramWebhookActionConfig]):
    config: TelegramWebhookActionConfig
    aiohttp_client: aiohttp.ClientSession
    telegram_client: telegram_clients.RestTelegramClient

    async def dispose(self) -> None:
        await self.aiohttp_client.close()

    @classmethod
    def from_config(
        cls,
        config: TelegramWebhookActionConfig,
    ) -> typing.Self:
        aiohttp_client = aiohttp.ClientSession()
        telegram_client = telegram_clients.RestTelegramClient(
            token=config.token_secret.value,
            aiohttp_client=aiohttp_client,
        )

        return cls(
            config=config,
            aiohttp_client=aiohttp_client,
            telegram_client=telegram_client,
        )

    def _format_message(self, event: task_base.Event) -> str:
        return (
            f"<b>{trim_string(event.title, self.config.max_message_title_length)}</b>"
            f"\n{trim_string(event.body, self.config.max_message_body_length)}"
            f"\n{event.url}"
        )

    async def process(self, event: task_base.Event) -> None:
        text = self._format_message(event)
        await self.telegram_client.send_message(
            request=telegram_clients.SendMessageRequest(
                chat_id=self.config.chat_id_secret.value,
                text=text,
            ),
        )


def register_default_plugins() -> None:
    logger.info("Registering default telegram actions plugins")
    task_base.register_action(
        name="telegram_webhook",
        config_class=TelegramWebhookActionConfig,
        processor_class=TelegramWebhookProcessor,
    )


__all__ = [
    "TelegramWebhookActionConfig",
    "TelegramWebhookProcessor",
    "register_default_plugins",
]

import typing

import aiohttp

import lib.task.base as task_base


def trim_string(s: str, max_length: int) -> str:
    return s[:max_length] + "..." if len(s) > max_length else s


class TelegramWebhookActionConfig(task_base.BaseActionConfig):
    chat_id_secret: task_base.SecretConfigPydanticAnnotation
    token_secret: task_base.SecretConfigPydanticAnnotation
    max_message_title_length: int = 100
    max_message_body_length: int = 500


class TelegramWebhookProcessor(task_base.ActionProcessor[TelegramWebhookActionConfig]):
    def __init__(
        self,
        config: TelegramWebhookActionConfig,
        aiohttp_client: aiohttp.ClientSession,
    ):
        self._config = config
        self._aiohttp_client = aiohttp_client

    async def dispose(self) -> None:
        await self._aiohttp_client.close()

    @classmethod
    def from_config(
        cls,
        config: TelegramWebhookActionConfig,
    ) -> typing.Self:
        aiohttp_client = aiohttp.ClientSession()

        return cls(
            config=config,
            aiohttp_client=aiohttp_client,
        )

    async def process(self, event: task_base.Event) -> None:
        async with self._aiohttp_client.post(
            f"https://api.telegram.org/bot{self._config.token_secret.value}/sendMessage",
            params={
                "chat_id": self._config.chat_id_secret.value,
                "text": f"<b>{trim_string(event.title, self._config.max_message_title_length)}</b>"
                f"\n{trim_string(event.body, self._config.max_message_body_length)}"
                f"\n{event.url}",
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            },
        ) as response:
            response.raise_for_status()


__all__ = [
    "TelegramWebhookActionConfig",
    "TelegramWebhookProcessor",
]

import dataclasses

import aiohttp
import aiohttp.typedefs as aiohttp_typedefs


@dataclasses.dataclass(frozen=True)
class SendMessageRequest:
    chat_id: str
    text: str
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = True

    @property
    def method(self) -> str:
        return "POST"

    @property
    def path(self) -> str:
        return "/sendMessage"

    @property
    def params(self) -> aiohttp_typedefs.Query:
        return {
            "chat_id": self.chat_id,
            "text": self.text,
            "parse_mode": self.parse_mode,
            "disable_web_page_preview": "true" if self.disable_web_page_preview else "false",
        }


@dataclasses.dataclass(frozen=True)
class RestTelegramClient:
    aiohttp_client: aiohttp.ClientSession
    token: str

    def _prepare_url(self, path: str) -> str:
        return f"https://api.telegram.org/bot{self.token}{path}"

    async def send_message(self, request: SendMessageRequest) -> None:
        async with self.aiohttp_client.request(
            method=request.method,
            url=self._prepare_url(request.path),
            params=request.params,
        ) as response:
            response.raise_for_status()


__all__ = [
    "RestTelegramClient",
    "SendMessageRequest",
]

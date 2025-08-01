import lib.utils.pydantic as pydantic_utils


class Settings(pydantic_utils.BaseSettings):
    github_token: str = NotImplemented

    telegram_token: str = NotImplemented
    telegram_chat_id: str = NotImplemented


__all__ = [
    "Settings",
]

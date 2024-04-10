import logging
import typing

_SECRETS: dict[str, str] = dict()  # value: replace_value


def register_secret(value: str, replace_value: str) -> None:
    if value == "":
        return

    _SECRETS[value] = replace_value


class CustomFormatter(logging.Formatter):
    def __init__(
        self,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        log_message = super().format(record)

        for value, replace_value in _SECRETS.items():
            log_message = log_message.replace(value, f"***{replace_value}***")

        return log_message


__all__ = [
    "CustomFormatter",
    "register_secret",
]

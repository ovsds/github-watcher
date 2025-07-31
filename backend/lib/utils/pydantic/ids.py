import typing

import pydantic

import lib.utils.pydantic.base as base

ID_STR_VALID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-=/")


def id_str_validator(v: str) -> str:
    for char in v:
        if char not in ID_STR_VALID_CHARS:
            raise ValueError(f"ID string contains invalid character: {char}")

    return v


class IDMixinModel(base.BaseModel):
    id: typing.Annotated[str, pydantic.AfterValidator(id_str_validator)]


def check_unique_ids[IDModelT: IDMixinModel](items: list[IDModelT]) -> list[IDModelT]:
    ids: set[str] = set()
    for item in items:
        if item.id in ids:
            raise ValueError(f"Duplicate task id: {item.id}")
        ids.add(item.id)

    return items


__all__ = [
    "IDMixinModel",
    "check_unique_ids",
    "id_str_validator",
]

import typing

import pydantic

T = typing.TypeVar("T")


class BaseModel(pydantic.BaseModel): ...


def make_list_factory(
    factory: typing.Callable[[typing.Any, pydantic.ValidationInfo], T]
) -> typing.Callable[[typing.Any, pydantic.ValidationInfo], list[T]]:
    def list_factory(v: typing.Any, info: pydantic.ValidationInfo) -> list[T]:
        assert isinstance(v, list)
        return [factory(item, info) for item in v]  # type: ignore

    return list_factory


ID_STR_VALID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-=/")


def id_str_validator(v: str) -> str:
    assert all(
        char in ID_STR_VALID_CHARS for char in v
    ), "ID string contains invalid characters(other than [a-zA-Z0-9_-])"

    return v


class IDMixinModel(pydantic.BaseModel):
    id: typing.Annotated[str, pydantic.AfterValidator(id_str_validator)]


IDModelT = typing.TypeVar("IDModelT", bound=IDMixinModel)


def check_unique_ids(items: list[IDModelT]) -> list[IDModelT]:
    ids: set[str] = set()
    for item in items:
        if item.id in ids:
            raise ValueError(f"Duplicate task id: {item.id}")
        ids.add(item.id)

    return items


__all__ = [
    "BaseModel",
    "IDMixinModel",
    "check_unique_ids",
    "id_str_validator",
    "make_list_factory",
]

import typing

import ujson

JsonSerializableType = str | int | float | bool | None
JsonSerializable = JsonSerializableType | typing.Mapping[str, "JsonSerializable"] | typing.Sequence["JsonSerializable"]
JsonSerializableDict = dict[str, JsonSerializable]
JsonSerializableList = list[JsonSerializable]


dumps_str = ujson.dumps
loads_str = ujson.loads


def dumps_bytes(obj: JsonSerializable) -> bytes:
    return dumps_str(obj).encode("utf-8")


def loads_bytes(obj: bytes) -> JsonSerializable:
    return loads_str(obj.decode("utf-8"))


__all__ = [
    "JsonSerializable",
    "JsonSerializableDict",
    "JsonSerializableList",
    "JsonSerializableType",
    "dumps_bytes",
    "dumps_str",
    "loads_bytes",
    "loads_str",
]

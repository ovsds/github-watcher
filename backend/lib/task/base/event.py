import lib.utils.pydantic as pydantic_utils


class Event(pydantic_utils.BaseModel, pydantic_utils.IDMixinModel):
    title: str
    body: str
    url: str


__all__ = [
    "Event",
]

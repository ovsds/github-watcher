import lib.utils.pydantic as pydantic_utils


class Event(pydantic_utils.IDMixinModel, pydantic_utils.BaseModel):
    title: str
    body: str
    url: str


__all__ = [
    "Event",
]

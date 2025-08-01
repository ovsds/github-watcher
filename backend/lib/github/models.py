import dataclasses
import datetime


@dataclasses.dataclass(frozen=True)
class Repository:
    owner: str
    name: str


@dataclasses.dataclass(frozen=True)
class Issue:
    id: str
    author: str | None
    url: str
    title: str
    body: str
    created_at: datetime.datetime


@dataclasses.dataclass(frozen=True)
class PullRequest:
    id: str
    author: str | None
    url: str
    title: str
    body: str
    created_at: datetime.datetime


@dataclasses.dataclass(frozen=True)
class WorkflowRun:
    id: int
    name: str
    url: str
    status: str
    conclusion: str | None
    created_at: datetime.datetime


__all__ = [
    "Issue",
    "PullRequest",
    "Repository",
    "WorkflowRun",
]

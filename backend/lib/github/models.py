import dataclasses
import datetime


@dataclasses.dataclass
class Issue:
    id: str
    author: str | None
    url: str
    title: str
    body: str
    created_at: datetime.datetime


@dataclasses.dataclass
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

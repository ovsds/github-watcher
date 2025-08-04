import dataclasses
import datetime

type UserLogin = str
type OrganizationName = str
type OwnerName = UserLogin | OrganizationName
type RepositoryName = str
type TeamSlug = str

type WorkflowRunStatus = str
type WorkflowRunConclusion = str


@dataclasses.dataclass(frozen=True)
class Repository:
    owner: OwnerName
    name: RepositoryName


@dataclasses.dataclass(frozen=True)
class Issue:
    id: str
    author: UserLogin | None
    url: str
    title: str
    body: str
    created_at: datetime.datetime


@dataclasses.dataclass(frozen=True)
class PullRequest:
    id: str
    author: UserLogin | None
    url: str
    title: str
    body: str
    created_at: datetime.datetime


@dataclasses.dataclass(frozen=True)
class WorkflowRun:
    id: int
    name: str
    url: str
    status: WorkflowRunStatus
    conclusion: WorkflowRunConclusion | None
    created_at: datetime.datetime


__all__ = [
    "Issue",
    "OrganizationName",
    "OwnerName",
    "PullRequest",
    "Repository",
    "RepositoryName",
    "TeamSlug",
    "UserLogin",
    "WorkflowRun",
    "WorkflowRunConclusion",
    "WorkflowRunStatus",
]

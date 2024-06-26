import abc
import dataclasses
import datetime
import logging
import typing

import aiohttp
import pydantic

import lib.github.models as github_models

logger = logging.getLogger(__name__)


class BaseRequest(abc.ABC):
    method: str

    @property
    @abc.abstractmethod
    def url(self) -> str: ...

    @property
    def params(self) -> dict[str, typing.Any]:
        return {}


class BaseModel(pydantic.BaseModel): ...


class BaseResponse(BaseModel):
    def to_dataclass(self) -> typing.Any:
        raise NotImplementedError


ResponseT = typing.TypeVar("ResponseT", bound=BaseResponse)


@dataclasses.dataclass
class GetRepositoryWorkflowRunsRequest(BaseRequest):
    owner: str
    repository: str
    created_after: datetime.datetime
    per_page: int = 100
    page: int = 1
    exclude_pull_requests: bool = True
    method: str = "GET"

    @property
    def url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repository}/actions/runs"

    @property
    def params(self) -> dict[str, typing.Any]:
        return {
            "created": f">={self.created_after.isoformat()}Z",
            "per_page": self.per_page,
            "page": self.page,
            "exclude_pull_requests": "true" if self.exclude_pull_requests else "false",
        }


class GetRepositoryWorkflowRunsResponse(BaseResponse):
    class WorkflowRun(pydantic.BaseModel):
        id: int
        name: str
        html_url: str
        status: str
        conclusion: str | None
        created_at: datetime.datetime

    total_count: int
    workflow_runs: list[WorkflowRun]

    def to_dataclass(self) -> list[github_models.WorkflowRun]:
        return [
            github_models.WorkflowRun(
                id=workflow_run.id,
                name=workflow_run.name,
                url=workflow_run.html_url,
                status=workflow_run.status,
                conclusion=workflow_run.conclusion,
                created_at=workflow_run.created_at,
            )
            for workflow_run in self.workflow_runs
        ]


class RestGithubClient:
    def __init__(
        self,
        aiohttp_client: aiohttp.ClientSession,
        token: str,
    ) -> None:
        self._aiohttp_client = aiohttp_client
        self._token = token

    @classmethod
    def from_token(cls, token: str) -> typing.Self:
        aiohttp_client = aiohttp.ClientSession()
        return cls(aiohttp_client=aiohttp_client, token=token)

    async def dispose(self) -> None:
        await self._aiohttp_client.close()

    async def _request(
        self,
        request: BaseRequest,
        response_model: type[ResponseT],
    ) -> ResponseT:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
        }
        logger.debug("Requesting method(%s) url(%s) params(%s)", request.method, request.url, request.params)
        async with self._aiohttp_client.request(
            method=request.method,
            url=request.url,
            params=request.params,
            headers=headers,
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return response_model.model_validate(data)

    async def get_repository_workflow_runs(
        self,
        request: GetRepositoryWorkflowRunsRequest,
    ) -> typing.AsyncGenerator[github_models.WorkflowRun, None]:
        while True:
            response = await self._request(request, GetRepositoryWorkflowRunsResponse)
            if not response.workflow_runs:
                return

            for workflow_run in response.to_dataclass():
                yield workflow_run

            request.page += 1


__all__ = [
    "GetRepositoryWorkflowRunsRequest",
    "RestGithubClient",
]

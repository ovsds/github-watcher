import abc
import dataclasses
import datetime
import logging
import typing

import aiohttp
import pydantic

import lib.github.models as github_models
import lib.utils.pydantic as pydantic_utils

logger = logging.getLogger(__name__)


class BaseRequest(abc.ABC):
    @property
    @abc.abstractmethod
    def method(self) -> str: ...

    @property
    @abc.abstractmethod
    def url(self) -> str: ...

    @property
    @abc.abstractmethod
    def params(self) -> dict[str, typing.Any]: ...


class BaseResponse(pydantic_utils.BaseModel):
    def to_dataclass(self) -> typing.Any:
        raise NotImplementedError


# https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository
@dataclasses.dataclass(frozen=True)
class GetRepositoryWorkflowRunsRequest(BaseRequest):
    owner: str
    repository: str
    created_after: datetime.datetime
    per_page: int = 100
    page: int = 1
    exclude_pull_requests: bool = True

    @property
    def method(self) -> str:
        return "GET"

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
    class WorkflowRun(pydantic_utils.BaseModel):
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


# https://docs.github.com/en/rest/teams/members#list-team-members
@dataclasses.dataclass(frozen=True)
class GetOrganizationTeamMembersRequest(BaseRequest):
    owner: github_models.OwnerName
    team_slug: github_models.TeamSlug

    role: typing.Literal["member", "maintainer", "all"] = "all"
    per_page: int = 100
    page: int = 1

    @property
    def method(self) -> str:
        return "GET"

    @property
    def url(self) -> str:
        return f"https://api.github.com/orgs/{self.owner}/teams/{self.team_slug}/members"

    @property
    def params(self) -> dict[str, typing.Any]:
        return {
            "role": self.role,
            "per_page": self.per_page,
            "page": self.page,
        }


class _TeamMember(pydantic_utils.BaseModel):
    login: github_models.UserLogin


class GetOrganizationTeamMembersResponse(BaseResponse, pydantic.RootModel[list[_TeamMember]]):
    root: list[_TeamMember]

    def to_dataclass(self) -> list[github_models.UserLogin]:
        return [member.login for member in self.root]


@dataclasses.dataclass(frozen=True)
class RestGithubClient:
    aiohttp_client: aiohttp.ClientSession
    token: str

    class BaseError(Exception): ...

    class NotFoundError(BaseError): ...

    class UnknownResponseError(BaseError): ...

    @classmethod
    def from_token(cls, token: str) -> typing.Self:
        aiohttp_client = aiohttp.ClientSession()
        return cls(aiohttp_client=aiohttp_client, token=token)

    async def dispose(self) -> None:
        await self.aiohttp_client.close()

    async def _request(
        self,
        request: BaseRequest,
    ) -> typing.Any:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        logger.debug("Requesting method(%s) url(%s) params(%s)", request.method, request.url, request.params)
        async with self.aiohttp_client.request(
            method=request.method,
            url=request.url,
            params=request.params,
            headers=headers,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def _get_repository_workflow_runs(
        self,
        request: GetRepositoryWorkflowRunsRequest,
    ) -> GetRepositoryWorkflowRunsResponse:
        try:
            raw_data = await self._request(request)
        except aiohttp.ClientResponseError as e:  # pragma: no cover
            logger.exception("Unknown response error")
            raise self.UnknownResponseError from e

        return GetRepositoryWorkflowRunsResponse.model_validate(raw_data)

    async def get_repository_workflow_runs(
        self,
        request: GetRepositoryWorkflowRunsRequest,
    ) -> typing.AsyncGenerator[github_models.WorkflowRun, None]:
        page = request.page

        while True:
            response = await self._get_repository_workflow_runs(
                request=GetRepositoryWorkflowRunsRequest(
                    owner=request.owner,
                    repository=request.repository,
                    created_after=request.created_after,
                    page=page,
                    per_page=request.per_page,
                ),
            )
            if not response.workflow_runs:
                return

            for workflow_run in response.to_dataclass():
                yield workflow_run

            page += 1

    async def _get_organization_team_members(
        self,
        request: GetOrganizationTeamMembersRequest,
    ) -> GetOrganizationTeamMembersResponse:
        try:
            raw_data = await self._request(request)
            return GetOrganizationTeamMembersResponse.model_validate(raw_data)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.info(e.message)
                raise self.NotFoundError from e

            logger.exception("Unknown response error")  # pragma: no cover
            raise self.UnknownResponseError from e  # pragma: no cover

    async def get_organization_team_members(
        self,
        request: GetOrganizationTeamMembersRequest,
    ) -> typing.AsyncGenerator[github_models.UserLogin, None]:
        page = request.page
        while True:
            response = await self._get_organization_team_members(
                request=GetOrganizationTeamMembersRequest(
                    owner=request.owner,
                    team_slug=request.team_slug,
                    page=page,
                    per_page=request.per_page,
                ),
            )
            if not response.root:
                return

            for member in response.to_dataclass():
                yield member

            page += 1


__all__ = [
    "GetOrganizationTeamMembersRequest",
    "GetRepositoryWorkflowRunsRequest",
    "RestGithubClient",
]

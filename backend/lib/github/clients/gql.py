import abc
import contextlib
import dataclasses
import datetime
import logging
import typing

import gql
import gql.transport.aiohttp as gql_aiohttp
import graphql
import pydantic
import pydantic.alias_generators as pydantic_alias_generators

import lib.github.models as github_models

logger = logging.getLogger(__name__)


class BaseRequest(abc.ABC):
    document: graphql.DocumentNode = NotImplemented

    @property
    def params(self) -> dict[str, typing.Any]:
        raise NotImplementedError


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(alias_generator=pydantic_alias_generators.to_camel)


class BaseResponse(BaseModel):
    def to_dataclass(self) -> typing.Any:
        raise NotImplementedError


ResponseT = typing.TypeVar("ResponseT", bound=BaseResponse)


@dataclasses.dataclass
class GetRepositoriesRequest(BaseRequest):
    owner: str
    limit: int = 100
    after: str | None = None

    document: graphql.DocumentNode = gql.gql(
        """
        query myOrgRepos($query: String!, $limit: Int!, $after: String) {
            search(query: $query, type: REPOSITORY, first: $limit, after: $after) {
                nodes {
                    ... on Repository {
                        name
                        owner {
                            login
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
        """
    )

    @property
    def params(self) -> dict[str, typing.Any]:
        return {
            "query": f"org:{self.owner}",
            "limit": self.limit,
            "after": self.after,
        }


class GetRepositoriesResponse(BaseResponse):
    class Search(BaseModel):
        class Repository(BaseModel):
            class Owner(BaseModel):
                login: str

            name: str
            owner: Owner

        class PageInfo(BaseModel):
            end_cursor: str
            has_next_page: bool

        nodes: list[Repository]
        page_info: PageInfo

    search: Search

    def to_dataclass(self) -> list[github_models.Repository]:
        return [
            github_models.Repository(
                name=repository.name,
                owner=repository.owner.login,
            )
            for repository in self.search.nodes
        ]


@dataclasses.dataclass
class GetRepositoryIssuesRequest(BaseRequest):
    owner: str
    repository: str
    created_after: datetime.datetime
    limit: int = 100

    document: graphql.DocumentNode = gql.gql(
        """
        query getIssues($query: String!, $limit: Int!) {
            search(query: $query, type: ISSUE, first: $limit) {
                nodes {
                    ... on Issue {
                        id
                        url
                        title
                        body
                        createdAt
                        author {
                            login
                        }
                    }
                }
            }
        }
        """
    )

    @property
    def params(self) -> dict[str, typing.Any]:
        query = [
            f"repo:{self.owner}/{self.repository}",
            "is:issue",
            f"created:>{self.created_after.isoformat()}",
            "sort:created-asc",
        ]
        return {
            "query": " ".join(query),
            "limit": self.limit,
        }


class GetRepositoryIssuesResponse(BaseResponse):
    class Search(BaseModel):
        class Issue(BaseModel):
            class Author(BaseModel):
                login: str

            id: str
            url: str
            title: str
            body: str
            created_at: datetime.datetime
            author: Author | None

        nodes: list[Issue]

    search: Search

    def to_dataclass(self) -> list[github_models.Issue]:
        return [
            github_models.Issue(
                id=issue.id,
                author=issue.author.login if issue.author else None,
                url=issue.url,
                title=issue.title,
                body=issue.body,
                created_at=issue.created_at,
            )
            for issue in self.search.nodes
        ]


@dataclasses.dataclass
class GetRepositoryPRsRequest(BaseRequest):
    owner: str
    repository: str
    created_after: datetime.datetime
    limit: int = 100

    document: graphql.DocumentNode = gql.gql(
        """
        query getPRs($query: String!, $limit: Int!) {
            search(query: $query, type: ISSUE, first: $limit) {
                nodes {
                    ... on PullRequest {
                        id
                        url
                        title
                        body
                        createdAt
                        author {
                            login
                        }
                    }
                }
            }
        }
        """
    )

    @property
    def params(self) -> dict[str, typing.Any]:
        query = [
            f"repo:{self.owner}/{self.repository}",
            "is:pr",
            f"created:>{self.created_after.isoformat()}",
            "sort:created-asc",
        ]
        return {
            "query": " ".join(query),
            "limit": self.limit,
        }


class GetRepositoryPRsResponse(BaseResponse):
    class Search(BaseModel):
        class PR(BaseModel):
            class Author(BaseModel):
                login: str

            id: str
            url: str
            title: str
            body: str
            created_at: datetime.datetime
            author: Author | None

        nodes: list[PR]

    search: Search

    def to_dataclass(self) -> list[github_models.PullRequest]:
        return [
            github_models.PullRequest(
                id=pr.id,
                author=pr.author.login if pr.author else None,
                url=pr.url,
                title=pr.title,
                body=pr.body,
                created_at=pr.created_at,
            )
            for pr in self.search.nodes
        ]


class GqlGithubClient:
    def __init__(self, token: str) -> None:
        self._token = token

    @contextlib.asynccontextmanager
    async def gql_client(self) -> typing.AsyncGenerator[gql.Client, None]:
        gql_transport = gql_aiohttp.AIOHTTPTransport(
            url="https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {self._token}"},
        )
        gql_client = gql.Client(
            transport=gql_transport,
            fetch_schema_from_transport=False,
        )
        try:
            yield gql_client
        finally:
            await gql_transport.close()

    async def _request(self, request: BaseRequest, response_model: type[ResponseT]) -> ResponseT:
        logger.debug("Requesting document(%s) params(%s)", request.document, request.params)
        async with self.gql_client() as gql_client:
            response = await gql_client.execute_async(
                document=request.document,
                variable_values=request.params,
            )
        parsed_response = response_model.model_validate(response)

        return parsed_response

    async def get_repositories(
        self,
        request: GetRepositoriesRequest,
    ) -> list[github_models.Repository]:
        result: list[github_models.Repository] = []
        while True:
            response = await self._request(request, GetRepositoriesResponse)
            result.extend(response.to_dataclass())
            if not response.search.page_info.has_next_page:
                break
            request.after = response.search.page_info.end_cursor

        return result

    async def get_repository_issues(
        self,
        request: GetRepositoryIssuesRequest,
    ) -> list[github_models.Issue]:
        response = await self._request(request, GetRepositoryIssuesResponse)
        return response.to_dataclass()

    async def get_repository_pull_requests(
        self,
        request: GetRepositoryPRsRequest,
    ) -> list[github_models.PullRequest]:
        response = await self._request(request, GetRepositoryPRsResponse)
        return response.to_dataclass()


__all__ = [
    "GetRepositoriesRequest",
    "GetRepositoryIssuesRequest",
    "GetRepositoryPRsRequest",
    "GqlGithubClient",
]

import pytest

import lib.github.clients as github_clients
import lib.github.models as github_models


@pytest.mark.asyncio
async def test_default(github_gql_client: github_clients.GqlGithubClient):
    iterator = github_gql_client.get_repositories(
        request=github_clients.GetRepositoriesRequest(
            owner="python",
        ),
    )

    assert await anext(iterator) == github_models.Repository(
        name="cpython",
        owner="python",
    )


@pytest.mark.asyncio
async def test_multiple_requests(github_gql_client: github_clients.GqlGithubClient):
    iterator = github_gql_client.get_repositories(
        request=github_clients.GetRepositoriesRequest(
            owner="python",
            limit=1,
        ),
    )

    assert await anext(iterator) == github_models.Repository(
        name="cpython",
        owner="python",
    )
    assert await anext(iterator) == github_models.Repository(
        name="mypy",
        owner="python",
    )


@pytest.mark.asyncio
async def test_finite(github_gql_client: github_clients.GqlGithubClient):
    iterator = github_gql_client.get_repositories(
        request=github_clients.GetRepositoriesRequest(
            owner="definetly-not-a-real-org",
        ),
    )

    assert len([item async for item in iterator]) == 0

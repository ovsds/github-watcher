import datetime

import pytest

import lib.github.clients as github_clients


@pytest.mark.asyncio
async def test__default(github_gql_client: github_clients.GqlGithubClient):
    pull_requests = await github_gql_client.get_repository_pull_requests(
        request=github_clients.GetRepositoryPRsRequest(
            owner="python",
            repository="cpython",
            created_after=datetime.datetime(2025, 1, 1),
            limit=1,
        ),
    )

    assert len(pull_requests) == 1
    pull_request = pull_requests[0]
    assert pull_request.id == "PR_kwDOBN0Z8c6GhTCQ"
    assert pull_request.author == "paulie4"
    assert pull_request.url == "https://github.com/python/cpython/pull/128389"
    assert pull_request.title == "gh-128388: pyrepl on Windows: add meta and ctrl+arrow keybindings"
    assert pull_request.created_at == datetime.datetime(2025, 1, 1, 5, 54, 29, tzinfo=datetime.UTC)

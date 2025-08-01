import datetime

import pytest

import lib.github.clients as github_clients


@pytest.mark.asyncio
async def test_default(github_gql_client: github_clients.GqlGithubClient):
    """Test getting issues from a repository with default parameters."""
    issues = await github_gql_client.get_repository_issues(
        request=github_clients.GetRepositoryIssuesRequest(
            owner="python",
            repository="cpython",
            created_after=datetime.datetime(2025, 1, 1),
            limit=1,
        ),
    )

    assert len(issues) == 1
    issue = issues[0]
    assert issue.id == "I_kwDOBN0Z8c6kzGKa"
    assert issue.author == "paulie4"
    assert issue.url == "https://github.com/python/cpython/issues/128388"
    assert issue.title == "`pyrepl` on Windows: add Ctrl+← and Ctrl+→ word-skipping and other keybindings"
    assert issue.created_at == datetime.datetime(2025, 1, 1, 5, 33, 57, tzinfo=datetime.UTC)

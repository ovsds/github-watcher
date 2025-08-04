import pytest

import lib.github.clients as github_clients


@pytest.mark.asyncio
async def test_default(github_rest_client: github_clients.RestGithubClient):
    iterator = github_rest_client.get_organization_team_members(
        request=github_clients.GetOrganizationTeamMembersRequest(
            owner="ovsds-example-organization",
            team_slug="github-watcher-repository-test",
        ),
    )

    members = [member async for member in iterator]
    assert members == ["ovsds", "ovsds-personal-robot"]


@pytest.mark.asyncio
async def test_per_page(github_rest_client: github_clients.RestGithubClient):
    iterator = github_rest_client.get_organization_team_members(
        request=github_clients.GetOrganizationTeamMembersRequest(
            owner="ovsds-example-organization",
            team_slug="github-watcher-repository-test",
            per_page=1,
        ),
    )

    members = [member async for member in iterator]
    assert members == ["ovsds", "ovsds-personal-robot"]


@pytest.mark.asyncio
async def test_no_team(github_rest_client: github_clients.RestGithubClient):
    iterator = github_rest_client.get_organization_team_members(
        request=github_clients.GetOrganizationTeamMembersRequest(
            owner="ovsds-example-organization",
            team_slug="github-watcher-repository-test-not-exists",
        ),
    )
    with pytest.raises(github_clients.RestGithubClient.NotFoundError):
        await anext(iterator)


@pytest.mark.asyncio
async def test_no_organization(github_rest_client: github_clients.RestGithubClient):
    iterator = github_rest_client.get_organization_team_members(
        request=github_clients.GetOrganizationTeamMembersRequest(
            owner="ovsds-example-organization-not-exists",
            team_slug="github-watcher-repository-test",
        ),
    )
    with pytest.raises(github_clients.RestGithubClient.NotFoundError):
        await anext(iterator)

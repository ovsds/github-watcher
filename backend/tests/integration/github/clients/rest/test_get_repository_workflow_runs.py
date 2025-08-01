import datetime

import pytest

import lib.github.clients as github_clients
import lib.github.models as github_models


@pytest.mark.asyncio
async def test_default(github_rest_client: github_clients.RestGithubClient):
    iterator = github_rest_client.get_repository_workflow_runs(
        request=github_clients.GetRepositoryWorkflowRunsRequest(
            owner="ovsds",
            repository="github-watcher",
            created_after=datetime.datetime(2025, 1, 1),
        ),
    )

    workflow_run = await anext(iterator)
    assert isinstance(workflow_run, github_models.WorkflowRun)


@pytest.mark.asyncio
async def test_per_page(github_rest_client: github_clients.RestGithubClient):
    iterator = github_rest_client.get_repository_workflow_runs(
        request=github_clients.GetRepositoryWorkflowRunsRequest(
            owner="ovsds",
            repository="github-watcher",
            created_after=datetime.datetime(2025, 1, 1),
            per_page=1,
        ),
    )

    for _ in range(2):
        workflow_run = await anext(iterator)
        assert isinstance(workflow_run, github_models.WorkflowRun)


@pytest.mark.asyncio
async def test_finite(github_rest_client: github_clients.RestGithubClient):
    iterator = github_rest_client.get_repository_workflow_runs(
        request=github_clients.GetRepositoryWorkflowRunsRequest(
            owner="ovsds",
            repository="github-watcher",
            created_after=datetime.datetime(3025, 1, 1),
        ),
    )
    assert len([item async for item in iterator]) == 0

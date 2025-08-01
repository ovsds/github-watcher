import typing

import pytest_asyncio

import lib.github.clients as github_clients
import tests.settings as test_settings


@pytest_asyncio.fixture(name="github_rest_client")
async def github_rest_client_fixture(
    settings: test_settings.Settings,
) -> typing.AsyncGenerator[github_clients.RestGithubClient, None]:
    client = github_clients.RestGithubClient.from_token(settings.github_token)
    try:
        yield client
    finally:
        await client.dispose()

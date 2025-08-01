import pytest

import lib.github.clients as github_clients
import tests.settings as test_settings


@pytest.fixture(name="github_gql_client")
def github_gql_client_fixture(settings: test_settings.Settings) -> github_clients.GqlGithubClient:
    return github_clients.GqlGithubClient(token=settings.github_token)

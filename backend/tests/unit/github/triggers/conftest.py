import pytest

import lib.github.triggers as github_triggers


@pytest.fixture(name="register_default_plugins", autouse=True, scope="session")
def register_default_plugins_fixture() -> None:
    github_triggers.register_default_plugins()

import datetime

import pytest

import lib.github.models as github_models
import lib.github.triggers as github_triggers


@pytest.fixture(name="pr")
def pr_fixture() -> github_models.PullRequest:
    return github_models.PullRequest(
        id="test_id",
        author="test_author",
        url="test_url",
        title="test_title",
        body="test_body",
        created_at=datetime.datetime.now(),
    )


def test_is_applicable_default(pr: github_models.PullRequest):
    config = github_triggers.RepositoryPRCreatedSubtriggerConfig(
        id="test_id",
    )

    assert config.is_applicable(pr=pr)


def test_is_applicable_include_author(pr: github_models.PullRequest):
    config = github_triggers.RepositoryPRCreatedSubtriggerConfig(
        id="test_id",
        include_author=["test_author"],
    )
    assert config.is_applicable(pr=pr)


def test_is_applicable_include_author_not_matching(pr: github_models.PullRequest):
    config = github_triggers.RepositoryPRCreatedSubtriggerConfig(
        id="test_id",
        include_author=["other_author"],
    )
    assert not config.is_applicable(pr=pr)


def test_is_applicable_exclude_author(pr: github_models.PullRequest):
    config = github_triggers.RepositoryPRCreatedSubtriggerConfig(
        id="test_id",
        exclude_author=["other_author"],
    )
    assert config.is_applicable(pr=pr)


def test_is_applicable_exclude_author_matching(pr: github_models.PullRequest):
    config = github_triggers.RepositoryPRCreatedSubtriggerConfig(
        id="test_id",
        exclude_author=["test_author"],
    )
    assert not config.is_applicable(pr=pr)

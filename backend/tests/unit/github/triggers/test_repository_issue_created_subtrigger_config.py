import datetime

import pytest

import lib.github.models as github_models
import lib.github.triggers as github_triggers


@pytest.fixture(name="issue")
def issue_fixture() -> github_models.Issue:
    return github_models.Issue(
        id="test_id",
        author="test_author",
        url="test_url",
        title="test_title",
        body="test_body",
        created_at=datetime.datetime.now(),
    )


def test_is_applicable_default(issue: github_models.Issue):
    config = github_triggers.RepositoryIssueCreatedSubtriggerConfig(
        id="test_id",
    )

    assert config.is_applicable(issue=issue)


def test_is_applicable_include_author(issue: github_models.Issue):
    config = github_triggers.RepositoryIssueCreatedSubtriggerConfig(
        id="test_id",
        include_author=["test_author"],
    )
    assert config.is_applicable(issue=issue)


def test_is_applicable_include_author_not_matching(issue: github_models.Issue):
    config = github_triggers.RepositoryIssueCreatedSubtriggerConfig(
        id="test_id",
        include_author=["other_author"],
    )
    assert not config.is_applicable(issue=issue)


def test_is_applicable_exclude_author(issue: github_models.Issue):
    config = github_triggers.RepositoryIssueCreatedSubtriggerConfig(
        id="test_id",
        exclude_author=["other_author"],
    )
    assert config.is_applicable(issue=issue)


def test_is_applicable_exclude_author_matching(issue: github_models.Issue):
    config = github_triggers.RepositoryIssueCreatedSubtriggerConfig(
        id="test_id",
        exclude_author=["test_author"],
    )
    assert not config.is_applicable(issue=issue)


def test_is_applicable_include_and_exclude_author(issue: github_models.Issue):
    config = github_triggers.RepositoryIssueCreatedSubtriggerConfig(
        id="test_id",
        include_author=["test_author"],
        exclude_author=["test_author"],
    )
    assert not config.is_applicable(issue=issue)

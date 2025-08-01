import contextlib
import dataclasses
import datetime
import logging
import re
import typing
import warnings

import pydantic

import lib.github.clients as github_clients
import lib.github.models as github_models
import lib.task.base as task_base
import lib.task.protocols
import lib.utils.asyncio as asyncio_utils
import lib.utils.pydantic as pydantic_utils

logger = logging.getLogger(__name__)


class SubtriggerConfig(pydantic_utils.TypedBaseModel, pydantic_utils.IDMixinModel):
    @pydantic.model_validator(mode="before")
    @classmethod
    def set_default_id(cls, data: dict[str, typing.Any]) -> dict[str, typing.Any]:
        if "id" not in data:
            data["id"] = data["type"]
        return data


def _check_match(string: str, items: list[str] | None = None) -> bool:
    return items is not None and len(items) != 0 and string in items


def _check_regex_match(string: str, regex_items: list[str] | None = None) -> bool:
    return regex_items is not None and len(regex_items) != 0 and any(re.match(regex, string) for regex in regex_items)


def _check_included(
    string: str,
    include: list[str] | None = None,
    include_regex: list[str] | None = None,
) -> bool:
    return (
        (not include and not include_regex)
        or _check_match(string, include)
        or _check_regex_match(string, include_regex)
    )


def _check_excluded(
    string: str,
    exclude: list[str] | None = None,
    exclude_regex: list[str] | None = None,
) -> bool:
    return _check_match(string, exclude) or _check_regex_match(string, exclude_regex)


def _check_applicable(
    string: str,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    include_regex: list[str] | None = None,
    exclude_regex: list[str] | None = None,
) -> bool:
    return _check_included(string, include=include, include_regex=include_regex) and not _check_excluded(
        string, exclude=exclude, exclude_regex=exclude_regex
    )


class RepositoryIssueCreatedSubtriggerConfig(SubtriggerConfig):
    type_name: str = "repository_issue_created"

    include_author: list[str] = pydantic.Field(default_factory=list)
    exclude_author: list[str] = pydantic.Field(default_factory=list)
    include_title: list[str] = pydantic.Field(default_factory=list)
    exclude_title: list[str] = pydantic.Field(default_factory=list)
    include_title_regex: list[str] = pydantic.Field(default_factory=list)
    exclude_title_regex: list[str] = pydantic.Field(default_factory=list)

    def is_applicable(self, issue: github_models.Issue) -> bool:
        if issue.author is not None and not _check_applicable(
            issue.author,
            include=self.include_author,
            exclude=self.exclude_author,
        ):
            return False
        if not _check_applicable(
            issue.title,
            include=self.include_title,
            exclude=self.exclude_title,
            include_regex=self.include_title_regex,
            exclude_regex=self.exclude_title_regex,
        ):
            return False

        return True


class RepositoryPRCreatedSubtriggerConfig(SubtriggerConfig):
    type_name: str = "repository_pr_created"

    include_author: list[str] = pydantic.Field(default_factory=list)
    exclude_author: list[str] = pydantic.Field(default_factory=list)

    def is_applicable(self, pr: github_models.PullRequest) -> bool:
        if pr.author is not None and not _check_applicable(
            pr.author,
            include=self.include_author,
            exclude=self.exclude_author,
        ):
            return False

        return True


class RepositoryFailedWorkflowRunSubtriggerConfig(SubtriggerConfig):
    type_name: str = "repository_failed_workflow_run"

    include: list[str] = pydantic.Field(default_factory=list)
    exclude: list[str] = pydantic.Field(default_factory=list)

    def is_applicable(self, workflow_run: github_models.WorkflowRun) -> bool:
        if workflow_run.status != "completed":
            return False
        if workflow_run.conclusion != "failure":
            return False
        if not _check_applicable(
            workflow_run.name,
            include=self.include,
            exclude=self.exclude,
        ):
            return False

        return True


class GithubTriggerConfig(task_base.BaseTriggerConfig):
    token_secret: pydantic_utils.TypedAnnotation[task_base.BaseSecretConfig]
    owner: str
    repos: list[str] = pydantic.Field(default_factory=list)  # TODO 1.0.0: remove
    include_repos: list[str] = pydantic.Field(default_factory=list)
    exclude_repos: list[str] = pydantic.Field(default_factory=list)
    default_timedelta_seconds: int = 60 * 60 * 24  # 1 day
    subtriggers: typing.Annotated[
        list[pydantic.SerializeAsAny[SubtriggerConfig]],
        pydantic.BeforeValidator(SubtriggerConfig.list_factory),
        pydantic.AfterValidator(pydantic_utils.check_unique_ids),
    ]

    @property
    def default_timedelta(self) -> datetime.timedelta:
        return datetime.timedelta(seconds=self.default_timedelta_seconds)

    @pydantic.field_validator("repos", mode="after")
    @classmethod
    def check_repos(cls, v: list[str]) -> list[str]:
        if len(v) > 0:
            warnings.warn(
                "`repos` field is deprecated in GithubTriggerConfig, use include_repos instead. "
                "`repos` will be removed in 1.0.0",
                FutureWarning,
            )
        return v

    @property
    def _include_repos(self) -> list[str]:
        return list(set(self.repos) | set(self.include_repos))

    def is_repository_applicable(self, repository: github_models.Repository) -> bool:
        if self._include_repos and repository.name not in self._include_repos:
            return False
        if repository.name in self.exclude_repos:
            return False

        return True


class RepositoryIssueCreatedState(pydantic_utils.BaseModel):
    last_issue_created: datetime.datetime

    @classmethod
    def default_factory(cls, timedelta: datetime.timedelta) -> typing.Self:
        return cls(
            last_issue_created=datetime.datetime.now(tz=datetime.UTC) - timedelta,
        )


class RepositoryPRCreatedState(pydantic_utils.BaseModel):
    last_pr_created: datetime.datetime

    @classmethod
    def default_factory(cls, timedelta: datetime.timedelta) -> typing.Self:
        return cls(
            last_pr_created=datetime.datetime.now(tz=datetime.UTC) - timedelta,
        )


class RepositoryFailedWorkflowRunState(pydantic_utils.BaseModel):
    oldest_incomplete_created: datetime.datetime
    already_reported_failed_runs: set[github_models.WorkflowRun] = pydantic.Field(
        default_factory=set[github_models.WorkflowRun]
    )

    @classmethod
    def default_factory(cls, timedelta: datetime.timedelta) -> typing.Self:
        return cls(
            oldest_incomplete_created=datetime.datetime.now(tz=datetime.UTC) - timedelta,
        )


class GithubTriggerState(pydantic_utils.BaseModel):
    repository_issue_created: dict[str, RepositoryIssueCreatedState] = pydantic.Field(
        default_factory=dict[str, RepositoryIssueCreatedState]
    )
    repository_pr_created: dict[str, RepositoryPRCreatedState] = pydantic.Field(
        default_factory=dict[str, RepositoryPRCreatedState]
    )
    repository_failed_workflow_run: dict[str, RepositoryFailedWorkflowRunState] = pydantic.Field(
        default_factory=dict[str, RepositoryFailedWorkflowRunState]
    )


@dataclasses.dataclass(frozen=True)
class GithubTriggerProcessor(task_base.TriggerProcessor[GithubTriggerConfig]):
    config: GithubTriggerConfig
    raw_state: lib.task.protocols.StateProtocol
    gql_github_client: github_clients.GqlGithubClient
    rest_github_client: github_clients.RestGithubClient

    @classmethod
    def from_config(
        cls,
        config: GithubTriggerConfig,
        state: lib.task.protocols.StateProtocol,
    ) -> typing.Self:
        gql_github_client = github_clients.GqlGithubClient(token=config.token_secret.value)
        rest_github_client = github_clients.RestGithubClient.from_token(token=config.token_secret.value)

        return cls(
            raw_state=state,
            gql_github_client=gql_github_client,
            rest_github_client=rest_github_client,
            config=config,
        )

    async def dispose(self) -> None:
        await self.rest_github_client.dispose()

    @contextlib.asynccontextmanager
    async def _acquire_state(self) -> typing.AsyncIterator[GithubTriggerState]:
        async with self.raw_state.acquire() as raw_state:
            if raw_state is None:
                raw_state = {}

            state = GithubTriggerState.model_validate(raw_state)
            try:
                yield state
            finally:
                await self.raw_state.set(state.model_dump(mode="json"))

    async def produce_events(self) -> typing.AsyncGenerator[task_base.Event, None]:
        repositories: list[github_models.Repository] = []

        async for repository in self.gql_github_client.get_repositories(
            github_clients.GetRepositoriesRequest(
                owner=self.config.owner,
            )
        ):
            if self.config.is_repository_applicable(repository):
                repositories.append(repository)

        async with self._acquire_state() as state:
            async for event in asyncio_utils.GatherIterators(
                self._process_subtrigger_factory(
                    subtrigger=subtrigger,
                    state=state,
                    repositories=repositories,
                )
                for subtrigger in self.config.subtriggers
            ):
                yield event

    def _process_subtrigger_factory(
        self,
        subtrigger: SubtriggerConfig,
        state: GithubTriggerState,
        repositories: list[github_models.Repository],
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        if isinstance(subtrigger, RepositoryIssueCreatedSubtriggerConfig):
            return self._process_all_repository_issue_created(
                state=state,
                subtrigger=subtrigger,
                repositories=repositories,
            )
        if isinstance(subtrigger, RepositoryPRCreatedSubtriggerConfig):
            return self._process_all_repository_pr_created(
                state=state,
                subtrigger=subtrigger,
                repositories=repositories,
            )
        if isinstance(subtrigger, RepositoryFailedWorkflowRunSubtriggerConfig):
            return self._process_all_repository_failed_workflow_run(
                state=state,
                subtrigger=subtrigger,
                repositories=repositories,
            )

        raise ValueError(f"Unknown subtrigger: {subtrigger}")

    async def _process_all_repository_issue_created(
        self,
        state: GithubTriggerState,
        subtrigger: RepositoryIssueCreatedSubtriggerConfig,
        repositories: list[github_models.Repository],
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        async for event in asyncio_utils.GatherIterators(
            self._process_repository_issue_created(
                state=state,
                subtrigger=subtrigger,
                repository=repository.name,
            )
            for repository in repositories
        ):
            yield event

    async def _process_repository_issue_created(
        self,
        state: GithubTriggerState,
        subtrigger: RepositoryIssueCreatedSubtriggerConfig,
        repository: str,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        if repository not in state.repository_issue_created:
            state.repository_issue_created[repository] = RepositoryIssueCreatedState.default_factory(
                self.config.default_timedelta,
            )
        repository_state = state.repository_issue_created[repository]
        last_issue_created = repository_state.last_issue_created

        while True:
            issues = await self.gql_github_client.get_repository_issues(
                github_clients.GetRepositoryIssuesRequest(
                    owner=self.config.owner,
                    repository=repository,
                    created_after=last_issue_created,
                )
            )
            if not issues:
                break

            for issue in issues:
                if subtrigger.is_applicable(issue):
                    yield task_base.Event(
                        id=f"issue_created__{issue.id}",
                        title=f"📋New issue in {self.config.owner}/{repository}",
                        body=f"Issue created by {issue.author}: {issue.title}",
                        url=issue.url,
                    )
                last_issue_created = max(last_issue_created, issue.created_at)
                repository_state.last_issue_created = last_issue_created

    async def _process_all_repository_pr_created(
        self,
        state: GithubTriggerState,
        subtrigger: RepositoryPRCreatedSubtriggerConfig,
        repositories: list[github_models.Repository],
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        async for event in asyncio_utils.GatherIterators(
            self._process_repository_pr_created(
                state=state,
                subtrigger=subtrigger,
                repository=repository.name,
            )
            for repository in repositories
        ):
            yield event

    async def _process_repository_pr_created(
        self,
        state: GithubTriggerState,
        subtrigger: RepositoryPRCreatedSubtriggerConfig,
        repository: str,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        if repository not in state.repository_pr_created:
            state.repository_pr_created[repository] = RepositoryPRCreatedState.default_factory(
                self.config.default_timedelta,
            )
        repository_state = state.repository_pr_created[repository]
        last_pr_created = repository_state.last_pr_created

        while True:
            prs = await self.gql_github_client.get_repository_pull_requests(
                github_clients.GetRepositoryPRsRequest(
                    owner=self.config.owner,
                    repository=repository,
                    created_after=last_pr_created,
                )
            )
            if not prs:
                break

            for pr in prs:
                if subtrigger.is_applicable(pr):
                    yield task_base.Event(
                        id=f"pr_created__{pr.id}",
                        title=f"🛠New PR in {self.config.owner}/{repository}",
                        body=f"PR created by {pr.author}: {pr.title}",
                        url=pr.url,
                    )
                last_pr_created = max(last_pr_created, pr.created_at)
                repository_state.last_pr_created = last_pr_created

    async def _process_all_repository_failed_workflow_run(
        self,
        state: GithubTriggerState,
        subtrigger: RepositoryFailedWorkflowRunSubtriggerConfig,
        repositories: list[github_models.Repository],
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        async for event in asyncio_utils.GatherIterators(
            self._process_repository_failed_workflow_run(
                state=state,
                subtrigger=subtrigger,
                repository=repository.name,
            )
            for repository in repositories
        ):
            yield event

    async def _process_repository_failed_workflow_run(
        self,
        state: GithubTriggerState,
        subtrigger: RepositoryFailedWorkflowRunSubtriggerConfig,
        repository: str,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        if repository not in state.repository_failed_workflow_run:
            state.repository_failed_workflow_run[repository] = RepositoryFailedWorkflowRunState.default_factory(
                self.config.default_timedelta,
            )
        repository_state = state.repository_failed_workflow_run[repository]

        oldest_incomplete_created = None
        last_created = None

        async for workflow_run in self.rest_github_client.get_repository_workflow_runs(
            request=github_clients.GetRepositoryWorkflowRunsRequest(
                owner=self.config.owner,
                repository=repository,
                created_after=repository_state.oldest_incomplete_created,
            ),
        ):
            if (
                subtrigger.is_applicable(workflow_run)
                and workflow_run not in repository_state.already_reported_failed_runs
            ):
                yield task_base.Event(
                    id=f"failed_workflow_run__{self.config.owner}__{repository}__{workflow_run.id}",
                    title=f"🔥Failed workflow run in {self.config.owner}/{repository}",
                    body=f"Workflow run {workflow_run.name} failed",
                    url=workflow_run.url,
                )
                repository_state.already_reported_failed_runs.add(workflow_run)

            if last_created is None:
                last_created = workflow_run.created_at
            else:
                last_created = max(last_created, workflow_run.created_at)

            if workflow_run.status != "completed":
                if oldest_incomplete_created is None:
                    oldest_incomplete_created = workflow_run.created_at
                else:
                    oldest_incomplete_created = min(oldest_incomplete_created, workflow_run.created_at)

        oldest_incomplete_created = (
            oldest_incomplete_created or last_created or repository_state.oldest_incomplete_created
        )
        repository_state.oldest_incomplete_created = oldest_incomplete_created
        repository_state.already_reported_failed_runs = {
            run for run in repository_state.already_reported_failed_runs if run.created_at >= oldest_incomplete_created
        }


def register_default_plugins() -> None:
    logger.info("Registering default github triggers plugins")
    task_base.register_trigger(
        name="github",
        config_class=GithubTriggerConfig,
        processor_class=GithubTriggerProcessor,
    )

    SubtriggerConfig.register("repository_issue_created", RepositoryIssueCreatedSubtriggerConfig)
    SubtriggerConfig.register("repository_pr_created", RepositoryPRCreatedSubtriggerConfig)
    SubtriggerConfig.register("repository_failed_workflow_run", RepositoryFailedWorkflowRunSubtriggerConfig)


__all__ = [
    "GithubTriggerConfig",
    "GithubTriggerProcessor",
    "RepositoryIssueCreatedSubtriggerConfig",
    "register_default_plugins",
]

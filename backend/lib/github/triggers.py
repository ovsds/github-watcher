import contextlib
import datetime
import logging
import typing

import pydantic

import lib.github.clients as github_clients
import lib.github.models as github_models
import lib.task.base as task_base
import lib.task.repositories as task_repositories
import lib.utils.asyncio as asyncio_utils
import lib.utils.pydantic as pydantic_utils

logger = logging.getLogger(__name__)


DEFAULT_TIMEDELTA = datetime.timedelta(days=10)


class SubtriggerConfig(pydantic_utils.BaseModel, pydantic_utils.IDMixinModel):
    type: str

    @pydantic.model_validator(mode="before")
    @classmethod
    def set_default_id(cls, data: dict[str, typing.Any]) -> dict[str, typing.Any]:
        if "id" not in data:
            data["id"] = data["type"]
        return data

    @classmethod
    def factory(cls, v: typing.Any, info: pydantic.ValidationInfo) -> "SubtriggerConfig":
        assert isinstance(v, dict)
        assert "type" in v

        if v["type"] == "repository_issue_created":
            return RepositoryIssueCreatedSubtriggerConfig.model_validate(v)
        if v["type"] == "repository_pr_created":
            return RepositoryPRCreatedSubtriggerConfig.model_validate(v)
        if v["type"] == "repository_failed_workflow_run":
            return RepositoryFailedWorkflowRunSubtriggerConfig.model_validate(v)

        raise ValueError(f"Unknown subtrigger type: {v['type']}")


class RepositoryIssueCreatedSubtriggerConfig(SubtriggerConfig): ...


class RepositoryPRCreatedSubtriggerConfig(SubtriggerConfig): ...


class RepositoryFailedWorkflowRunSubtriggerConfig(SubtriggerConfig): ...


class GithubTriggerConfig(task_base.BaseTriggerConfig):
    token_secret: task_base.SecretConfigPydanticAnnotation
    owner: str
    repos: list[str]
    subtriggers: typing.Annotated[
        list[pydantic.SerializeAsAny[SubtriggerConfig]],
        pydantic.BeforeValidator(pydantic_utils.make_list_factory(SubtriggerConfig.factory)),
        pydantic.AfterValidator(pydantic_utils.check_unique_ids),
    ]


class RepositoryIssueCreatedState(pydantic_utils.BaseModel):
    last_issue_created: datetime.datetime

    @classmethod
    def default_factory(cls) -> typing.Self:
        return cls(
            last_issue_created=datetime.datetime.now(tz=datetime.UTC) - DEFAULT_TIMEDELTA,
        )


class RepositoryPRCreatedState(pydantic_utils.BaseModel):
    last_pr_created: datetime.datetime

    @classmethod
    def default_factory(cls) -> typing.Self:
        return cls(
            last_pr_created=datetime.datetime.now(tz=datetime.UTC) - DEFAULT_TIMEDELTA,
        )


class RepositoryFailedWorkflowRunState(pydantic_utils.BaseModel):
    oldest_incomplete_created: datetime.datetime
    already_reported_failed_runs: set[github_models.WorkflowRun] = pydantic.Field(default_factory=set)

    @classmethod
    def default_factory(cls) -> typing.Self:
        return cls(
            oldest_incomplete_created=datetime.datetime.now(tz=datetime.UTC) - DEFAULT_TIMEDELTA,
        )


class GithubTriggerState(pydantic_utils.BaseModel):
    repository_issue_created: dict[str, RepositoryIssueCreatedState] = pydantic.Field(default_factory=dict)
    repository_pr_created: dict[str, RepositoryPRCreatedState] = pydantic.Field(default_factory=dict)
    repository_failed_workflow_run: dict[str, RepositoryFailedWorkflowRunState] = pydantic.Field(default_factory=dict)


class GithubTriggerProcessor(task_base.TriggerProcessor[GithubTriggerConfig]):
    def __init__(
        self,
        raw_state: task_repositories.StateProtocol,
        gql_github_client: github_clients.GqlGithubClient,
        rest_github_client: github_clients.RestGithubClient,
        config: GithubTriggerConfig,
    ) -> None:
        self._raw_state = raw_state
        self._gql_github_client = gql_github_client
        self._rest_github_client = rest_github_client
        self._config = config

    @classmethod
    def from_config(
        cls,
        config: GithubTriggerConfig,
        state: task_repositories.StateProtocol,
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
        await self._rest_github_client.dispose()

    @contextlib.asynccontextmanager
    async def _acquire_state(self) -> typing.AsyncIterator[GithubTriggerState]:
        async with self._raw_state.acquire() as raw_state:
            if raw_state is None:
                raw_state = {}

            state = GithubTriggerState.model_validate(raw_state)
            try:
                yield state
            finally:
                await self._raw_state.set(state.model_dump(mode="json"))

    async def produce_events(self) -> typing.AsyncGenerator[task_base.Event, None]:
        async with self._acquire_state() as state:
            async for event in asyncio_utils.GatherIterators(
                self._process_subtrigger_factory(subtrigger=subtrigger, state=state)
                for subtrigger in self._config.subtriggers
            ):
                yield event

    def _process_subtrigger_factory(
        self,
        subtrigger: SubtriggerConfig,
        state: GithubTriggerState,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        if isinstance(subtrigger, RepositoryIssueCreatedSubtriggerConfig):
            return self._process_all_repository_issue_created(state=state)
        if isinstance(subtrigger, RepositoryPRCreatedSubtriggerConfig):
            return self._process_all_repository_pr_created(state=state)
        if isinstance(subtrigger, RepositoryFailedWorkflowRunSubtriggerConfig):
            return self._process_all_repository_failed_workflow_run(state=state)

        raise ValueError(f"Unknown subtrigger: {subtrigger}")

    async def _process_all_repository_issue_created(
        self,
        state: GithubTriggerState,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        async for event in asyncio_utils.GatherIterators(
            self._process_repository_issue_created(state=state, repo=repo) for repo in self._config.repos
        ):
            yield event

    async def _process_repository_issue_created(
        self,
        state: GithubTriggerState,
        repo: str,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        if repo not in state.repository_issue_created:
            state.repository_issue_created[repo] = RepositoryIssueCreatedState.default_factory()
        repository_state = state.repository_issue_created[repo]
        last_issue_created = repository_state.last_issue_created

        while True:
            issues = await self._gql_github_client.get_repository_issues(
                github_clients.GetRepositoryIssuesRequest(
                    owner=self._config.owner,
                    repo=repo,
                    created_after=last_issue_created,
                )
            )
            if not issues:
                break

            for issue in issues:
                yield task_base.Event(
                    id=f"issue_created__{issue.id}",
                    title=f"📋New issue in {self._config.owner}/{repo}",
                    body=f"Issue created by {issue.author}: {issue.title}",
                    url=issue.url,
                )
                last_issue_created = max(last_issue_created, issue.created_at)
                repository_state.last_issue_created = last_issue_created

    async def _process_all_repository_pr_created(
        self,
        state: GithubTriggerState,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        async for event in asyncio_utils.GatherIterators(
            self._process_repository_pr_created(state=state, repo=repo) for repo in self._config.repos
        ):
            yield event

    async def _process_repository_pr_created(
        self,
        state: GithubTriggerState,
        repo: str,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        if repo not in state.repository_pr_created:
            state.repository_pr_created[repo] = RepositoryPRCreatedState.default_factory()
        repository_state = state.repository_pr_created[repo]
        last_pr_created = repository_state.last_pr_created

        while True:
            prs = await self._gql_github_client.get_repository_pull_requests(
                github_clients.GetRepositoryPRsRequest(
                    owner=self._config.owner,
                    repo=repo,
                    created_after=last_pr_created,
                )
            )
            if not prs:
                break

            for pr in prs:
                yield task_base.Event(
                    id=f"pr_created__{pr.id}",
                    title=f"🛠New PR in {self._config.owner}/{repo}",
                    body=f"PR created by {pr.author}: {pr.title}",
                    url=pr.url,
                )
                last_pr_created = max(last_pr_created, pr.created_at)
                repository_state.last_pr_created = last_pr_created

    async def _process_all_repository_failed_workflow_run(
        self,
        state: GithubTriggerState,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        async for event in asyncio_utils.GatherIterators(
            self._process_repository_failed_workflow_run(state=state, repo=repo) for repo in self._config.repos
        ):
            yield event

    async def _process_repository_failed_workflow_run(
        self,
        state: GithubTriggerState,
        repo: str,
    ) -> typing.AsyncGenerator[task_base.Event, None]:
        if repo not in state.repository_failed_workflow_run:
            state.repository_failed_workflow_run[repo] = RepositoryFailedWorkflowRunState.default_factory()
        repository_state = state.repository_failed_workflow_run[repo]

        request = github_clients.GetRepositoryWorkflowRunsRequest(
            owner=self._config.owner,
            repo=repo,
            created_after=repository_state.oldest_incomplete_created,
        )

        oldest_incomplete_created = None
        last_created = None

        async for workflow_run in self._rest_github_client.get_repository_workflow_runs(request):
            if (
                workflow_run.status == "completed"
                and workflow_run.conclusion == "failure"
                and workflow_run not in repository_state.already_reported_failed_runs
            ):
                yield task_base.Event(
                    id=f"failed_workflow_run__{self._config.owner}__{repo}__{workflow_run.id}",
                    title=f"🔥Failed workflow run in {self._config.owner}/{repo}",
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


__all__ = [
    "GithubTriggerConfig",
]

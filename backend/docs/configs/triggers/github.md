# Github trigger

Composite trigger for GitHub events, currently supported sub-triggers:

- Created PR
- Created Issue
- Workflow run failed

## Configuration

- `id` - trigger id, used for trigger identification.
- `type` - trigger type, should be `github`.
- `owner` - repository owner.
- `include_repos` - list of repositories to include.
- `exclude_repos` - list of repositories to exclude.
- `default_timedelta_seconds` - default timedelta in seconds for events. Default is `86400` (1 day).
- `sub_triggers` - list of sub-triggers, currently supported.

## Sub-triggers

### Repository Issue created

Triggered when a new Issue is created in repository from trigger.

- `id` - sub-trigger id, used for sub-trigger identification. Optional, `type` is used if not provided.
- `type` - sub-trigger type, should be `repository_issue_created`.
- `include_author` - list of authors to include.
- `exclude_author` - list of authors to exclude.
- `include_title` - list of titles to include.
- `exclude_title` - list of titles to exclude.
- `include_title_regex` - list of title regex checks to include.
- `exclude_title_regex` - list of title regex checks to exclude.

### Repository PR created

Triggered when a new PR is created in repository from trigger.

- `id` - sub-trigger id, used for sub-trigger identification. Optional, `type` is used if not provided.
- `type` - sub-trigger type, should be `repository_pr_created`.
- `include_author` - list of authors to include.
- `exclude_author` - list of authors to exclude.

### Workflow run failed

Triggered when a workflow run failed in repository from trigger.

- `id` - sub-trigger id, used for sub-trigger identification. Optional, `type` is used if not provided.
- `type` - sub-trigger type, should be `repository_failed_workflow_run`.
- `include` - list of workflow names to include.
- `exclude` - list of workflow names to exclude.

## Example

```yaml
id: github_trigger
type: github
owner: ovsds
include_repos:
  - github-watcher
  - github-watcher-actions
default_timedelta_seconds: 3600
sub_triggers:
  - type: repository_pr_created
  - type: repository_issue_created
  - type: repository_failed_workflow_run
    exclude:
      - Check PR
```

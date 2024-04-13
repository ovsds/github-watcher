# Github Watcher Backend

Asynchronous application for checking triggers and performing reactions.

## Usage

### Settings

Can be set by both yaml file and environment variables, [example](example/settings.yaml).
File path can be set by `GITHUB_WATCHER_SETTINGS_YAML` environment variable.
Settings consist of next sections:

- app - general application settings
- logs - logging settings
- tasks - task processing settings

#### App

`app.env` - application environment, used mainly for logging. Default is `production`.

```yaml
app:
  env: development
```

Can be set by `GITHUB_WATCHER_APP__ENV` environment variable.

---

`app.debug` - debug mode, enables more verbose logging. Default is `false`.

```yaml
app:
  debug: true
```

Can be set by `GITHUB_WATCHER_APP__DEBUG` environment variable.

#### Logs

`logs.level` logging level, can be one of `debug`, `info`, `warning`, `error`. Default is `info`.

```yaml
logs:
  level: debug
```

Can be set by `GITHUB_WATCHER_LOGS__LEVEL` environment variable.

---

`logs.format` - logging format string, passed to python logging formatter. Default is `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.

```yaml
logs:
  format: "%(message)s"
```

Can be set by `GITHUB_WATCHER_LOGS__FORMAT` environment variable.

#### Tasks

`tasks.config_backend` - backend configuration, used for setting up triggers and reactions.
Can select among different types. Currently, only `yaml_file` is supported.

```yaml
tasks:
  config_backend:
    type: yaml_file
    path: example/config.yaml
```

Can be set by environment variables:

```shell
GITHUB_WATCHER_TASKS__CONFIG_BACKEND__TYPE=yaml_file
GITHUB_WATCHER_TASKS__CONFIG_BACKEND__PATH=example/config.yaml
```

---

`tasks.queue_backend` - queue configuration, used as a message broker for task processing.
Can select among different types. Currently, only `memory` is supported.

```yaml
tasks:
  queue_backend:
    type: memory
```

Can be set by environment variables:

```shell
GITHUB_WATCHER_TASKS__QUEUE_BACKEND__TYPE=memory
```

---

`tasks.state_backend` - state backend configuration, used for storing task and queue state.
Can select among different types. Currently, only `local_dir` is supported.

```yaml
tasks:
  state_backend:
    type: local_dir
    path: example/state
```

Can be set by environment variables:

```shell
GITHUB_WATCHER_TASKS__STATE_BACKEND__TYPE=local_dir
GITHUB_WATCHER_TASKS__STATE_BACKEND__PATH=example/state
```

---

`tasks.scheduler.limit` - maximum number of parallel jobs. Default is `100`.

```yaml
tasks:
  scheduler:
    limit: 10
```

Can be set by `GITHUB_WATCHER_TASKS__SCHEDULER__LIMIT` environment variable.

---

`tasks.scheduler.pending_limit` - maximum number of pending jobs. `0` means no limit. Default is `0`.

```yaml
tasks:
  scheduler:
    pending_limit: 10
```

Can be set by `GITHUB_WATCHER_TASKS__SCHEDULER__PENDING_LIMIT` environment variable.

---

`tasks.scheduler.timeout` - maximum time for all jobs to finish in seconds. `0` means no timeout.
Default is `600`.

```yaml
tasks:
  scheduler:
    timeout: 10
```

Can be set by `GITHUB_WATCHER_TASKS__SCHEDULER__TIMEOUT` environment variable.

---

`tasks.scheduler.close_timeout` - maximum time for scheduler to wait for all jobs to finish in seconds.

```yaml
tasks:
  scheduler:
    close_timeout: 10
```

Can be set by `GITHUB_WATCHER_TASKS__SCHEDULER__CLOSE_TIMEOUT` environment variable.

### Task Processors

Task (`tasks.task_processor`), trigger(`tasks.trigger_processor`) and
event (`tasks.event_processor`) processors can be set by same block with the same structure.

---

`tasks.[...]_processor.count` - number of job processors. Default is `5`.

```yaml
tasks:
  [...]_processor:
    count: 10
```

Can be set by `GITHUB_WATCHER_TASKS__[...]_PROCESSOR__COUNT` environment variable.

---

`tasks.[...]_processor.max_retries` - maximum number of retries for failed jobs. Default is `3`.

```yaml
tasks:
  [...]_processor:
    max_retries: 5
```

Can be set by `GITHUB_WATCHER_TASKS__[...]_PROCESSOR__MAX_RETRIES` environment variable.

---

`tasks.[...]_processor.queue_state_mode` - queue state mode, sets queue state handling mode.
Can be one of `preserve`, `restart`, `ignore`. Default is `preserve`.

```yaml
tasks:
  [...]_processor:
    queue_state_mode: restart
```

Can be set by `GITHUB_WATCHER_TASKS__[...]_PROCESSOR__QUEUE_STATE_MODE` environment variable.

---

`tasks.[...]_processor.failed_queue_state_mode` - failed queue state mode,
sets queue state handling mode for failed jobs. Can be one of `preserve`, `restart`, `ignore`. Default is `preserve`.

```yaml
tasks:
  [...]_processor:
    failed_queue_state_mode: ignore
```

### Config

Config can be set by yaml file, [example](example/config.yaml) when using `yaml_file` config backend.

```yaml
tasks:
  - id:
    triggers: ...
    actions: ...
```

Task config consists of two main sections:

- id - task id, used for task identification
- triggers - list of triggers.
  Currently, only [github](docs/configs/triggers/github.md) trigger is supported.
- actions - list of actions.
  Currently, only [telegram_webhook](docs/configs/actions/telegram_webhook.md) action is supported.

## Development

### Global dependencies

- poetry

### Taskfile commands

For all commands see [Taskfile](Taskfile.yaml) or `task --list-all`.

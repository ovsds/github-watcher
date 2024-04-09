# "Github Watcher Backend"

"Github Watcher Backend"

## Development

### Global dependencies

- poetry

### Taskfile commands

For all commands see [Taskfile](Taskfile.yaml) or `task --list-all`.

### Environment variables

Application:

- `APP_ENV` - Application environment (`development` or `production`)
- `APP_NAME` - Application name
- `APP_VERSION` - Application version
- `APP_DEBUG` - Application debug mode

Logging:

- `LOGS_MIN_LEVEL` - Minimum log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `LOGS_FORMAT` - Log format

# Github Watcher

[![CI](https://github.com/ovsds/github-watcher/workflows/Check%20PR/badge.svg)](https://github.com/ovsds/github-watcher/actions?query=workflow%3A%22%22Check+PR%22%22)

Github Watcher is an easy-to-use extendable framework for setting up custom reactions on various triggers.

### Supported triggers

- Github: new PR, new Issue, failed workflow run

### Supported reactions

- Telegram message

## Usage

It can be easily setup in CI by [github-watcher-action](https://github.com/ovsds/github-watcher-action), example:

- [workflow](.github/workflows/github-watcher.yaml)
- [config](.github/github-watcher-config.yaml)

For any advanced use cases, it can be used as a standalone service by running the backend service in docker. Example:

```shell
docker run \
  --rm \
  --volume ./backend/example/settings.yaml:/settings.yaml \  # provide settings file
  --volume ./backend/example/config.yaml:/config.yaml \  # provide config file for yaml_file config backend
  --volume ./backend/example/state:/state \  # provide state directory for local_dir state backend
  --env GITHUB_WATCHER_SETTINGS_YAML=/settings.yaml \
  --env GITHUB_TOKEN \
  --env TELEGRAM_CHAT_ID \
  --env TELEGRAM_BOT_TOKEN \
  ghcr.io/ovsds/github-watcher:0.3.0
```

### Backend

The backend service is responsible for handling triggers and reactions.
More information can be found in [backend/README.md](backend/README.md).

## Development

### Global dependencies

- nvm
- node

### Taskfile commands

For all commands see [Taskfile](Taskfile.yaml) or `task --list-all`.

## License

[MIT](LICENSE)

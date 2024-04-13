# Telegram webhook action

Action to send a message to a Telegram chat using a webhook on event.

## Configuration

- `id` - action id, used for action identification.
- `type` - action type, should be `telegram_webhook`.
- `chat_id_secret` - [secret](../secrets/README.md) configuration to provide chat id.
- `token_secret` - [secret](../secrets/README.md) configuration to provide bot token.
- `max_message_title_length` - maximum message title length. Default is `100`.
- `max_message_body_length` - maximum message body length. Default is `500`.

## Example

```yaml
id: telegram_webhook
type: telegram_webhook
chat_id_secret:
  type: env
  key: TELEGRAM_CHAT_ID
token_secret:
  type: env
  key: TELEGRAM_BOT_TOKEN
max_message_title_length: 50
max_message_body_length: 200
```

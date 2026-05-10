# computer_use_remote tool

Controls the subscribed A0 CLI host machine as a local desktop target.
Load `computer-use-remote` before using this tool.

## Requirements
- A CLI client is subscribed to this chat and advertises enabled local computer use.
- Backend: `{{backend}}`
- Trust mode: `{{trust_mode}}`
- Features: `{{features}}`

## Arguments
- `action`: one of `start_session`, `status`, `capture`, `move`, `click`, `scroll`, `key`, `type`, `stop_session`
- `session_id`: optional for actions after `start_session`

Action-specific fields:
- `move`: `x`, `y` normalized to `[0,1]`
- `click`: optional `x`, `y`, plus optional `button` (`left`, `right`, `middle`) and `count`
- `scroll`: `dx`, `dy`
- `key`: `key` or `keys`
- `type`: `text`, optional `submit` boolean

## Runtime Notes
- Use `start_session` before interactive actions. `status` only inspects state.
- Successful interactive actions attach a fresh screenshot; base decisions on the latest capture.
- Prefer keyboard/accessibility routes before pointer actions.
- Coordinates are normalized global screen coordinates.

# code_execution_remote tool

Runs shell-backed execution on the machine where the subscribed A0 CLI is running.
Load `a0-cli-remote-workflows` before using this tool for nontrivial local project work.

Current local access mode: `{{access_mode}}`

## Requirements
- A CLI client is subscribed to this chat and advertises remote execution.
- Paths and shell syntax are evaluated on the CLI host, not inside Agent Zero.
- {{write_runtime_note}}

## Arguments
- `runtime`: one of `terminal`, `python`, `nodejs`, `output`, `reset`
- `runtime=input` is a temporary deprecated compatibility alias for sending one line of
  keyboard input into a running shell session
- `session`: integer session id (default `0`)

Runtime-specific fields:
- `terminal`, `python`, `nodejs`: require `code`
- `input`: requires `keyboard` (or `code` as fallback)
- `reset`: optional `reason`

## Notes
- Reuse `session` when continuing a workflow.
- Use `output` to poll a running session and `reset` for a stuck session.
- If the CLI returns a disabled/no-client error, ask the user to enable or reconnect the CLI instead of falling back to server-side execution.

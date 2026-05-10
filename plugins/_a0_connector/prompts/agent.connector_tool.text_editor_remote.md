# text_editor_remote tool

Reads, writes, and patches files on the machine where the subscribed A0 CLI is running.
This is different from server-side file tools. Load `a0-cli-remote-workflows` before using it for edits.

Current access mode: `{{access_mode}}`

## Requirements
- A CLI client is subscribed to this chat and advertises remote file access.
- Paths are evaluated on the CLI host filesystem, not the Agent Zero server.
- {{write_guidance}}

## Operations
- `read`: optional `line_from`, `line_to`
- `write`: requires `content`
- `patch`: requires either `patch_text` or `edits`

## Notes
- Prefer `read` before line-number edits.
- Prefer `patch_text` for context-anchored changes and `edits` only for fresh, surgical line ranges.
- If freshness checks reject a line patch, reread the file and retry with updated ranges.

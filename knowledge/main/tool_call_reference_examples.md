# Tool Call Reference Examples

These examples are intentionally short and high signal so tool-call shape guidance
can live in knowledge without bloating the default prompt stack.

## 1) Namespaced tool (`text_editor`) vs non-namespaced tool (`code_execution_tool`)

- `text_editor` requires method in `tool_name`:
  - `text_editor:read`
  - `text_editor:write`
  - `text_editor:patch`
- `code_execution_tool` uses a plain tool name plus behavior in `tool_args.runtime`.

### Example A: read file lines with namespaced tool

```json
{
  "tool_name": "text_editor:read",
  "tool_args": {
    "path": "/workspace/agent-zero/README.md",
    "line_from": 1,
    "line_to": 60
  }
}
```

### Example B: run shell command with `code_execution_tool`

```json
{
  "tool_name": "code_execution_tool",
  "tool_args": {
    "runtime": "terminal",
    "session": 0,
    "reset": false,
    "code": "pwd"
  }
}
```

### Example C: poll ongoing terminal output

```json
{
  "tool_name": "code_execution_tool",
  "tool_args": {
    "runtime": "output",
    "session": 0
  }
}
```

## 2) Memory tools use plain names and structured args

```json
{
  "tool_name": "memory_load",
  "tool_args": {
    "query": "tool argument format",
    "limit": 3,
    "threshold": 0.7
  }
}
```

## 3) Subordinate tool booleans are JSON booleans

```json
{
  "tool_name": "call_subordinate",
  "tool_args": {
    "profile": "",
    "message": "Review this patch for edge cases.",
    "reset": true
  }
}
```

Use these examples as structure references only. Adapt arguments to the current task.

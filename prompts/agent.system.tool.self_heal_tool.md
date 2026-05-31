### self_heal_tool
self-healing and system repair
args:
- `action` (one of: diagnose, fix, update, restart, logs)
- `fix_action` (optional: specific fix to apply)
- `service` (optional: service to restart)
returns diagnosis results, fix status, system logs
example:
~~~json
{
  "thoughts": ["Something is broken, I need to diagnose and fix it."],
  "headline": "Running system diagnosis",
  "tool_name": "self_heal_tool",
  "tool_args": {
    "action": "diagnose"
  }
}
~~~

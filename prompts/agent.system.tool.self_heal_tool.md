### self_heal_tool
self-healing and system repair
args: `action` (diagnose, fix, update, restart, logs)
optional: `fix_action`, `service`
example:
~~~json
{
  "thoughts": ["Something is broken, I need to fix it."],
  "headline": "Running diagnosis",
  "tool_name": "self_heal_tool",
  "tool_args": {
    "action": "diagnose"
  }
}
~~~

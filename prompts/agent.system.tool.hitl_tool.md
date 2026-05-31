### hitl_tool
human-in-the-loop intervention modes
args: `action` (mode, checkpoint, approve, reject)
optional: `mode` (full_auto, gate_only, checkpoint, copilot, step_by_step, express, regulatory, custom)
example:
~~~json
{
  "thoughts": ["I need to set the HITL mode."],
  "headline": "Setting HITL mode",
  "tool_name": "hitl_tool",
  "tool_args": {
    "action": "mode",
    "mode": "checkpoint"
  }
}
~~~

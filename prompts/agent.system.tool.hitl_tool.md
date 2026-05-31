### hitl_tool
human-in-the-loop intervention modes
args:
- `action` (one of: mode, checkpoint, approve, reject)
- `mode` (optional: full_auto, gate_only, checkpoint, copilot, step_by_step, express, regulatory, custom)
returns current mode, pending approvals, checkpoint status
example:
~~~json
{
  "thoughts": ["I need to set the human-in-the-loop mode."],
  "headline": "Setting HITL mode",
  "tool_name": "hitl_tool",
  "tool_args": {
    "action": "mode",
    "mode": "checkpoint"
  }
}
~~~

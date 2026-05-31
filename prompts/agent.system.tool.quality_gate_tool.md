### quality_gate_tool
quality gates for research pipeline
args: `action` (check, pass, fail), `gate` (1-5)
optional: `data`
example:
~~~json
{
  "thoughts": ["I need to check the quality gate."],
  "headline": "Checking quality gate",
  "tool_name": "quality_gate_tool",
  "tool_args": {
    "action": "check",
    "gate": 1
  }
}
~~~

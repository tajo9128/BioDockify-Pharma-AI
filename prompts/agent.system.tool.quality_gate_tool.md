### quality_gate_tool
quality gates for research pipeline
args:
- `action` (one of: check, pass, fail)
- `gate` (gate number: 1-5)
- `data` (optional: data to check)
returns gate status, requirements, pass/fail details
example:
~~~json
{
  "thoughts": ["I need to check if this stage passes the quality gate."],
  "headline": "Checking quality gate",
  "tool_name": "quality_gate_tool",
  "tool_args": {
    "action": "check",
    "gate": 1
  }
}
~~~

### debate_tool
multi-agent debate for hypothesis validation
args:
- `action` (one of: hypothesis, method, results)
- `topic` (debate topic)
- `context` (optional: additional context)
returns debate arguments from Pharmacologist, Biostatistician, Chemist perspectives
example:
~~~json
{
  "thoughts": ["I need to validate this hypothesis through debate."],
  "headline": "Running multi-agent debate",
  "tool_name": "debate_tool",
  "tool_args": {
    "action": "hypothesis",
    "topic": "Compound X shows promising anti-cancer activity"
  }
}
~~~

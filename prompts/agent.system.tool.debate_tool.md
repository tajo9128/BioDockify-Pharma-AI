### debate_tool
multi-agent debate for hypothesis validation
args: `action` (hypothesis, method, results), `topic`
optional: `context`
example:
~~~json
{
  "thoughts": ["I need to validate this hypothesis."],
  "headline": "Running debate",
  "tool_name": "debate_tool",
  "tool_args": {
    "action": "hypothesis",
    "topic": "Compound X shows anti-cancer activity"
  }
}
~~~

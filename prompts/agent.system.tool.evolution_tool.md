### evolution_tool
cross-run knowledge evolution
args: `action` (store, recall, evolve, history)
optional: `key`, `value`, `domain`
example:
~~~json
{
  "thoughts": ["I need to store this finding."],
  "headline": "Storing knowledge",
  "tool_name": "evolution_tool",
  "tool_args": {
    "action": "store",
    "key": "compound_x_ic50",
    "value": "IC50 = 1.2 nM"
  }
}
~~~

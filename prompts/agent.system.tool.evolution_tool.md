### evolution_tool
cross-run knowledge evolution with Ebbinghaus time-decay
args:
- `action` (one of: store, recall, evolve, history)
- `key` (knowledge key)
- `value` (optional: knowledge value)
- `domain` (optional: knowledge domain)
returns stored knowledge, evolution history, decay metrics
example:
~~~json
{
  "thoughts": ["I need to store this finding for future reference."],
  "headline": "Storing knowledge",
  "tool_name": "evolution_tool",
  "tool_args": {
    "action": "store",
    "key": "compound_x_ic50",
    "value": "IC50 = 1.2 nM against target Y",
    "domain": "drug_discovery"
  }
}
~~~

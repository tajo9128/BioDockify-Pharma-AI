## memory tools
use when durable recall or storage is useful
- `memory_load`: args `query`, optional `threshold`, `limit`, `filter`
- `memory_save`: args `text`, optional `area` and metadata kwargs
- `memory_delete`: arg `ids` comma-separated ids
- `memory_forget`: args `query`, optional `threshold`, `filter`

notes:
- `threshold` is similarity from `0` to `1`
- `filter` is a metadata expression (e.g. `area=='main'`)
- confirm destructive changes when accuracy matters

example:
~~~json
{
  "thoughts": ["I should search memory for relevant prior guidance."],
  "headline": "Loading related memories",
  "tool_name": "memory_load",
  "tool_args": {
    "query": "tool argument format",
    "threshold": 0.7,
    "limit": 3
  }
}
~~~

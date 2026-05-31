### benchmark
run system benchmarks and diagnostics
args:
- `action` (one of: run, api_health, storage, memory, dependencies)
returns system health metrics, dependency status, performance benchmarks
example:
~~~json
{
  "thoughts": ["I need to check the system health."],
  "headline": "Running system benchmark",
  "tool_name": "benchmark",
  "tool_args": {
    "action": "run"
  }
}
~~~

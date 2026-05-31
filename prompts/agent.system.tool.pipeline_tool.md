### pipeline_tool
run autonomous research pipeline (25 stages, 9 phases)
args: `action` (start, status, resume, cancel), `topic`
optional: `mode` (full, quick, literature_only)
example:
~~~json
{
  "thoughts": ["I need to run a full research pipeline."],
  "headline": "Starting research pipeline",
  "tool_name": "pipeline_tool",
  "tool_args": {
    "action": "start",
    "topic": "novel drug targets for Alzheimer's disease"
  }
}
~~~

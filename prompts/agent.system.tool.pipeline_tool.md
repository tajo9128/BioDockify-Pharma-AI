### pipeline_tool
run the autonomous research pipeline (25 stages, 9 phases)
args:
- `action` (one of: start, status, resume, cancel)
- `topic` (research topic)
- `mode` (optional: full, quick, literature_only)
returns pipeline status, stage progress, results
example:
~~~json
{
  "thoughts": ["I need to run a full research pipeline on this topic."],
  "headline": "Starting research pipeline",
  "tool_name": "pipeline_tool",
  "tool_args": {
    "action": "start",
    "topic": "novel drug targets for Alzheimer's disease"
  }
}
~~~

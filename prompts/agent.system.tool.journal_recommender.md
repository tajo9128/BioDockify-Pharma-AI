### journal_recommender
find and verify academic journals
args: `action` (search, verify, profile, recommend, history, stats)
optional: `query`, `issn`, `topic`
example:
~~~json
{
  "thoughts": ["I need to find a journal for this paper."],
  "headline": "Searching journals",
  "tool_name": "journal_recommender",
  "tool_args": {
    "action": "search",
    "query": "drug discovery"
  }
}
~~~

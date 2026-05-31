### journal_recommender
find and verify academic journals for manuscript submission
args:
- `action` (one of: search, verify, profile, recommend, history, stats)
- `query` (search query or journal name)
- `issn` (ISSN number for verification)
- `topic` (research topic for recommendation)
returns journal details, Scopus/WoS indexing, hijacked journal alerts, APC, impact metrics
example:
~~~json
{
  "thoughts": ["I need to find a suitable journal for this paper."],
  "headline": "Searching for journals",
  "tool_name": "journal_recommender",
  "tool_args": {
    "action": "search",
    "query": "drug discovery pharmaceutical"
  }
}
~~~

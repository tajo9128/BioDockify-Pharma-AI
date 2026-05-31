### verify_tool
5-layer verification of research claims
args:
- `action` (one of: verify, check_citation, check_claim)
- `claim` (claim to verify)
- `citation` (optional: citation to check)
returns verification status, sources, confidence score
example:
~~~json
{
  "thoughts": ["I need to verify this research claim."],
  "headline": "Verifying research claim",
  "tool_name": "verify_tool",
  "tool_args": {
    "action": "verify",
    "claim": "Aspirin reduces risk of heart attack by 30%"
  }
}
~~~

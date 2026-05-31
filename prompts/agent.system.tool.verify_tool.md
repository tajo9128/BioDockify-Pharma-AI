### verify_tool
5-layer verification of research claims
args: `action` (verify, check_citation, check_claim)
optional: `claim`, `citation`
example:
~~~json
{
  "thoughts": ["I need to verify this claim."],
  "headline": "Verifying claim",
  "tool_name": "verify_tool",
  "tool_args": {
    "action": "verify",
    "claim": "Aspirin reduces heart attack risk by 30%"
  }
}
~~~

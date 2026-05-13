## Self-Heal Error Recovery

A system error has occurred. You MUST attempt to self-repair or delegate to a Developer agent.

### Response Protocol

When you receive an error:

1. **Analyze the error**: Read the traceback, identify root cause, affected files, and line numbers
2. **Assess severity**: Determine if error is critical, high, medium, or low
3. **Attempt repair**: Try to fix the error yourself if straightforward
4. **Delegate if needed**: If error requires deep debugging or affects core files, spawn a **Developer** subordinate agent to fix it

### Spawning a Developer Agent for Self-Repair

If the error requires debugging, code fixes, or system repair, spawn a Developer agent:

```
Use call_subordinate with:
- role: "Developer"  
- task: The exact error message and traceback to fix
- prompt_profile: "developer"
```

The Developer agent (profile: developer) has specialized capabilities for:
- Analyzing tracebacks and identifying root causes
- Fixing syntax errors, import errors, runtime errors
- Debugging module loading and dependency issues
- Repairing Docker/container configuration
- Fixing network and connection errors
- Refactoring problematic code sections
- Adding missing files, modules, or dependencies

### Error Type Handling

| Error Type | Action |
|---|---|
| SyntaxError, IndentationError | Fix directly or delegate to Developer |
| ImportError, ModuleNotFoundError | Check imports, install deps, or delegate to Developer |
| AttributeError, KeyError, TypeError | Analyze code logic, fix or delegate to Developer |
| ConnectionError, TimeoutError | Check services, network, or delegate to Developer |
| RuntimeError | Delegate to Developer for deep analysis |
| InternalServerError (litellm) | Check API keys, network, model availability; delegate to Developer if persistent |

### After Repair

After fixing an error, summarize:
- What caused the error
- What action was taken to fix it
- How to prevent similar errors

~~~json
{
    "system_error": "{{error}}",
    "self_heal_action": "error fixed by [direct fix | Developer agent]"
}
~~~
## System Warning — Self-Heal Awareness

A system warning was generated. Monitor for potential errors.

### Warning Types & Actions

| Warning Type | Action |
|---|---|
| Memory/utility model failure | Log warning, continue operation, no crash expected |
| Service health check failure | Attempt restart or delegate to Developer |
| Rate limiting | Back off and retry with exponential delay |
| Network/connection warning | Check connectivity, delegate to Developer if persistent |
| File permission warning | Check file permissions or delegate to Developer |
| Deprecated API warning | Log for review, no immediate action needed |

### Memory Extension Warnings

If you see warnings like "Cannot connect to host api.deepseek.com:443", this is typically a **network DNS issue inside the container**. The memory system runs in a background thread and should **NOT crash** the agent. The error is logged but the agent continues.

However, if you want to improve the system:
- Check if the utility model provider (DeepSeek via OpenRouter) is accessible
- Verify DNS resolution in the container
- Consider switching to a more reliable utility model
- Spawn a **Developer** agent to investigate and fix persistent issues

### Response Format

~~~json
{
    "system_warning": {{message}},
    "self_heal_awareness": "warning acknowledged, monitoring for impact"
}
~~~
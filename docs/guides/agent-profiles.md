# Agent Profiles

Agent profiles let you give Agent Zero different identities, prompt overrides, tools, extensions, and optionally model settings. Use them when you want a specialized agent such as a researcher, developer, security auditor, copywriter, or domain-specific assistant.

Use **Settings > Agent Config** to choose the default profile for new chats. The chat composer profile selector shows and changes the profile for the currently selected chat only, so different chats can keep different active profiles.

## Where Profiles Live

| Location | Purpose |
|---|---|
| `/a0/agents/<profile>/` | Built-in framework profiles. Do not edit these for custom work. |
| `/a0/usr/agents/<profile>/` | User-created profiles. This is the normal place for custom profiles and survives updates. |
| `/a0/usr/plugins/<plugin>/agents/<profile>/` | Plugin-distributed profiles tied to plugin functionality. |
| `/a0/usr/projects/<project>/.a0proj/agents/<profile>/` | Project-scoped profiles available only inside one project. |

## Required Profile Definition

Every profile needs an `agent.yaml` file:

```yaml
title: Data Analyst
description: Agent specialized in data analysis, visualization, and statistical modeling.
context: Use this agent for data analysis tasks, creating visualizations, statistical
  analysis, and working with datasets in Python.
```

`agent.yaml` intentionally has only these fields:

| Field | Purpose |
|---|---|
| `title` | Display name shown in the UI |
| `description` | One-line summary of the specialization |
| `context` | Instructions telling a superior agent when to delegate to this profile |

Do not put model settings, temperature, or tool allow-lists in `agent.yaml`.

## Prompt Overrides

Profiles inherit the root prompt files from `/a0/prompts`. To customize a profile, copy only the prompt files you need into:

```text
/a0/usr/agents/<profile>/prompts/
```

The most common override is:

```text
prompts/agent.system.main.specifics.md
```

This file is intentionally empty by default and is the safest place to add role, expertise, workflow, and style instructions.

Useful root prompt levers:

| File | Use it for |
|---|---|
| `agent.system.main.specifics.md` | Role, expertise, persona, workflow, and behavioral specialization. |
| `agent.system.main.communication.md` | Changing the response contract, such as replacing the default `thoughts`, `headline`, `tool_name`, `tool_args` JSON shape. |
| `agent.system.main.solving.md` | Changing the problem-solving loop, autonomy level, delegation policy, or verification standard. |
| `agent.system.main.environment.md` | Describing a different runtime or domain environment. |
| `agent.system.main.role.md` | Replacing the base Agent Zero role. Use rarely; prefer `specifics.md` when possible. |
| `agent.system.tool.<name>.md` | Documenting a profile-specific tool or overriding a tool prompt. |

Only override what you actually want to change. Copying unchanged prompt files makes profiles harder to maintain when the framework updates.

## Profile-Specific Models

Main and Utility model settings are not part of `agent.yaml`. They are handled by the always-enabled `_model_config` plugin.

To give one profile its own Main or Utility model, create a companion config file:

| Profile scope | Model config path |
|---|---|
| User profile | `/a0/usr/agents/<profile>/plugins/_model_config/config.json` |
| Plugin-distributed profile | `/a0/usr/plugins/<plugin>/agents/<profile>/plugins/_model_config/config.json` |
| Project-scoped profile | `/a0/usr/projects/<project>/.a0proj/agents/<profile>/plugins/_model_config/config.json` |

Example complete config:

```json
{
  "allow_chat_override": true,
  "chat_model": {
    "provider": "openrouter",
    "name": "anthropic/claude-sonnet-4.6",
    "api_base": "",
    "ctx_length": 200000,
    "ctx_history": 0.7,
    "vision": true,
    "rl_requests": 0,
    "rl_input": 0,
    "rl_output": 0,
    "kwargs": {}
  },
  "utility_model": {
    "provider": "openrouter",
    "name": "openai/gpt-5.4-mini",
    "api_base": "",
    "ctx_length": 128000,
    "ctx_input": 0.7,
    "rl_requests": 0,
    "rl_input": 0,
    "rl_output": 0,
    "kwargs": {}
  },
  "embedding_model": {
    "provider": "huggingface",
    "name": "sentence-transformers/all-MiniLM-L6-v2",
    "api_base": "",
    "rl_requests": 0,
    "rl_input": 0,
    "kwargs": {}
  }
}
```

Important: scoped `_model_config/config.json` files are selected as a whole. They are not deep-merged with broader global or project config. If you create this file, include a complete effective config with `chat_model`, `utility_model`, and `embedding_model`. If you only want to customize Main or Utility, copy the other model sections from the current effective config.

Do not store API keys in this file. API keys are managed globally through Settings and secrets.

## Tools and Extensions

Profiles can also add or override tools and extensions:

```text
/a0/usr/agents/<profile>/tools/<tool_name>.py
/a0/usr/agents/<profile>/extensions/<hook_point>/_NN_name.py
```

If you add a tool, also add a matching prompt file:

```text
/a0/usr/agents/<profile>/prompts/agent.system.tool.<tool_name>.md
```

## Quick Example

```text
/a0/usr/agents/data-analyst/
+-- agent.yaml
+-- prompts/
|   +-- agent.system.main.specifics.md
+-- plugins/
    +-- _model_config/
        +-- config.json
```

The `plugins/_model_config/config.json` file is optional. Use it only when this profile needs different models from the global or project settings.

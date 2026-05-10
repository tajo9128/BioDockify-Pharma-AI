# A0 CLI Connector

Agent Zero lives in Docker for a reason. That keeps it safer. The problem is that people see Docker and assume the agent can never really touch the code on their computer.

A0 CLI is the answer to that.

Agent Zero stays in Docker. A0 CLI installs on the host machine. That is what lets Agent Zero finally work on the real files on your real computer.

For now, use the install commands below.

## Quick Install

**macOS / Linux:**
```bash
curl -LsSf https://cli.agent-zero.ai/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm https://cli.agent-zero.ai/install.ps1 | iex
```

Run these on the host machine, not inside the Agent Zero container.

The installer uses `uv`, and `uv` will select or download a compatible Python if needed.

## Open it and start working

1. Make sure Agent Zero is already running.
2. Launch A0 CLI on the host machine:

```bash
a0
```

3. If Agent Zero is running on the same machine, A0 CLI will usually find it for you.
4. If Agent Zero is somewhere else, enter the exact web address or set `AGENT_ZERO_HOST` as env variable before launching `a0`.
5. Open or create a chat and confirm you can talk to Agent Zero from the host machine.

> [!NOTE]
> Current Agent Zero builds starting from v1.9 include the builtin connector support that A0 CLI expects. If you see a connector-specific `404`, update Agent Zero first.

## Give this to another agent

If another agent is helping with setup, do not paste a whole checklist. Paste one line:

```text
Set up the A0 CLI connector for Agent Zero on this machine using the a0-setup-cli Skill.
```

## Troubleshooting

- **Nothing appears locally:** Enter the Agent Zero web address manually or export `AGENT_ZERO_HOST`.
- **You tried to install from inside Docker:** A0 CLI belongs on the host machine. Agent Zero stays in Docker.
- **Function keys do nothing:** Some terminals and IDEs capture function keys. Use `Ctrl+P`.
- **Connector route returns `404`:** Update Agent Zero to a build with builtin connector support.

## Related links

- [Quick Start](../quickstart.md)
- [Installation Guide](../setup/installation.md)

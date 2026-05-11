# BioDockify AI

**BioDockify AI** is a modified pharmaceutical research distribution built on top of [Agent Zero](https://github.com/agent0ai/agent-zero) — an open-source agentic framework created and maintained by [Jan Tomasek](https://github.com/Xrenel) and the Agent Zero team.

> **This is a fork/modification of Agent Zero.** BioDockify AI is not a standalone product. It is a customized rebranding and domain-specific tuning of the Agent Zero framework, adapted for pharmaceutical research and drug discovery use cases. All core framework functionality belongs to the Agent Zero project.

## Acknowledgments

We gratefully thank the **Agent Zero team** and the open-source community for making Agent Zero freely available under an open-source license. Their commitment to open, transparent, and modifiable AI software makes projects like BioDockify AI possible.

- **Original Project**: [github.com/agent0ai/agent-zero](https://github.com/agent0ai/agent-zero)
- **Original Author**: Jan Tomasek
- **License**: Open source — see the original Agent Zero repository for license details

## What BioDockify AI Adds

BioDockify AI layers the following modifications on top of the unmodified Agent Zero framework:

- **Pharma Research Assistant Role** — Identity and system prompts tuned for pharmaceutical research, drug discovery, and biotech workflows
- **Domain Knowledge Base** — Identity and capabilities documentation focused on pharma/biotech research tasks
- **Rebranded UI** — Custom BioDockify AI branding, DNA double-helix favicon, and pharmaceutical-themed visual identity
- **Docker Hub Image** — Pre-built Docker image with all modifications applied: `tajo9128/biodockify-pharma-ai`

No core Agent Zero framework code has been modified. All changes are limited to:

- UI branding files (`webui/`, `public/`, `plugins/`)
- Agent identity knowledge (`knowledge/main/about/identity.md`)
- Initial message prompt (`prompts/fw.initial_message.md`)

## Quick Start

```bash
docker run -d -p 80:80 --name biodockify \
  -v biodockify_usr:/usr \
  tajo9128/biodockify-pharma-ai:latest
```

Or run with a specific version:

```bash
docker run -d -p 80:80 --name biodockify \
  -v biodockify_usr:/usr \
  tajo9128/biodockify-pharma-ai:v1.0.5
```

Then open [http://localhost](http://localhost) in your browser.

## Features (Inherited from Agent Zero)

- Multi-agent cooperation with subordinate delegation
- Browser automation and web research
- Code execution in Python, Node.js, and Bash
- Persistent memory and knowledge management
- File management and document querying
- Scheduled tasks and automation
- MCP (Model Context Protocol) client and server
- External REST API for programmatic access
- Plugin system with extensible architecture
- Project-based workspace isolation

## Disclaimer

BioDockify AI is an independent community modification. It is not affiliated with, endorsed by, or officially connected to the Agent Zero project or its maintainers. All Agent Zero framework code remains the property of its original authors under their chosen license.

## Version

v1.0.5
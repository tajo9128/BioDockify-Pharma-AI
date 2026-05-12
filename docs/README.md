![BioDockify AI Logo](res/header.png)
# BioDockify AI Documentation

Welcome to the BioDockify AI documentation hub. Whether you're getting started or diving deep into the framework, you'll find comprehensive guides below.

## Quick Start

- **[Quickstart Guide](quickstart.md):** Get up and running in 5 minutes with BioDockify AI.
- **[Installation Guide](setup/installation.md):** Install scripts, updates, and advanced Docker setup (includes [How to Update](setup/installation.md#how-to-update-BioDockify-AI)).
- **[A0 CLI Connector](guides/a0-cli-connector.md):** Install the terminal-native connector, connect it to BioDockify AI, and copy a setup brief for another agent.
- **[Self Update](guides/self-update.md):** How the in-app updater works (technical reference).
- **[VPS Deployment](setup/vps-deployment.md):** Deploy BioDockify AI on a remote server.
- **[Development Setup](setup/dev-setup.md):** Set up a local development environment.

## User Guides

- **[Usage Guide](guides/usage.md):** Comprehensive guide to BioDockify AI's features and capabilities.
- **[A0 CLI Connector](guides/a0-cli-connector.md):** Terminal-first companion workflow for BioDockify AI.
- **[Agent Profiles](guides/agent-profiles.md):** Create and select specialized profiles, prompt overrides, and profile-specific model config.
- **[Projects Tutorial](guides/projects.md):** Learn to create isolated workspaces with dedicated context and memory.
- **[API Integration](guides/api-integration.md):** Add external APIs without writing code.
- **[MCP Setup](guides/mcp-setup.md):** Configure Model Context Protocol servers.
- **[A2A Setup](guides/a2a-setup.md):** Enable agent-to-agent communication.
- **[Troubleshooting](guides/troubleshooting.md):** Solutions to common issues and FAQs.

## Developer Documentation

- **[Architecture Overview](developer/architecture.md):** Understand BioDockify AI's internal structure and components.
- **[Plugins](developer/plugins.md):** Build plugins with `plugin.yaml`, scoped settings, and activation toggles.
- **[Extensions](developer/extensions.md):** Create custom extensions to extend functionality.
- **[Connectivity](developer/connectivity.md):** Connect to BioDockify AI from external applications.
- **[WebSockets](developer/websockets.md):** Real-time communication infrastructure.
- **[MCP Configuration](developer/mcp-configuration.md):** Advanced MCP server configuration.
- **[Notifications](developer/notifications.md):** Notification system architecture and setup.
- **[Contributing Skills](developer/contributing-skills.md):** Create and share agent skills.
- **[Contributing Guide](guides/contribution.md):** Contribute to the BioDockify AI project.

## Community & Support

- **Join the Community:** Connect with other users on [Discord](https://discord.gg/B8KZKNsPpj) to discuss ideas, ask questions, and collaborate.
- **Share Your Work:** Show off your BioDockify AI creations and workflows in the [Show and Tell](https://github.com/agent0ai/BioDockify-AI/discussions/categories/show-and-tell) area.
- **Report Issues:** Use the [GitHub issue tracker](https://github.com/agent0ai/BioDockify-AI/issues) to report bugs or suggest features.
- **Follow Updates:** Subscribe to the [YouTube channel](https://www.youtube.com/@BioDockifyAIFW) for tutorials and release videos.

---

## Table of Contents

- [Quick Start](#quick-start)
  - [Quickstart Guide](quickstart.md)
  - [Installation Guide](setup/installation.md)
    - [How to Update BioDockify AI](setup/installation.md#how-to-update-BioDockify-AI)
    - [Manual Installation (Advanced)](setup/installation.md#manual-installation-advanced)
    - [Step 1: Install Docker Desktop](setup/installation.md#step-1-install-docker-desktop)
      - [Windows Installation](setup/installation.md#-windows-installation)
      - [macOS Installation](setup/installation.md#-macos-installation)
      - [Linux Installation](setup/installation.md#-linux-installation)
    - [Step 2: Run BioDockify AI](setup/installation.md#step-2-run-BioDockify-AI)
      - [Pull Docker Image](setup/installation.md#21-pull-the-BioDockify-AI-docker-image)
      - [Map Folders for Persistence](setup/installation.md#22-optional-map-folders-for-persistence)
      - [Run the Container](setup/installation.md#23-run-the-container)
      - [Access the Web UI](setup/installation.md#24-access-the-web-ui)
    - [Step 3: Configure BioDockify AI](setup/installation.md#step-3-configure-BioDockify-AI)
      - [Settings Configuration](setup/installation.md#settings-configuration)
      - [Agent Configuration](setup/installation.md#agent-configuration)
      - [Chat Model Settings](setup/installation.md#chat-model-settings)
      - [API Keys](setup/installation.md#api-keys)
      - [Authentication](setup/installation.md#authentication)
    - [Choosing Your LLMs](setup/installation.md#choosing-your-llms)
    - [Installing Ollama (Local Models)](setup/installation.md#installing-and-using-ollama-local-models)
    - [Using on Mobile Devices](setup/installation.md#using-BioDockify-AI-on-your-mobile-device)
  - [Self Update (technical)](guides/self-update.md)
  - [VPS Deployment](setup/vps-deployment.md)
  - [Development Setup](setup/dev-setup.md)
  - [A0 CLI Connector](guides/a0-cli-connector.md)

- [User Guides](#user-guides)
  - [Usage Guide](guides/usage.md)
    - [Basic Operations](guides/usage.md#basic-operations)
    - [Plugins and Plugin Hub](guides/usage.md#plugins-and-plugin-hub)
    - [Tool Usage](guides/usage.md#tool-usage)
    - [Projects](guides/usage.md#projects)
      - [What Projects Provide](guides/usage.md#what-projects-provide)
      - [Creating Projects](guides/usage.md#creating-projects)
      - [Project Configuration](guides/usage.md#project-configuration)
      - [Activating Projects](guides/usage.md#activating-projects)
      - [Common Use Cases](guides/usage.md#common-use-cases)
    - [Tasks & Scheduling](guides/usage.md#tasks--scheduling)
      - [Task Types](guides/usage.md#task-types)
      - [Creating Tasks](guides/usage.md#creating-tasks)
      - [Task Configuration](guides/usage.md#task-configuration)
      - [Integration with Projects](guides/usage.md#integration-with-projects)
    - [Secrets & Variables](guides/usage.md#secrets--variables)
    - [Remote Access via Tunneling](guides/usage.md#remote-access-via-tunneling)
    - [Voice Interface](guides/usage.md#voice-interface)
    - [Memory Management](guides/usage.md#memory-management)
    - [Backup & Restore](guides/usage.md#backup--restore)
  - [A0 CLI Connector](guides/a0-cli-connector.md)
  - [Agent Profiles](guides/agent-profiles.md)
  - [Projects Tutorial](guides/projects.md)
  - [API Integration](guides/api-integration.md)
  - [MCP Setup](guides/mcp-setup.md)
  - [A2A Setup](guides/a2a-setup.md)
  - [Troubleshooting](guides/troubleshooting.md)

- [Developer Documentation](#developer-documentation)
  - [Architecture Overview](developer/architecture.md)
    - [System Architecture](developer/architecture.md#system-architecture)
    - [Runtime Architecture](developer/architecture.md#runtime-architecture)
    - [Implementation Details](developer/architecture.md#implementation-details)
    - [Core Components](developer/architecture.md#core-components)
      - [Agents](developer/architecture.md#1-agents)
      - [Tools](developer/architecture.md#2-tools)
      - [Memory System](developer/architecture.md#3-memory-system)
      - [Prompts](developer/architecture.md#4-prompts)
      - [Knowledge](developer/architecture.md#5-knowledge)
      - [Skills](developer/architecture.md#6-skills)
      - [Extensions](developer/architecture.md#7-extensions)
  - [Plugins](developer/plugins.md)
  - [Extensions](developer/extensions.md)
  - [Connectivity](developer/connectivity.md)
  - [WebSockets](developer/websockets.md)
  - [MCP Configuration](developer/mcp-configuration.md)
  - [Notifications](developer/notifications.md)
  - [Contributing Skills](developer/contributing-skills.md)
  - [Contributing Guide](guides/contribution.md)

---

### Your journey with BioDockify AI starts now!

Ready to dive in? Start with the [Quickstart Guide](quickstart.md) for the fastest path to your first chat, or follow the [Installation Guide](setup/installation.md) for a detailed setup walkthrough.


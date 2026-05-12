<<<<<<< HEAD
# Contributing to BioDockify AI

This file is the GitHub-visible entry point for contributors.

For the full contribution workflow, start with:

- [`docs/guides/contribution.md`](docs/guides/contribution.md) — fork, sync, branch, validation, and pull-request flow
- [`docs/developer/sharing-and-safety.md`](docs/developer/sharing-and-safety.md) — how to decide whether a change should go upstream, into a plugin repository, into a skills repository, or remain private
- [`docs/developer/plugins.md`](docs/developer/plugins.md) — plugin structure and Plugin Index submission
- [`docs/developer/contributing-skills.md`](docs/developer/contributing-skills.md) — skill authoring and publication

## Quick rules

- Search open and recently closed upstream PRs before opening a new one.
- Use the branch currently adopted by comparable active upstream PRs or explicit maintainer guidance.
- Keep one focused change per PR whenever practical.
- Keep the source branch available on your fork until the PR is merged or intentionally closed.
- Include exact tests run, or clearly explain why validation was blocked.
- Do not include secrets, `.env` files, local virtual environments, or machine-specific artifacts in a PR.

## Choosing the right place to share work

- **Core bugfix or docs for BioDockify AI itself:** contribute back to `agent0ai/BioDockify-AI` from a public fork.
- **Community plugin:** publish the plugin in its own public repository, then submit it to `agent0ai/a0-plugins`.
- **Reusable skill:** contribute it to BioDockify AI's `skills/` tree or publish it in a dedicated public repository/collection.
- **Private experiment, customer-specific code, local R&D, or sensitive material:** keep it out of public forks and upstream PRs.

If you're unsure, use the decision guide in [`docs/developer/sharing-and-safety.md`](docs/developer/sharing-and-safety.md).
=======
# Contributing to BioDockify

Thank you for your interest in building the future of autonomous pharmaceutical research! We prioritize scientific rigor, code safety, and user privacy.

## Development Standards

### 1. "Pharma-Grade" Safety
*   **No Hallucinations**: All features involving text generation MUST implement a verification step or citation lock.
*   **Privacy First**: No telemetry is strictly preferred. If added, it must be opt-in.
*   **Local Default**: Features should function (even if degraded) without internet access using local LLMs.

### 2. Code Quality
*   **Frontend**: React Functional Components, Typed Props, Lucide Icons.
*   **Backend**: Type-hinted Python, Pydantic Models for all data exchange.
*   **Commits**: Conventional Commits (e.g., `feat: add semantic scholar ranking`, `fix: battery monitor race condition`).

### 3. Architecture
*   **UI**: `ui/src/components` (Dumb components) vs `ui/src/app` (Page logic).
*   **Orchestration**: `orchestration/planner` (Logic) vs `orchestration/runtime` (Execution).

## Getting Started

1.  Ensure you have `Ollama` running for local tests.
2.  Run `pytest` to check compliance modules.
3.  Use `npm run lint` before pushing frontend code.
>>>>>>> 3768e8a174058c75c6c7fdc6d99db17d246d1fed


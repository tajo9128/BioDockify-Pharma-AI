# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.0.x   | :x:                |

## Reporting a Vulnerability

We take the security of BioDockify seriously. If you discover a security vulnerability, please do **NOT** open a public issue.

*   **Email:** Please email [your-email@example.com] with a description of the vulnerability.
*   **Response:** We will aim to acknowledge your email within 48 hours.

## Data Privacy Architecture
BioDockify is built with a **"Local-First"** security philosophy to protect pharmaceutical Intellectual Property (IP).

### 1. Local Processing
*   **Inference:** All BioNER (entity extraction) and Graph processing occur locally on your machine within the Docker container.
*   **Database:** The Neo4j database is hosted on `localhost` and file-based. No data is synced to a cloud backend managed by us.

### 2. External APIs (Optional)
*   **LLMs:** If you configure the system to use OpenAI/Gemini/Claude APIs for the "Agent" reasoning, text snippets *will* be sent to those providers.
*   **Control:** This is strictly opt-in. You must provide your own API Key. We do not proxy or store your keys.
*   **Local Alternatives:** We are working on supporting local LLMs (Llama 3, Mistral) via Ollama to enable a 100% air-gapped workflow in future versions.

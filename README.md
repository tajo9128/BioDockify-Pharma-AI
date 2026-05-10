# BioDockify Pharma AI

AI-powered research assistant for pharmaceutical and biomedical research.

## Quick Start

```bash
docker run -d -p 80:80 --name biodockify \
  -v biodockify_usr:/usr \
  tajo9128/biodockify-ai:latest
```

Or run with specific version:
```bash
docker run -d -p 80:80 --name biodockify \
  -v biodockify_usr:/usr \
  tajo9128/biodockify-ai:v1.0.0
```

Then open http://localhost in your browser.

## Features

- AI Research Assistant with proactive research capabilities
- Custom blue theme (#0077B6)
- Browser automation for research
- File management and code execution
- Memory and knowledge management
- Multi-agent cooperation

## Version

v1.0.0
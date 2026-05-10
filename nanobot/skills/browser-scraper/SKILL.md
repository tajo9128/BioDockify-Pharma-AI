---
name: browser-scraper
description: Advanced browser automation for web scraping, login automation, and NotebookLM uploads using Playwright.
metadata: {"nanobot":{"emoji":"🌐","requires":{"bins":["playwright"]},"install":[{"id":"pip","kind":"pip","package":"playwright","label":"Install Playwright"}]}}
---

# Browser Scraper Skill

Advanced browser automation for Agent Zero research workflows.

## Capabilities

- **Web Scraping**: Extract content from any website
- **Login Automation**: Persistent browser sessions with cookie storage
- **NotebookLM Upload**: Automated document uploads
- **PDF Download**: Capture research papers

## When to use

Use this skill when user asks:
- "scrape this website"
- "login to my Google account"
- "upload documents to NotebookLM"
- "download PDFs from this page"
- "automate browser task"

## Usage

### Basic Web Scraping
```python
from agent_zero.skills.browser_scraper import BrowserScraper

scraper = BrowserScraper()
await scraper.start()

# Scrape a page
content = await scraper.scrape_page("https://example.com")

# Download PDF
await scraper.download_pdf("https://example.com/paper.pdf", "./downloads/")

await scraper.close()
```

### Login Automation (Persistent)
```python
# First-time login (saves cookies)
await scraper.login_google("user@gmail.com", "app_password")

# Future runs auto-login via cookies
await scraper.restore_session()
```

### NotebookLM Upload
```python
notebook_url = await scraper.upload_to_notebooklm([
    "./research/paper1.pdf",
    "./research/paper2.pdf"
])
print(f"Notebook ready: {notebook_url}")
```

## Configuration

Environment variables:
- `BROWSER_HEADLESS`: Run headless (default: true)
- `BROWSER_PROFILE_PATH`: Cookie storage path
- `BROWSER_TIMEOUT`: Page load timeout (ms)

## Security

- Credentials encrypted with AES
- Cookies stored in encrypted volume
- No plaintext password logging

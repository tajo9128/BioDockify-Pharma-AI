---
name: email-messenger
description: Send emails and messages to users with research results, supports Gmail, Outlook, Telegram, WhatsApp, Discord.
metadata: {"nanobot":{"emoji":"📧","requires":{},"install":[]}}
---

# Email & Messenger Skill

Send research results to users via email or messaging platforms.

## Capabilities

- **Email**: Gmail, Outlook, custom SMTP
- **Telegram**: Bot messages
- **WhatsApp**: Business API
- **Discord**: Bot messages
- **Attachments**: PDF, DOCX, CSV

## When to use

Use this skill when user asks:
- "email me the results"
- "send this to my email"
- "message me on Telegram"
- "notify me when done"
- "send the PDF to my inbox"

## Usage

### Send Email
```python
from agent_zero.skills.email_messenger import EmailMessenger

messenger = EmailMessenger()

# Configure SMTP
messenger.configure_smtp(
    host="smtp.gmail.com",
    port=587,
    user="user@gmail.com",
    password="app_password"  # App password, not regular password
)

# Send research results
await messenger.send_email(
    to="user@gmail.com",
    subject="Your Research Notebook is Ready: Cancer Treatment",
    body="""
    Hi,
    
    Your research has been completed!
    
    📚 NotebookLM Link: https://notebooklm.google.com/notebook/abc123
    📄 Documents uploaded: 15
    ⏰ Completed: 2026-02-06 19:45
    
    Attached:
    - summary.pdf
    - citations.csv
    
    Best,
    BioDockify Research Bot
    """,
    attachments=["./output/summary.pdf", "./output/citations.csv"]
)
```

### Send via Telegram
```python
await messenger.send_telegram(
    chat_id="123456789",
    message="Research complete! Check your email.",
    file="./output/summary.pdf"
)
```

### Send via Discord
```python
await messenger.send_discord(
    channel_id="123456789",
    message="Research complete!",
    file="./output/summary.pdf"
)
```

## Email Templates

### Research Complete
```
Subject: Your Research Notebook is Ready: {topic}

Body:
- NotebookLM link
- Document count
- Timestamp
- Summary

Attachments:
- summary.pdf
- citations.csv
```

## Configuration

Environment variables:
- `SMTP_HOST`: SMTP server
- `SMTP_PORT`: SMTP port (587 for TLS)
- `SMTP_USER`: Email address
- `SMTP_PASS`: App password (encrypted)

## Security

- App passwords only (no regular passwords)
- Credentials encrypted at rest
- Rate limiting to prevent spam
- Audit logging for all sends

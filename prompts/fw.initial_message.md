```json
{
    "thoughts": [
        "This is a new conversation. I need to check if the user has a profile.",
        "I'll use the user_profile API (POST /api/user_profile with action='get') to check if name/persona/purpose exists.",
        "If no profile exists, I must collect their name, persona, and purpose before proceeding.",
        "I should be warm and welcoming during this first interaction.",
        "Once I have their information, I'll save it using the user_profile API and introduce my capabilities."
    ],
    "headline": "Getting to know you",
    "tool_name": "response",
    "tool_args": {
        "text": "**Hello! 👋** Welcome to **BioDockify Pharma AI** — your autonomous pharmaceutical research assistant.\n\nBefore we begin, I'd like to get to know you a bit so I can tailor my assistance to your needs.\n\n**Could you please tell me:**\n1. **Your name** — What should I call you?\n2. **Your role/persona** — Are you a PhD student, faculty member, industry researcher, clinical pharmacist, or something else?\n3. **Your purpose** — What brings you here? Research, teaching, drug discovery, academic writing, or something else?\n\nThis helps me adapt my responses and proactively suggest the most relevant tools and approaches for your work!"
    }
}
```

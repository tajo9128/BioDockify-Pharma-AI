import httpx
import os
from typing import Any

class DiscordTool:
    """
    Tool for interacting with Discord via REST API (Bot Token).
    Uses 'NANOBOT_CHANNELS__DISCORD__TOKEN' env var or config if passed.
    """

    name = "discord_tool"
    description = (
        "Interact with Discord. Actions: 'announce' (send message), 'history' (read messages). "
        "Args: 'channel_id', 'content'."
    )

    def __init__(self, token: str = ""):
        self.token = token
        # Try to find token from env if not provided
        if not self.token:
             self.token = os.environ.get("NANOBOT_CHANNELS__DISCORD__TOKEN", "")

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["announce", "history"],
                        "description": "Action to perform."
                    },
                    "channel_id": {
                        "type": "string",
                        "description": "Discord Channel ID."
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content (for announce)."
                    }
                },
                "required": ["action", "channel_id"]
            }
        }

    async def execute(self, action: str, channel_id: str, **kwargs: Any) -> str:
        if not self.token:
            return "Error: Discord Bot Token not configured."
        
        headers = {"Authorization": f"Bot {self.token}"}
        base_url = "https://discord.com/api/v10"

        async with httpx.AsyncClient() as client:
            try:
                if action == "announce":
                    content = kwargs.get("content")
                    if not content:
                        return "Error: 'content' required."
                    
                    url = f"{base_url}/channels/{channel_id}/messages"
                    resp = await client.post(url, headers=headers, json={"content": content})
                    if resp.status_code in (200, 201):
                        return "Message sent successfully."
                    else:
                        return f"Error sending message: {resp.status_code} - {resp.text}"

                elif action == "history":
                    # Get last 10 messages
                    url = f"{base_url}/channels/{channel_id}/messages?limit=10"
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        messages = resp.json()
                        result = f"Last 10 messages in {channel_id}:\n"
                        for m in reversed(messages):
                            author = m.get('author', {}).get('username', 'Unknown')
                            content = m.get('content', '')
                            result += f"[{author}]: {content}\n"
                        return result
                    else:
                        return f"Error fetching history: {resp.status_code} - {resp.text}"
                
                else:
                    return f"Unknown action: {action}"

            except Exception as e:
                return f"Discord Tool Error: {e}"

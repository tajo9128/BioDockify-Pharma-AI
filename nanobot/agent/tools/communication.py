"""Communication tools: email."""

from typing import Any
from nanobot.agent.tools.base import Tool

class EmailTool(Tool):
    """
    Email Automation Tool.
    Uses the shared EmailMessenger to send emails.
    """
    
    @property
    def name(self) -> str:
        return "send_email"
    
    @property
    def description(self) -> str:
        return "Send an email to a user. Requires recipient email and subject."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address."
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject."
                },
                "body": {
                    "type": "string",
                    "description": "Email body content."
                },
                "attachments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to attach (optional)."
                }
            },
            "required": ["to", "subject", "body"]
        }
        
    async def execute(self, to: str, subject: str, body: str, attachments: list[str] = None, **kwargs: Any) -> str:
        try:
            # Lazy import
            from agent_zero.skills.email_messenger import get_email_messenger
            messenger = get_email_messenger()
            
            success = await messenger.send_email(
                to=to,
                subject=subject,
                body=body,
                attachments=attachments
            )
            
            if success:
                return f"Email sent successfully to {to}."
            else:
                return "Failed to send email. Check logs/config."
                
        except ImportError:
            return "Error: Email capability not available (dependency missing)."
        except Exception as e:
            return f"Email Error: {e}"

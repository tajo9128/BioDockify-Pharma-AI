import asyncio

from helpers.extension import Extension
from helpers.print_style import PrintStyle
from helpers import errors

from helpers.errors import HandledException


class HandleCriticalException(Extension):
    async def execute(self, data: dict = {}, **kwargs):
        if not self.agent:
            return

        if not (exception:= data.get("exception")):
            return

        # when exception is HandledException, keep it active, no logging here
        if isinstance(exception, HandledException):
            return 

        # asyncio cancel - chat is being terminated, print out and re-raise as handledException
        if isinstance(exception, asyncio.CancelledError):
            PrintStyle(font_color="white", background_color="red", padding=True).print(
                f"Context {self.agent.context.id} terminated during message loop"
            )
            data["exception"] = HandledException(exception)
            return

        # other exceptions should be logged and re-raised as HandledException
        error_text = errors.error_text(exception)
        error_message = errors.format_error(exception)

        # Log full traceback to console for debugging
        PrintStyle(font_color="red", padding=True).print(error_message)

        # Show friendly message to user in chat (not raw traceback)
        friendly_msg = _friendly_error(exception)
        self.agent.context.log.log(
            type="error",
            content=friendly_msg,
        )
        PrintStyle(font_color="red", padding=True).print(
            f"{self.agent.agent_name}: {friendly_msg}"
        )

        data["exception"] = HandledException(exception)


def _friendly_error(e: Exception) -> str:
    """Convert exception to user-friendly message (no raw traceback)."""
    etype = type(e).__name__
    msg = str(e)

    # LLM / API errors
    if "litellm" in etype.lower() or "openai" in etype.lower() or "api" in etype.lower():
        return f"AI service temporarily unavailable. Please check your API key and try again. ({etype})"
    if "authentication" in msg.lower() or "api_key" in msg.lower() or "unauthorized" in msg.lower():
        return "Authentication failed. Please check your API key in Settings."
    if "rate" in msg.lower() and "limit" in msg.lower():
        return "Rate limit reached. Please wait a moment and try again."
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return "Request timed out. The AI service may be slow — please try again."
    if "connection" in msg.lower() or "network" in msg.lower():
        return "Network error. Please check your internet connection and try again."

    # RDKit / chemistry errors
    if "rdkit" in msg.lower() or "Chem" in etype:
        return f"Chemistry processing error: {msg[:100]}"

    # Generic fallback — show error type + short message, no traceback
    short_msg = msg[:150] + "..." if len(msg) > 150 else msg
    return f"An error occurred ({etype}): {short_msg}"

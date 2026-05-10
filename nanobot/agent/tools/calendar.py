import shutil
import subprocess
import json
from typing import Any, Optional
from datetime import datetime, timedelta

class CalendarTool:
    """
    Tool for interacting with Google Calendar via gcalcli.
    Requires 'gcalcli' to be installed and authenticated on the system.
    """
    
    name = "calendar"
    description = (
        "Interact with Google Calendar. "
        "Actions: 'agenda' (list events), 'add' (create event), 'quick' (quick add text). "
        "Args: 'start' (YYYY-MM-DD or 'today'), 'end', 'title', 'where', 'when'."
    )

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["agenda", "add", "quick"],
                        "description": "The action to perform."
                    },
                    "start": {
                        "type": "string",
                        "description": "Start time/date (for agenda) or event date."
                    },
                    "end": {
                        "type": "string",
                        "description": "End time/date (for agenda)."
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the event (for add)."
                    },
                    "where": {
                        "type": "string",
                        "description": "Location of the event."
                    },
                    "when": {
                        "type": "string",
                        "description": "Time of the event (e.g. '10am')."
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Duration in minutes (default 60)."
                    },
                     "text": {
                        "type": "string",
                        "description": "Text for quick add (e.g. 'Dinner at 7pm')."
                    }
                },
                "required": ["action"]
            }
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        if not shutil.which("gcalcli"):
            return "Error: 'gcalcli' not found in PATH. Please install it (pip install gcalcli) and authenticate."

        try:
            if action == "agenda":
                start = kwargs.get("start", datetime.now().strftime("%Y-%m-%d"))
                end = kwargs.get("end", (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))
                # gcalcli agenda --tsv ...
                cmd = ["gcalcli", "agenda", start, end, "--nocolor"]
                return self._run_command(cmd)

            elif action == "add":
                title = kwargs.get("title", "Untitled Event")
                where = kwargs.get("where", "")
                when = kwargs.get("when", "")
                duration = kwargs.get("duration", 60)
                # This is tricky with gcalcli's interactive mode. 
                # We'll use --noprompt with specific flags if possible, or 'quick' is better.
                # gcalcli add --title "Title" --where "Location" --when "Time" --duration 60 --noprompt
                cmd = ["gcalcli", "add", "--title", title, "--duration", str(duration), "--noprompt"]
                if where:
                    cmd.extend(["--where", where])
                if when:
                    cmd.extend(["--when", when])
                
                return self._run_command(cmd)

            elif action == "quick":
                text = kwargs.get("text", "")
                if not text:
                    return "Error: 'text' argument required for quick add."
                cmd = ["gcalcli", "quick", text, "--noprompt"]
                return self._run_command(cmd)

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Calendar Error: {e}"

    def _run_command(self, cmd: list[str]) -> str:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=15
            )
            return result.stdout.strip() if result.stdout else "Success."
        except subprocess.CalledProcessError as e:
            return f"Error executing gcalcli: {e.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out."

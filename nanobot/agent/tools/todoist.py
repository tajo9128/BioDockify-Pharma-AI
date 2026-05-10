import os
from typing import Any

class TaskTool:
    """
    Tool for interacting with Todoist.
    Requires 'todoist-api-python' installed and TODOIST_API_KEY env var.
    """

    name = "todoist"
    description = (
        "Interact with Todoist task manager. "
        "Actions: 'add' (create task), 'list' (get tasks). "
        "Args: 'content' (task name), 'due_string' (e.g. 'tomorrow at 10am')."
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
                        "enum": ["add", "list"],
                        "description": "The action to perform."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content of the task (for add)."
                    },
                    "due_string": {
                        "type": "string",
                        "description": "Natural language due date (e.g. 'tomorrow')."
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Optional project ID."
                    }
                },
                "required": ["action"]
            }
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        try:
            from todoist_api_python.api import TodoistAPI
        except ImportError:
            return "Error: 'todoist-api-python' not installed."

        api_key = os.environ.get("TODOIST_API_KEY")
        if not api_key:
            return "Error: TODOIST_API_KEY environment variable not set."

        api = TodoistAPI(api_key)

        try:
            if action == "add":
                content = kwargs.get("content")
                if not content:
                    return "Error: 'content' is required for adding a task."
                
                due_string = kwargs.get("due_string")
                task = await api.add_task(content=content, due_string=due_string)
                return f"Task created: {task.content} (ID: {task.id}) due {task.due.string if task.due else 'No date'}"

            elif action == "list":
                tasks = await api.get_tasks()
                if not tasks:
                    return "No active tasks found."
                
                # Format simple list
                result = "Active Tasks:\n"
                for t in tasks[:10]: # Limit to 10
                    due = t.due.string if t.due else "No Date"
                    result += f"- {t.content} (Due: {due})\n"
                return result

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Todoist Error: {e}"

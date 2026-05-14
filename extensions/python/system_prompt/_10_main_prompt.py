from typing import Any
import json
import os

from helpers.extension import Extension, extensible
from helpers import files
from agent import Agent, LoopData


class MainPrompt(Extension):

    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs: Any,
    ):
        if not self.agent:
            return
        prompt = await build_prompt(self.agent)
        system_prompt.append(prompt)


@extensible
async def build_prompt(agent: Agent) -> str:
    # Load user profile if it exists and pass as template variables
    profile_vars = {}
    profile_path = files.get_abs_path("usr/user_profile.json")
    if os.path.exists(profile_path):
        try:
            with open(profile_path) as f:
                profile = json.load(f)
                if profile.get("name"):
                    profile_vars["user_name"] = profile["name"]
                    profile_vars["user_persona"] = profile.get("persona", "")
                    profile_vars["user_purpose"] = profile.get("purpose", "")
        except (json.JSONDecodeError, IOError):
            pass

    return agent.read_prompt("agent.system.main.md", **profile_vars)

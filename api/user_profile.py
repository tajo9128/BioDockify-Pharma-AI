from helpers.api import ApiHandler, Request
from helpers import files
import json
import os

PROFILE_FILE = files.get_abs_path("usr/user_profile.json")


class UserProfile(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "get")

        if action == "get":
            if os.path.exists(PROFILE_FILE):
                with open(PROFILE_FILE) as f:
                    profile = json.load(f)
                return {"profile": profile, "exists": True}
            return {"profile": None, "exists": False}

        elif action == "save":
            name = input.get("name", "").strip()
            persona = input.get("persona", "").strip()
            purpose = input.get("purpose", "").strip()

            if not name or not persona or not purpose:
                return {"error": "name, persona, and purpose are required"}

            profile = {
                "name": name,
                "persona": persona,
                "purpose": purpose,
                "saved_at": str(__import__("datetime").datetime.now())
            }

            os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
            with open(PROFILE_FILE, "w") as f:
                json.dump(profile, f, indent=2)

            return {"profile": profile, "saved": True}

        return {"error": "Unknown action"}

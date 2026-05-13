from helpers.api import ApiHandler, Request
from helpers import files
import re


class UpdateCheck(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        current = input.get("current_version", "v0.0.0")

        # Read version from gitinfo or fallback to current
        label_file = files.get_abs_path("identity.md")
        latest = current
        try:
            content = files.read_file(label_file)
            m = re.search(r'v?\d+\.\d+\.\d+', content or "")
            if m:
                latest = "v" + m.group().lstrip("v")
        except Exception:
            latest = current

        # Check if update is available (compare versions)
        update_available = False
        try:
            def parse_ver(v):
                parts = v.lstrip("v").split(".")
                return tuple(int(p) for p in parts[:3])
            current_parts = parse_ver(current)
            latest_parts = parse_ver(latest)
            update_available = latest_parts > current_parts
        except Exception:
            pass

        return {
            "current_version": current,
            "latest_version": latest,
            "update_available": update_available,
            "release_url": "https://github.com/tajo9128/BioDockify-Pharma-AI/releases"
        }

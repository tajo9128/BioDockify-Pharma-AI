from helpers.api import ApiHandler, Request, Response
from helpers import errors, git


class HealthCheck(ApiHandler):

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        gitinfo = None
        error = None
        try:
            gitinfo = git.get_git_info()
        except Exception as e:
            error = errors.error_text(e)

        health = {"status": "ok"}
        try:
            from api.system_health import SystemHealth
            health_check = SystemHealth()
            health = await health_check.process({"action": "all"}, request)
        except Exception:
            pass

        return {"gitinfo": gitinfo, "health": health, "error": error}

from helpers.api import ApiHandler, Request, Response

from helpers import process

class Restart(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_csrf(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        process.reload()
        return {"status": "ok", "message": "Server restarted"}
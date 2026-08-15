import secrets
from urllib.parse import urlparse
from helpers.api import (
    ApiHandler,
    Input,
    Output,
    Request,
    Response,
    session,
)
from helpers import runtime, dotenv, login
import fnmatch

ALLOWED_ORIGINS_KEY = "ALLOWED_ORIGINS"


class GetCsrfToken(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: Input, request: Request) -> Output:

        # check for allowed origin to prevent dns rebinding attacks
        origin_check = await self.check_allowed_origin(request)
        if not origin_check["ok"]:
            return {
                "ok": False,
                "error": f"Origin {self.get_origin_from_request(request)} not allowed when login is disabled. Set login and password or add your URL to ALLOWED_ORIGINS env variable. Currently allowed origins: {','.join(origin_check['allowed_origins'])}",
            }

        # generate a csrf token if it doesn't exist
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)

        # return the csrf token and runtime id
        return {
            "ok": True,
            "token": session["csrf_token"],
            "runtime_id": runtime.get_runtime_id(),
        }

    async def check_allowed_origin(self, request: Request):
        # if login is required, this check is unnecessary
        if login.is_login_required():
            return {"ok": True, "origin": "", "allowed_origins": ""}
        # initialize allowed origins if not yet set
        self.initialize_allowed_origins(request)
        # otherwise, check if the origin is allowed
        return await self.is_allowed_origin(request)

    async def is_allowed_origin(self, request: Request):
        # get the origin from the request
        origin = self.get_origin_from_request(request)
        if not origin:
            return {"ok": False, "origin": "", "allowed_origins": ""}

        # list of allowed origins
        allowed_origins = await self.get_allowed_origins()

        # check if the origin is allowed
        match = any(
            fnmatch.fnmatch(origin, allowed_origin)
            for allowed_origin in allowed_origins
        )
        return {"ok": match, "origin": origin, "allowed_origins": allowed_origins}

    def get_origin_from_request(self, request: Request):
        # get from origin
        r = request.headers.get("Origin") or request.environ.get("HTTP_ORIGIN")
        if not r:
            # try referer if origin not present
            r = (
                request.headers.get("Referer")
                or request.referrer
                or request.environ.get("HTTP_REFERER")
            )
        if not r:
            return None
        # parse and normalize
        p = urlparse(r)
        if not p.scheme or not p.hostname:
            return None
        return f"{p.scheme}://{p.hostname}" + (f":{p.port}" if p.port else "")

    async def get_allowed_origins(self) -> list[str]:
        # get the allowed origins from the environment
        allowed_origins = [
            origin.strip()
            for origin in (dotenv.get_dotenv_value(ALLOWED_ORIGINS_KEY) or "").split(
                ","
            )
            if origin.strip()
        ]

        # if there are no allowed origins, allow default localhosts
        if not allowed_origins:
            allowed_origins = self.get_default_allowed_origins()

        # always allow tunnel url if running
        try:
            from api.tunnel_proxy import process as tunnel_api_process

            tunnel = await tunnel_api_process({"action": "get"})
            if tunnel and isinstance(tunnel, dict) and tunnel["success"]:
                allowed_origins.append(tunnel["tunnel_url"])
        except Exception:
            pass

        return allowed_origins

    def get_default_allowed_origins(self) -> list[str]:
        return [
            "*://localhost",
            "*://localhost:*",
            "*://127.0.0.1",
            "*://127.0.0.1:*",
            "*://0.0.0.0",
            "*://0.0.0.0:*",
        ]

    def initialize_allowed_origins(self, request: Request):
        """
        SECURITY: Origin auto-allowlist removed (was a DNS-rebinding attack vector).

        Previously, the first non-localhost origin to hit the server was
        permanently saved to ALLOWED_ORIGINS in .env. A malicious website
        could get itself allow-listed, then (after DNS rebinding) issue
        authenticated cross-origin requests.

        Now: only localhost origins are allowed by default. For remote
        access, users must explicitly set ALLOWED_ORIGINS in usr/.env:
            ALLOWED_ORIGINS=http://192.168.1.100,http://myserver.example.com
        """
        # No auto-allowlist — return without saving anything
        return

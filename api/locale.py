"""Locale API — returns currency/timezone/unit config from env vars."""
from helpers.api import ApiHandler, Request, Response
import os

LOCALE_MAP = {
    "en-IN": {"symbol": "₹", "currency": "INR", "tz": "Asia/Kolkata"},
    "en-US": {"symbol": "$", "currency": "USD", "tz": "America/New_York"},
    "en-GB": {"symbol": "£", "currency": "GBP", "tz": "Europe/London"},
    "en-EU": {"symbol": "€", "currency": "EUR", "tz": "Europe/Berlin"},
    "ja-JP": {"symbol": "¥", "currency": "JPY", "tz": "Asia/Tokyo"},
    "en-AU": {"symbol": "A$", "currency": "AUD", "tz": "Australia/Sydney"},
}


class LocaleHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        locale = os.environ.get("BIODOCKIFY_LOCALE", "en-US")
        cfg = LOCALE_MAP.get(locale, LOCALE_MAP["en-US"])
        return {"locale": locale, "symbol": cfg["symbol"], "currency": cfg["currency"],
                "timezone": cfg["tz"], "unitSystem": os.environ.get("BIODOCKIFY_UNITS", "metric")}

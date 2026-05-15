"""Kokoro TTS + Edge-TTS + Browser fallback text-to-speech API."""
from helpers.api import ApiHandler, Request, Response
import base64
import io
import os
import logging

logger = logging.getLogger("kokoro_tts")
_kokoro_instance = None

def _get_kokoro():
    global _kokoro_instance
    if _kokoro_instance is None:
        try:
            from kokoro_onnx import Kokoro
            _kokoro_instance = Kokoro()
        except ImportError:
            _kokoro_instance = False
    return _kokoro_instance if _kokoro_instance is not False else None


class KokoroTTS(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        text = (input.get("text", "") or "").strip()
        voice = (input.get("voice", "") or "default").strip()
        speed = float(input.get("speed", "1.0") or 1.0)

        if not text:
            return {"error": "Text is required", "audio": None}

        text = text[:5000]  # limit for performance

        # Try Kokoro first (best quality)
        audio = await self._try_kokoro(text, voice, speed)
        if audio:
            return audio

        # Try Edge-TTS (good quality, no API key)
        audio = await self._try_edge_tts(text, voice, speed)
        if audio:
            return audio

        # Fallback: return text for browser SpeechSynthesis
        return {
            "fallback": True,
            "text": text,
            "message": "TTS engines unavailable. Using browser speech synthesis.",
            "audio": None,
        }

    async def _try_kokoro(self, text: str, voice: str, speed: float) -> dict | None:
        try:
            import soundfile as sf
            kokoro = _get_kokoro()
            if kokoro is None: return None
            lang_code = voice if voice in ["en-us", "en-gb", "ja", "zh", "ko"] else "en-us"
            samples, sample_rate = kokoro.create(text, voice=lang_code, speed=speed)

            buffer = io.BytesIO()
            sf.write(buffer, samples, sample_rate, format="WAV")
            audio_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return {
                "audio": audio_b64,
                "format": "wav",
                "sample_rate": sample_rate,
                "engine": "kokoro",
                "duration_sec": round(len(samples) / sample_rate, 1),
            }
        except ImportError:
            return None
        except Exception as e:
            logger.warning(f"Kokoro TTS failed: {e}")
            return None

    async def _try_edge_tts(self, text: str, voice: str, speed: float) -> dict | None:
        try:
            import edge_tts
            import asyncio
            from edge_tts import Communicate

            voice_map = {
                "en-us-female": "en-US-AriaNeural",
                "en-us-male": "en-US-GuyNeural",
                "en-gb-female": "en-GB-SoniaNeural",
                "en-gb-male": "en-GB-RyanNeural",
                "default": "en-US-AriaNeural",
            }
            edge_voice = voice_map.get(voice, "en-US-AriaNeural")

            rate = f"{'+' if speed > 1 else ''}{int((speed - 1) * 100)}%"
            communicate = Communicate(text, edge_voice, rate=rate)

            buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])

            audio_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return {
                "audio": audio_b64,
                "format": "mp3",
                "engine": "edge-tts",
            }
        except ImportError:
            return None
        except Exception as e:
            logger.warning(f"Edge-TTS failed: {e}")
            return None

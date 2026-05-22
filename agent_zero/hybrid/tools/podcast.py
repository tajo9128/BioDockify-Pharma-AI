"""
Podcast Tool - Generate audio recap of research using edge-tts (FREE).
"""
import logging
import os

logger = logging.getLogger(__name__)

VALID_VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}

class PodcastTool:
    """Generate audio podcasts from text via edge-tts."""

    async def execute(self, text: str, voice: str = "nova") -> str:
        """Generate audio file. Returns the output file path."""
        logger.info(f"Generating podcast for text length {len(text)}, voice={voice}")

        if not text or not text.strip():
            return "Error: no text provided for podcast"

        voice = voice if voice in VALID_VOICES else "nova"

        try:
            from modules.surfsense.audio import generate_podcast_audio

            output_dir = os.path.join(os.getcwd(), "data", "podcasts")
            os.makedirs(output_dir, exist_ok=True)

            safe_name = "".join(c for c in text[:30] if c.isalnum() or c in " _-").strip()
            if not safe_name:
                safe_name = "podcast"
            output_path = os.path.join(output_dir, f"{safe_name}.mp3")

            await generate_podcast_audio(text=text, voice=voice, output_path=output_path)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Podcast saved: {output_path}")
                return output_path
            return f"Error: podcast file not created at {output_path}"
        except ImportError:
            return "Error: edge-tts not installed. Run: pip install edge-tts"
        except Exception as e:
            logger.error(f"Podcast generation failed: {e}")
            return f"Error generating podcast: {str(e)}"

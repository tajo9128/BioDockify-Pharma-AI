from openai import OpenAI
import os
from typing import Optional
from pathlib import Path

# Helper to get client from environment or config
def get_openai_client():
    # Try to load API Key from different possible sources
    api_key = os.getenv("OPENAI_API_KEY") 
    
    # If using custom compatible endpoints (like LM Studio which might not support audio), this might fail.
    # So we strictly look for keys that support Audio (OpenAI usually).
    if not api_key:
        # Fallback to loading from config if needed, or raise handy error
        # For now, assume environment variable or explicit passing
        pass
        
    return OpenAI(api_key=api_key)

async def generate_podcast_audio(text: str, voice: str = "alloy", output_path: str = "output.mp3", api_key: str = None) -> str:
    """
    Generates an audio file from text using OpenAI TTS.
    Returns absolute path to the generated file.
    """
    try:
        client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
        # Ensure output directory exists (Fix for Bug #7)
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        response.stream_to_file(output_path)
        return str(Path(output_path).absolute())
        
    except Exception as e:
        print(f"TTS Error: {e}")
        raise ValueError(f"Failed to generate audio: {e}")


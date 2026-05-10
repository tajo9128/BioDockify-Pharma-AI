"""
SurfSense Audio Output Module - FREE VERSION
Uses edge-tts (Microsoft Edge TTS) - NO API KEY REQUIRED
Perfect for students and educational use.
"""
import os
from typing import Optional
from pathlib import Path
import asyncio

# Lazy import for edge_tts - allows module to load without the dependency
# This is useful for CI environments where edge_tts may not be installed
_edge_tts = None

def _get_edge_tts():
    """Lazily import edge_tts only when needed."""
    global _edge_tts
    if _edge_tts is None:
        try:
            import edge_tts as _tts_module
            _edge_tts = _tts_module
        except ImportError:
            raise ImportError(
                "edge_tts is not installed. Install it with: pip install edge-tts"
            )
    return _edge_tts


# Available voices from Microsoft Edge TTS
# Students can choose from 100+ free voices
VALID_VOICES = {
    # English
    'en-US-AriaNeural': 'Aria (US English, Female)',
    'en-US-GuyNeural': 'Guy (US English, Male)',
    'en-GB-SoniaNeural': 'Sonia (UK English, Female)',
    'en-GB-RyanNeural': 'Ryan (UK English, Male)',
    'en-AU-NatashaNeural': 'Natasha (Australian, Female)',
    'en-IN-NeerjaNeural': 'Neerja (Indian, Female)',
    # Chinese
    'zh-CN-XiaoxiaoNeural': 'Xiaoxiao (Chinese, Female)',
    'zh-CN-YunxiNeural': 'Yunxi (Chinese, Male)',
    # Spanish
    'es-ES-ElviraNeural': 'Elvira (Spanish, Female)',
    'es-MX-DaliaNeural': 'Dalia (Mexican, Female)',
    # French
    'fr-FR-DeniseNeural': 'Denise (French, Female)',
    'fr-FR-HenriNeural': 'Henri (French, Male)',
    # German
    'de-DE-KatjaNeural': 'Katja (German, Female)',
    'de-DE-ConradNeural': 'Conrad (German, Male)',
    # Japanese
    'ja-JP-NanamiNeural': 'Nanami (Japanese, Female)',
    # Arabic
    'ar-SA-ZariyahNeural': 'Zariyah (Arabic, Female)',
    # Korean
    'ko-KR-SunHiNeural': 'SunHi (Korean, Female)',
    # Portuguese
    'pt-BR-FranciscaNeural': 'Francisca (Brazilian, Female)',
    # Italian
    'it-IT-ElsaNeural': 'Elsa (Italian, Female)',
    # Russian
    'ru-RU-SvetlanaNeural': 'Svetlana (Russian, Female)',
}

# Default voice (matches OpenAI's 'alloy' style)
DEFAULT_VOICE = 'en-US-AriaNeural'

async def generate_podcast_audio(
    text: str,
    voice: str = "alloy",
    output_path: str = "output.mp3"
) -> str:
    """
    Generates audio file from text using FREE edge-tts (Microsoft Edge TTS).
    NO API KEY REQUIRED - Perfect for students!

    Args:
        text: Text to convert to speech
        voice: Voice identifier (OpenAI-style names mapped to Edge voices)
            - alloy, echo, fable, onyx, nova, shimmer → English voices
            - Any Edge voice name (e.g., 'en-US-AriaNeural')
        output_path: Path to save MP3 file

    
    Returns:
        Absolute path to generated MP3 file
    
    Raises:
        ValueError: If text is empty or voice is invalid
    """
    if not text or len(text.strip()) == 0:
        raise ValueError("Text cannot be empty")
    
    # Map OpenAI voice names to Edge voices
    voice_mapping = {
        'alloy': 'en-US-AriaNeural',      # Default US English female
        'echo': 'en-US-GuyNeural',          # US English male
        'fable': 'en-GB-SoniaNeural',       # UK English female
        'onyx': 'en-GB-RyanNeural',        # UK English male
        'nova': 'en-AU-NatashaNeural',      # Australian female
        'shimmer': 'en-IN-NeerjaNeural',    # Indian female
    }
    
    # Use mapped voice or default
    edge_voice = voice_mapping.get(voice, voice)
    
    # Validate voice
    if edge_voice not in VALID_VOICES:
        print(f"Warning: Voice '{voice}' not recognized, using default")
        print(f"Available voices: {list(VALID_VOICES.keys())[:10]}...")
        edge_voice = DEFAULT_VOICE
    
    print(f"🎙️ Using FREE edge-tts voice: {edge_voice} ({VALID_VOICES[edge_voice]})")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Get edge_tts module (lazy import)
        edge_tts = _get_edge_tts()
        
        # Create edge-tts communicate object
        communicate = edge_tts.Communicate(text, edge_voice)
        
        # Save audio to file (async)
        await communicate.save(output_path)
        
        file_size = os.path.getsize(output_path)
        print(f"✅ Audio generated: {output_path} ({file_size:,} bytes)")
        
        return str(Path(output_path).absolute())
        
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        raise ValueError(f"Failed to generate audio: {e}")


def get_available_voices() -> dict:
    """
    Get all available free voices from edge-tts.
    
    Returns:
        Dictionary mapping voice IDs to descriptions
    """
    return VALID_VOICES



def get_voice_for_language(language_code: str) -> str:
    """
    Get a suitable voice for a language code (ISO 639-1).
    Supports international students!
    
    Args:
        language_code: ISO 639-1 language code (en, zh, es, fr, de, etc.)
    
    Returns:
        Edge voice identifier
    """
    language_voice_map = {
        'en': 'en-US-AriaNeural',
        'zh': 'zh-CN-XiaoxiaoNeural',
        'es': 'es-ES-ElviraNeural',
        'fr': 'fr-FR-DeniseNeural',
        'de': 'de-DE-KatjaNeural',
        'ja': 'ja-JP-NanamiNeural',
        'ko': 'ko-KR-SunHiNeural',
        'ar': 'ar-SA-ZariyahNeural',
        'pt': 'pt-BR-FranciscaNeural',
        'it': 'it-IT-ElsaNeural',
        'ru': 'ru-RU-SvetlanaNeural',
    }
    
    return language_voice_map.get(language_code, DEFAULT_VOICE)



# Convenience function for students - simple interface
async def text_to_speech(text: str, output_file: str = "speech.mp3") -> str:
    """
    Simple text-to-speech for students.
    Uses default English voice, no API key needed.
    
    Args:
        text: Text to speak
        output_file: Where to save the audio
    
    Returns:
        Path to generated audio file
    """
    return await generate_podcast_audio(text, voice="alloy", output_path=output_file)



if __name__ == "__main__":
    # Test the FREE TTS
    import asyncio
    
    async def test():
        test_text = "Hello! This is a free text-to-speech test for students. No API key required!"
        output = await text_to_speech(test_text, "test_output.mp3")
        print(f"Test audio saved to: {output}")
        print(f"Available voices: {len(VALID_VOICES)} FREE voices")
    
    asyncio.run(test())

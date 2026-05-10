import asyncio
import os
import sys
import pytest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment for testing if key is missing
if not os.getenv("OPENAI_API_KEY"):
    print("[WARN] No OPENAI_API_KEY found. Using Mock Audio Generation.")
    os.environ["MOCK_TTS"] = "true"

# Check for optional dependencies
try:
    from modules.surfsense.audio import generate_podcast_audio
    from modules.surfsense.slides import generate_slides
    from modules.surfsense.video import create_video_summary
    HAS_SURFSENSE_DEPS = True
except ImportError as e:
    HAS_SURFSENSE_DEPS = False
    IMPORT_ERROR = str(e)

async def test_pipeline():
    if not HAS_SURFSENSE_DEPS:
        pytest.skip(f"SurfSense dependencies not available: {IMPORT_ERROR}")
    print("Testing SurfSense Video Pipeline...")
    
    # Ensure output dir exists
    os.makedirs("test_output", exist_ok=True)
    
    # 1. Test Audio
    print("[1/3] Generating Audio...")
    audio_path = "test_output/audio.mp3"
    try:
        if os.environ.get("MOCK_TTS") == "true":
            # Create dummy mp3 file
            with open(audio_path, "wb") as f:
                f.write(b'\x00' * 1024) # 1KB of silence/junk
            print("[OK] Audio generated (MOCK): " + audio_path)
        else:
            audio_path = await generate_podcast_audio(
                "Welcome to BioDockify. This is a test of the automated research video engine.",
                output_path=audio_path
            )
            print("[OK] Audio generated: " + audio_path)
    except Exception as e:
        print("[ERR] Audio failed: " + str(e))
        return

    # 2. Test Slides
    print("[2/3] Generating Slides...")
    md_text = """
# BioDockify Video Engine
- Automated Synthesis
- Multi-Modal Output
---
# Features
- Podcast Generation
- Slide Deck Creation
- Video Stitching
    """
    try:
        slide_paths = await generate_slides(md_text, output_dir="test_output/slides")
        print(f"[OK] Slides generated: {len(slide_paths)}")
    except Exception as e:
        print("[ERR] Slides failed: " + str(e))
        import traceback
        traceback.print_exc()
        return

    # 3. Test Video
    print("[3/3] Stitching Video...")
    try:
        video_path = await create_video_summary(slide_paths, audio_path, output_path="test_output/final_video.mp4")
        print("[OK] Video generated: " + video_path)
    except Exception as e:
        print("[ERR] Video failed: " + str(e))
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    # On Windows, ProactorEventLoop is required for subprocesses (default in 3.8+)
    # We do NOT want to use SelectorEventLoop.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    asyncio.run(test_pipeline())

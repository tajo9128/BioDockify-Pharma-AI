import ffmpeg
import os
from typing import List
from pathlib import Path
import math

async def create_video_summary(slide_images: List[str], audio_file: str, output_path: str = "summary.mp4") -> str:
    """
    Combines slide images and audio into a final video.
    Each slide is displayed for an equal portion of the audio duration.
    Returns absolute path to the generated video.
    """
    try:
        # 1. Get audio duration
        probe = ffmpeg.probe(audio_file)
        audio_duration = float(probe['format']['duration'])
        
        num_slides = len(slide_images)
        if num_slides == 0:
            raise ValueError("No slides provided for video generation")
            
        slide_duration = audio_duration / num_slides
        
        # 2. Create input streams for each slide
        # We need to create a concat file for ffmpeg or use complex filter
        # For simplicity/reliability with many files, creating a concat input text file is safer
        
        concat_file_path = str(Path(output_path).parent / "slides_input.txt")
        with open(concat_file_path, "w") as f:
            for slide in slide_images:
                # Escape path for ffmpeg
                safe_path = slide.replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
                f.write(f"duration {slide_duration}\n")
            # Repeat last image to prevent cut-off
            last_slide = slide_images[-1].replace("\\", "/")
            f.write(f"file '{last_slide}'\n")
            
        # 3. Stitch Video
        # Input 0: Visual (from concat file)
        # Input 1: Audio
        
        # Resolve ffmpeg binary path from imageio-ffmpeg
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        # WARNING: ffmpeg-python doesn't easily support custom binary path without monkeypatching or PATH mod.
        # But we can create the process manually or use `cmd` argument if supported.
        # `ffmpeg-python` uses `subprocess.Popen(['ffmpeg', ...])`.
        # Best way: temporarily add to PATH for this process.
        
        env = os.environ.copy()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
        
        # We must re-import/configure? No, subprocess inherits env.
        # But ffmpeg-python calls Popen internally. use .run(cmd=ffmpeg_exe) if available.
        # Actually .run() accepts `cmd` argument!
        
        input_video = ffmpeg.input(concat_file_path, format='concat', safe=0)
        input_audio = ffmpeg.input(audio_file)
        
        (
            ffmpeg
            .output(
                input_video, 
                input_audio, 
                output_path, 
                vcodec='libx264', 
                acodec='aac', 
                pix_fmt='yuv420p',
                r=24,  # 24 fps
                **{'shortest': None} # Fix for Bug #6: Invalid parameter name
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, cmd=ffmpeg_exe)
        )
        
        # Cleanup (Fix for Bug #9)
        try:
            os.remove(concat_file_path)
        except Exception as e:
            import logging
            logging.getLogger("surfsense.video").debug(f"Failed to remove concat file {concat_file_path}: {e}")
        
        return str(Path(output_path).absolute())
        
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode('utf8') if e.stderr else str(e)
        print(f"FFmpeg Error: {error_msg}")
        raise ValueError(f"Video Generation Failed: {error_msg}")
    except Exception as e:
        print(f"Video Error: {e}")
        raise ValueError(f"Video Generation Failed: {e}")


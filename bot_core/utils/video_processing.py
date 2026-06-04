import os
import subprocess
import asyncio
import traceback
from typing import Optional, Dict, Any
from .image_processing import render_image

# Cache FFmpeg status
FFMPEG_CACHE = None

async def is_ffmpeg_installed() -> bool:
    global FFMPEG_CACHE
    if FFMPEG_CACHE is not None:
        return FFMPEG_CACHE

    paths = ["../bin/ffmpeg", "/usr/bin/ffmpeg", "ffmpeg"]
    for path in paths:
        if os.path.exists(path):
            FFMPEG_CACHE = True
            return True

    try:
        process = await asyncio.create_subprocess_exec(
            "which", "ffmpeg",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await process.communicate()
        FFMPEG_CACHE = (process.returncode == 0)
    except Exception:
        FFMPEG_CACHE = False

    return FFMPEG_CACHE

async def process_video_to_webm(video_bytes: bytes, text_overlay_data: Dict[str, Any]) -> Optional[bytes]:
    ffmpeg_path = "ffmpeg"
    if os.path.exists("../bin/ffmpeg"):
        ffmpeg_path = "../bin/ffmpeg"

    temp_dir = "/tmp"
    input_path = os.path.join(temp_dir, "input.mp4")
    overlay_path = os.path.join(temp_dir, "overlay.png")
    output_path = os.path.join(temp_dir, "output.webm")

    try:
        with open(input_path, "wb") as f:
            f.write(video_bytes)

        overlay_bytes = render_image(
            text=text_overlay_data["text"],
            v_pos=text_overlay_data["v_pos"],
            h_pos=text_overlay_data["h_pos"],
            font_key=text_overlay_data["font_key"],
            color_hex=text_overlay_data["color_hex"],
            size_key=text_overlay_data["size_key"],
            bg_mode="transparent"
        )
        with open(overlay_path, "wb") as f:
            f.write(overlay_bytes)

        ffmpeg_cmd = [
            ffmpeg_path,
            '-i', input_path,
            '-i', overlay_path,
            '-filter_complex', "[0:v]scale='if(gt(iw,ih),512,-1)':'if(gt(ih,iw),512,-1)',pad=512:512:(512-iw)/2:(512-ih)/2:color=black@0[bg];[bg][1:v]overlay=0:0",
            '-t', '3',
            '-an',
            '-c:v', 'libvpx-vp9',
            '-b:v', '1M',
            '-crf', '30',
            '-fs', '250k',
            '-y',
            output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f"FFmpeg error: {stderr.decode()}")
            return None

        if os.path.exists(output_path):
            with open(output_path, "rb") as f:
                return f.read()
        return None

    except Exception as e:
        print(f"Video processing error: {e}")
        traceback.print_exc()
        return None
    finally:
        for path in [input_path, overlay_path, output_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

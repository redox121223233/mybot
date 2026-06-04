import os
import subprocess
import asyncio
import traceback
import logging
from typing import Optional, Dict, Any
from .image_processing import render_image

logger = logging.getLogger(__name__)

# Cache FFmpeg path
FFMPEG_PATH_CACHE = None

async def get_ffmpeg_path() -> Optional[str]:
    global FFMPEG_PATH_CACHE
    if FFMPEG_PATH_CACHE is not None:
        return FFMPEG_PATH_CACHE

    # Check project bin directory (Vercel build artifact)
    # The current file is in bot_core/utils/, so ../../bin/ffmpeg from here
    local_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "bin", "ffmpeg"))

    # Also check parent directory if called from api/ (Vercel root)
    root_bin = os.path.abspath(os.path.join(os.getcwd(), "bin", "ffmpeg"))

    potential_paths = [local_bin, root_bin, "/usr/bin/ffmpeg", "ffmpeg"]

    for path in potential_paths:
        if os.path.exists(path):
            logger.info(f"FFmpeg found at: {path}")
            FFMPEG_PATH_CACHE = path
            return path

    try:
        process = await asyncio.create_subprocess_exec(
            "which", "ffmpeg",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        if process.returncode == 0:
            path = stdout.decode().strip()
            logger.info(f"FFmpeg found via 'which': {path}")
            FFMPEG_PATH_CACHE = path
            return path
    except Exception:
        pass

    logger.warning("FFmpeg NOT found in any known locations.")
    return None

async def is_ffmpeg_installed() -> bool:
    return await get_ffmpeg_path() is not None

async def process_video_to_webm(video_bytes: bytes, text_overlay_data: Dict[str, Any]) -> Optional[bytes]:
    ffmpeg_path = await get_ffmpeg_path()
    if not ffmpeg_path:
        logger.error("Cannot process video: FFmpeg not found.")
        return None

    temp_dir = "/tmp"
    input_path = os.path.join(temp_dir, f"input_{os.getpid()}.mp4")
    overlay_path = os.path.join(temp_dir, f"overlay_{os.getpid()}.png")
    output_path = os.path.join(temp_dir, f"output_{os.getpid()}.webm")

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

        logger.info(f"Running FFmpeg: {' '.join(ffmpeg_cmd)}")
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            return None

        if os.path.exists(output_path):
            with open(output_path, "rb") as f:
                return f.read()
        return None

    except Exception as e:
        logger.error(f"Video processing error: {e}")
        logger.error(traceback.format_exc())
        return None
    finally:
        for path in [input_path, overlay_path, output_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

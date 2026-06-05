import os
import subprocess
import asyncio
import traceback
import logging
import sys
from typing import Optional, Dict, Any
from .image_processing import render_image

logger = logging.getLogger(__name__)

# Cache FFmpeg path
FFMPEG_PATH_CACHE = None

async def get_ffmpeg_path() -> Optional[str]:
    global FFMPEG_PATH_CACHE
    if FFMPEG_PATH_CACHE is not None:
        return FFMPEG_PATH_CACHE

    # 1. Direct path in Vercel root
    # Vercel places bin/ in the project root
    root_bin = os.path.join(os.getcwd(), "bin", "ffmpeg")

    # 2. Path relative to this file
    # bot_core/utils/video_processing.py -> ../../bin/ffmpeg
    this_dir = os.path.dirname(os.path.abspath(__file__))
    rel_bin = os.path.abspath(os.path.join(this_dir, "..", "..", "bin", "ffmpeg"))

    potential_paths = [root_bin, rel_bin, "/var/task/bin/ffmpeg", "/usr/bin/ffmpeg", "ffmpeg"]

    logger.info(f"Checking FFmpeg paths: {potential_paths}")

    for path in potential_paths:
        try:
            if path == "ffmpeg":
                process = await asyncio.create_subprocess_exec(
                    "which", "ffmpeg",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                if process.returncode == 0:
                    found = stdout.decode().strip()
                    logger.info(f"FFmpeg found in PATH: {found}")
                    FFMPEG_PATH_CACHE = found
                    return found
            elif os.path.exists(path):
                # Force executable permission in case build script didn't stick
                if not os.access(path, os.X_OK):
                    logger.info(f"Setting chmod +x on {path}")
                    os.chmod(path, 0o755)
                logger.info(f"FFmpeg found at: {path}")
                FFMPEG_PATH_CACHE = path
                return path
        except Exception as e:
            logger.error(f"Error checking {path}: {e}")

    # Last resort: search
    try:
        logger.info("Searching for ffmpeg binary...")
        find_proc = await asyncio.create_subprocess_exec(
            "find", ".", "-name", "ffmpeg", "-type", "f",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, _ = await find_proc.communicate()
        if find_proc.returncode == 0:
            found_paths = stdout.decode().splitlines()
            if found_paths:
                found = os.path.abspath(found_paths[0])
                logger.info(f"FFmpeg found via find: {found}")
                os.chmod(found, 0o755)
                FFMPEG_PATH_CACHE = found
                return found
    except Exception:
        pass

    logger.error("FFmpeg NOT FOUND")
    return None

async def is_ffmpeg_installed() -> bool:
    return await get_ffmpeg_path() is not None

async def process_video_to_webm(video_bytes: bytes, text_overlay_data: Optional[Dict[str, Any]]) -> Optional[bytes]:
    ffmpeg_path = await get_ffmpeg_path()
    if not ffmpeg_path:
        return None

    temp_dir = "/tmp"
    pid = os.getpid()
    input_path = os.path.join(temp_dir, f"input_{pid}.mp4")
    overlay_path = os.path.join(temp_dir, f"overlay_{pid}.png")
    output_path = os.path.join(temp_dir, f"output_{pid}.webm")

    try:
        with open(input_path, "wb") as f:
            f.write(video_bytes)

        if text_overlay_data and text_overlay_data.get("text"):
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

            filter_str = "[0:v]scale='if(gt(iw,ih),512,-1)':'if(gt(ih,iw),512,-1)',pad=512:512:(512-iw)/2:(512-ih)/2:color=black@0[bg];[bg][1:v]overlay=0:0"
            ffmpeg_cmd = [
                ffmpeg_path, '-i', input_path, '-i', overlay_path,
                '-filter_complex', filter_str,
                '-t', '3', '-an', '-c:v', 'libvpx-vp9', '-b:v', '512k', '-crf', '35', '-fs', '250k', '-y', output_path
            ]
        else:
            filter_str = "scale='if(gt(iw,ih),512,-1)':'if(gt(ih,iw),512,-1)',pad=512:512:(512-iw)/2:(512-ih)/2:color=black@0"
            ffmpeg_cmd = [
                ffmpeg_path, '-i', input_path,
                '-vf', filter_str,
                '-t', '3', '-an', '-c:v', 'libvpx-vp9', '-b:v', '512k', '-crf', '35', '-fs', '250k', '-y', output_path
            ]

        logger.info(f"Running FFmpeg: {' '.join(ffmpeg_cmd)}")
        process = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg return code: {process.returncode}")
            logger.error(f"FFmpeg stderr: {stderr.decode()}")
            return None

        if os.path.exists(output_path):
            with open(output_path, "rb") as f:
                return f.read()
        return None

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return None
    finally:
        for path in [input_path, overlay_path, output_path]:
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass

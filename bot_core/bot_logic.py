import logging
import os
import asyncio
from typing import Optional, Dict, Any
from .utils.video_processing import process_video_to_webm, get_ffmpeg_path

logger = logging.getLogger(__name__)

async def run_ffmpeg(args: list) -> bool:
    """Utility to run raw ffmpeg commands safely."""
    ffmpeg_path = await get_ffmpeg_path()
    if not ffmpeg_path:
        logger.error("FFmpeg path not found.")
        return False
    
    cmd = [ffmpeg_path] + args
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return True
        else:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            return False
    except Exception as e:
        logger.error(f"Error running FFmpeg: {e}")
        return False

async def convert_video_to_sticker(video_bytes: bytes, text_overlay: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
    """Converts Video bytes to Telegram-compatible WEBM sticker bytes."""
    return await process_video_to_webm(video_bytes, text_overlay)

async def convert_gif_to_sticker(gif_bytes: bytes, text_overlay: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
    """Converts GIF bytes to Telegram-compatible WEBM sticker bytes."""
    return await process_video_to_webm(gif_bytes, text_overlay)

import logging
import os
import asyncio
from typing import Optional
from .utils.video_processing import get_ffmpeg_path

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

async def convert_video_to_sticker(input_path: str, output_path: str) -> bool:
    """Converts MP4/Video to Telegram-compatible WEBM sticker using FFmpeg."""
    # Telegram WEBM requirements: VP9, no audio, max 3s, max 512px side
    filter_str = "scale='if(gt(iw,ih),512,-1)':'if(gt(ih,iw),512,-1)',pad=512:512:(512-iw)/2:(512-ih)/2:color=black@0"
    args = [
        '-i', input_path,
        '-vf', filter_str,
        '-t', '3',
        '-an',
        '-c:v', 'libvpx-vp9',
        '-b:v', '512k',
        '-crf', '35',
        '-fs', '250k',
        '-y',
        output_path
    ]
    return await run_ffmpeg(args)

async def convert_gif_to_sticker(input_path: str, output_path: str) -> bool:
    """Converts GIF to Telegram-compatible WEBM sticker."""
    # The command is the same for GIFs as FFmpeg handles them as video inputs
    return await convert_video_to_sticker(input_path, output_path)

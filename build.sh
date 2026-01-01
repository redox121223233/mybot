#!/bin/bash

# Dependencies like curl and tar are pre-installed in the Vercel build environment.

# 2. Define FFmpeg version and URL
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
FFMPEG_DIR="ffmpeg-*-amd64-static" # Wildcard to match version

# 3. Download and extract FFmpeg to /tmp
curl -L $FFMPEG_URL | tar -Jx -C /tmp

# 4. Move the ffmpeg binary to the api directory
# This makes it available in the same directory as the serverless function
mv /tmp/$FFMPEG_DIR/ffmpeg api/

# 5. Make it executable
chmod +x api/ffmpeg

echo "FFmpeg binary has been placed in the api/ directory."

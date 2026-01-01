#!/bin/bash

# Dependencies like curl and tar are pre-installed in the Vercel build environment.

# 2. Define FFmpeg version and URL
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
FFMPEG_DIR="ffmpeg-*-amd64-static" # Wildcard to match version

# 3. Download and extract FFmpeg to /tmp
curl -L $FFMPEG_URL | tar -Jx -C /tmp

# 4. Create a bin directory and move the ffmpeg binary there
mkdir -p bin/
mv /tmp/$FFMPEG_DIR/ffmpeg bin/

# 5. Make it executable
chmod +x bin/ffmpeg

echo "FFmpeg binary has been placed in the bin/ directory."

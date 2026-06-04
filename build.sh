#!/bin/bash

# Define FFmpeg version and URL
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"

# Create a bin directory in the root
mkdir -p bin/

# Download and extract FFmpeg
echo "Downloading FFmpeg..."
curl -L $FFMPEG_URL | tar -Jx -C /tmp

# Find the extracted directory (name changes with version)
EXTRACTED_DIR=$(find /tmp -name "ffmpeg-*-amd64-static" -type d | head -n 1)

if [ -n "$EXTRACTED_DIR" ]; then
    echo "Found extracted FFmpeg in $EXTRACTED_DIR"
    cp "$EXTRACTED_DIR/ffmpeg" bin/
    chmod +x bin/ffmpeg
    echo "FFmpeg binary has been placed in the bin/ directory."
else
    echo "Failed to find extracted FFmpeg directory."
    exit 1
fi

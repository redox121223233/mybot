#!/bin/bash

# Define FFmpeg version and URL
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"

# Create a bin directory in the root
mkdir -p bin/

# Download and extract FFmpeg
echo "Downloading FFmpeg from $FFMPEG_URL..."
curl -L $FFMPEG_URL | tar -Jx -C /tmp

# Find the extracted directory
EXTRACTED_DIR=$(find /tmp -name "ffmpeg-*-amd64-static" -type d | head -n 1)

if [ -n "$EXTRACTED_DIR" ]; then
    echo "Found extracted FFmpeg in $EXTRACTED_DIR"
    # Copy both ffmpeg and ffprobe
    cp "$EXTRACTED_DIR/ffmpeg" bin/
    cp "$EXTRACTED_DIR/ffprobe" bin/
    chmod +x bin/ffmpeg bin/ffprobe
    echo "FFmpeg binaries placed in bin/ directory."
    ls -l bin/
else
    echo "ERROR: Failed to find extracted FFmpeg directory."
    exit 1
fi

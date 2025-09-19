# --- Base image ---
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (برای ffmpeg یا pillow اگر نیاز بود)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (Cloud Run/Railway/Heroku معمولاً 8080 استفاده می‌کنن)
EXPOSE 8080

# Default command to run your bot
# از waitress استفاده می‌کنیم چون تو کدت هست
CMD ["python", "bot.py"]

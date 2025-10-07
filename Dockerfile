FROM python:3.11-slim

# نصب FFmpeg و ابزارهای سیستمی
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-noto \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# تنظیم دایرکتری کاری
WORKDIR /app

# کپی فایل‌های requirements
COPY requirements.txt .

# نصب وابستگی‌های Python
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد ربات
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]

FROM python:3.11-slim

# نصب FFmpeg برای پردازش ویدیو
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# تنظیم دایرکتوری کار
WORKDIR /app

# کپی پکیج‌ها و نصب
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی ربات
COPY app.py .

# اجرای ربات
CMD ["python", "app.py"]
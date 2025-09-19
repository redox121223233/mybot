# استفاده از Python
FROM python:3.11-slim

# مسیر کاری داخل کانتینر
WORKDIR /app

# کپی کردن فایل‌ها
COPY . .

# نصب وابستگی‌ها
RUN pip install --no-cache-dir -r requirements.txt

# اجرای ربات
CMD ["python", "bot.py"]

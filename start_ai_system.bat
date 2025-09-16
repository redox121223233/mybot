@echo off
chcp 65001 >nul
echo 🚀 راه‌اندازی سیستم هوش مصنوعی
echo ================================

echo 📍 بررسی Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python نصب نشده است!
    echo 💡 لطفاً Python را از python.org دانلود و نصب کنید
    pause
    exit /b 1
)
echo ✅ Python موجود است

echo.
echo 🔍 بررسی فایل‌های مورد نیاز...
if not exist "ai_control_server.py" (
    echo ❌ فایل ai_control_server.py موجود نیست!
    pause
    exit /b 1
)
if not exist "ai_integration.py" (
    echo ❌ فایل ai_integration.py موجود نیست!
    pause
    exit /b 1
)
echo ✅ تمام فایل‌ها موجود است

echo.
echo 📦 نصب وابستگی‌ها...
pip install flask requests waitress >nul 2>&1
if errorlevel 1 (
    echo ⚠️ خطا در نصب پکیج‌ها، ادامه می‌دهیم...
) else (
    echo ✅ وابستگی‌ها نصب شدند
)

echo.
echo 🔧 تنظیم متغیرهای محیطی...
set AI_CONTROL_URL=http://localhost:5000
set AI_CONTROL_SECRET=ai_secret_2025
set AI_CONTROL_PORT=5000
echo ✅ متغیرها تنظیم شدند

echo.
echo 🚀 راه‌اندازی سرور کنترل...
echo ⏳ لطفاً صبر کنید...

start /B python ai_control_server.py

echo 🔄 صبر برای راه‌اندازی سرور...
timeout /t 5 /nobreak >nul

echo.
echo 🧪 تست اتصال...
python -c "import requests; r=requests.get('http://localhost:5000/health', timeout=5); print('✅ سرور آماده است!' if r.status_code==200 else '❌ خطا در اتصال')" 2>nul
if errorlevel 1 (
    echo ❌ خطا در تست اتصال
    echo 💡 ممکن است سرور هنوز آماده نباشد
)

echo.
echo ================================
echo ✅ سیستم هوش مصنوعی راه‌اندازی شد!
echo.
echo 💡 نکات مهم:
echo • پنل وب: http://localhost:5000
echo • برای توقف این پنجره را ببندید
echo • حالا می‌توانید ربات را اجرا کنید
echo.
echo 🤖 برای اجرای ربات:
echo python bot.py
echo.
echo ================================

echo ⏳ سرور در حال اجرا... (این پنجره را نبندید)
echo 🛑 برای توقف Ctrl+C فشار دهید

:loop
timeout /t 30 /nobreak >nul
python -c "import requests; requests.get('http://localhost:5000/health', timeout=2)" >nul 2>&1
if errorlevel 1 (
    echo ⚠️ سرور قطع شده، تلاش برای راه‌اندازی مجدد...
    start /B python ai_control_server.py
    timeout /t 5 /nobreak >nul
)
goto loop
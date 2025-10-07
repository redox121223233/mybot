#!/bin/bash

# اسکریپت دانلود خودکار فونت‌های فارسی

echo "📥 در حال دانلود فونت‌های فارسی..."

# ساخت پوشه fonts
mkdir -p fonts
cd fonts

# پاک‌سازی فایل‌های قدیمی
rm -f *.zip 2>/dev/null

echo ""
echo "⬇️  دانلود Vazirmatn..."
wget -q --show-progress https://github.com/rastikerdar/vazirmatn/releases/download/v33.003/vazirmatn-v33.003.zip
if [ -f vazirmatn-v33.003.zip ]; then
    unzip -q -o vazirmatn-v33.003.zip "Vazirmatn-Regular.ttf" "Vazirmatn-Medium.ttf" 2>/dev/null
    rm vazirmatn-v33.003.zip
    echo "✅ Vazirmatn دانلود شد"
else
    echo "❌ خطا در دانلود Vazirmatn"
fi

echo ""
echo "⬇️  دانلود Sahel..."
wget -q --show-progress https://github.com/rastikerdar/sahel-font/releases/download/v3.4.0/sahel-font-v3.4.0.zip
if [ -f sahel-font-v3.4.0.zip ]; then
    unzip -q -o sahel-font-v3.4.0.zip "Sahel.ttf" "Sahel-Bold.ttf" 2>/dev/null
    rm sahel-font-v3.4.0.zip
    echo "✅ Sahel دانلود شد"
else
    echo "❌ خطا در دانلود Sahel"
fi

echo ""
echo "⬇️  دانلود IRANSans..."
wget -q --show-progress https://github.com/rastikerdar/iran-sans/releases/download/v5.0/iran-sans-v5.0.zip
if [ -f iran-sans-v5.0.zip ]; then
    unzip -q -o iran-sans-v5.0.zip "IRANSans.ttf" "IRANSansX-Regular.ttf" 2>/dev/null
    rm iran-sans-v5.0.zip
    echo "✅ IRANSans دانلود شد"
else
    echo "❌ خطا در دانلود IRANSans"
fi

echo ""
echo "⚠️  توجه: Noto Naskh Arabic باید دستی دانلود شود:"
echo "🔗 https://fonts.google.com/noto/specimen/Noto+Naskh+Arabic"
echo ""
echo "فایل‌های مورد نیاز:"
echo "  - NotoNaskhArabic-Regular.ttf"
echo "  - NotoNaskhArabic-Medium.ttf"
echo ""

# بازگشت به پوشه اصلی
cd ..

# نمایش فونت‌های دانلود شده
echo "📦 فونت‌های موجود:"
ls -lh fonts/*.ttf 2>/dev/null || echo "  هیچ فونتی یافت نشد"
echo ""
echo "✅ دانلود کامل شد!"

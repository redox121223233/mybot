import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont

# توکن از متغیر محیطی (روی Render تنظیم می‌کنیم)
TOKEN = os.getenv("8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! 👋 متن بفرست تا برات استیکر بسازم!")

async def text_to_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # ساخت تصویر از متن
    img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    w, h = draw.textsize(text, font=font)
    draw.text(((512-w)/2, (512-h)/2), text, font=font, fill="black")

    # ذخیره فایل
    img.save("sticker.png")

    # ارسال به کاربر
    await update.message.reply_sticker(sticker=open("sticker.png", "rb"))

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_to_sticker))

    app.run_polling()

if __name__ == "__main__":
    main()

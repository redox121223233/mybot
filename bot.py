def get_font(size):
    """بارگذاری فونت با fallback"""
    font_paths = [
        "Vazir.ttf",
        "NotoSans-Regular.ttf",
        "arial.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Arial.ttf",
        "/Windows/Fonts/arial.ttf"
    ]
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue
    return ImageFont.load_default()

def make_text_sticker(text, path, background_file_id=None):
    try:
        img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))

        # 📌 بکگراند
        if background_file_id:
            try:
                file_info = requests.get(API + f"getFile?file_id={background_file_id}").json()
                if file_info.get("ok"):
                    file_path = file_info["result"]["file_path"]
                    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                    resp = requests.get(file_url)
                    if resp.status_code == 200:
                        bg = Image.open(BytesIO(resp.content)).convert("RGBA")
                        bg = bg.resize((512, 512))
                        img.paste(bg, (0, 0))
            except Exception as e:
                logger.error(f"Error loading background: {e}")

        draw = ImageDraw.Draw(img)

        # 📌 شروع با سایز خیلی بزرگ
        font_size = 800
        font = get_font(font_size)
        w, h = draw.textbbox((0, 0), text, font=font)[2:]
        # کوچک کردن تا جا بشه
        while (w > 480 or h > 480) and font_size > 100:
            font_size -= 20
            font = get_font(font_size)
            w, h = draw.textbbox((0, 0), text, font=font)[2:]
        
        x = (512 - w) / 2
        y = (512 - h) / 2

        # 📌 ضخامت outline متناسب با سایز فونت
        outline_thickness = max(6, font_size // 12)

        # حاشیه سفید
        for dx in range(-outline_thickness, outline_thickness+1, 2):
            for dy in range(-outline_thickness, outline_thickness+1, 2):
                draw.text((x+dx, y+dy), text, font=font, fill="white")

        # متن اصلی
        draw.text((x, y), text, font=font, fill="black")

        img.save(path, "PNG")
        logger.info(f"✅ Sticker saved with font_size={font_size}, outline={outline_thickness}")
        return True
    except Exception as e:
        logger.error(f"make_text_sticker error: {e}")
        return False

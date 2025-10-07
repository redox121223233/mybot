import arabic_reshaper
from bidi.algorithm import get_display

def prepare_farsi_text(text: str) -> str:
    """
    متن فارسی را به صورت درست (راست‌به‌چپ و ترتیب صحیح کلمات و خطوط) آماده می‌کند.
    """
    if not text:
        return ""
    lines = text.split("\n")
    reshaped_lines = []
    for line in lines:
        reshaped = arabic_reshaper.reshape(line)
        displayed = get_display(reshaped)
        reshaped_lines.append(displayed)
    return "\n".join(reshaped_lines)
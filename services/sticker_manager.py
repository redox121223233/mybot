import os
from PIL import Image, ImageDraw, ImageFont

def process_sticker(user_id, photo_path, text, settings):
    """
    Process the photo to add text and create the sticker with user-defined settings.
    """
    try:
        # Get settings for text
        color = settings.get("color", "white")  # Default color is white
        font_size = settings.get("size", 32)  # Default font size is 32
        position = settings.get("position", "center")  # Default position is center
        font_path = os.path.join("fonts", settings.get("font", "Arial.ttf"))  # Default font is Arial.ttf

        # Open the image
        image = Image.open(photo_path).convert("RGBA")
        draw = ImageDraw.Draw(image)

        # Load the font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()

        # Calculate text size and position
        text_width, text_height = draw.textsize(text, font=font)

        if position == "top":
            x = (image.width - text_width) // 2
            y = 20  # Top margin
        elif position == "bottom":
            x = (image.width - text_width) // 2
            y = image.height - text_height - 20  # Bottom margin
        else:
            x = (image.width - text_width) // 2
            y = (image.height - text_height) // 2  # Center position

        # Draw the text
        draw.text((x, y), text, font=font, fill=color)

        # Save the final image
        final_path = f"final_{user_id}_sticker.png"
        image.save(final_path)
        return final_path

    except Exception as e:
        print(f"❌ Error in sticker creation: {e}")
        return None

def create_sticker(user_id, photo_path, text, settings, api):
    """
    Create a sticker set for the user with the provided photo and text.
    """
    final_image_path = process_sticker(user_id, photo_path, text, settings)
    if final_image_path:
        # Create the sticker set name
        sticker_set_name = f"pack_{user_id}_by_{api.username}"

        # Check if the sticker set exists
        if not api.sticker_set_exists(sticker_set_name):
            # Create new sticker set
            api.create_new_sticker_set(user_id, sticker_set_name, f"استیکرهای {user_id}", final_image_path, emoji="😀")
            return sticker_set_name
        else:
            # Add the sticker to the existing set
            api.add_sticker_to_set(user_id, sticker_set_name, final_image_path, emoji="😀")
            return sticker_set_name
    else:
        return None

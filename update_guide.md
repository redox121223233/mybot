# 🚀 How to Apply the Sticker API Fix

## The Problem
The error `ExtBot.create_new_sticker_set() got an unexpected keyword argument 'sticker'` occurs because you're running an old version of the code locally.

## The Solution
The fix has been implemented in the `fix/sticker-transparency-error` branch and is ready in PR #25.

## Steps to Apply the Fix Locally

### Option 1: Pull the Latest Changes
```bash
cd your-bot-directory
git checkout fix/sticker-transparency-error
git pull origin fix/sticker-transparency-error
```

### Option 2: Merge the Fix into Your Local Branch
```bash
cd your-bot-directory
git checkout fix/sticker-transparency-error
git pull origin fix/sticker-transparency-error
```

### Option 3: Manual Fix (if you prefer)
Edit your `api/index.py` file:

1. **Add InputSticker import** (line 18):
```python
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, InputSticker
```

2. **Replace the add_sticker_to_set call** (around line 371):
```python
# OLD CODE:
await bot.add_sticker_to_set(user_id=user_id, name=full_pack_name, sticker=sticker_bytes, emojis=['😊'])

# NEW CODE:
input_sticker = InputSticker(
    sticker=sticker_bytes,
    emoji_list=['😊']
)
await bot.add_sticker_to_set(user_id=user_id, name=full_pack_name, sticker=input_sticker)
```

3. **Replace the create_new_sticker_set call** (around line 402):
```python
# OLD CODE:
await bot.create_new_sticker_set(
    user_id=user_id, 
    name=full_pack_name, 
    title=pack_name, 
    sticker=sticker_bytes, 
    emojis=['😊']
)

# NEW CODE:
input_sticker = InputSticker(
    sticker=sticker_bytes,
    emoji_list=['😊']
)
await bot.create_new_sticker_set(
    user_id=user_id, 
    name=full_pack_name, 
    title=pack_name, 
    sticker=input_sticker
)
```

## Restart Your Bot
After applying the fix, restart your bot:
```bash
python api/index.py
# or however you normally start your bot
```

## Verification
The error should no longer occur. Your bot should now be able to:
- ✅ Create new sticker packs
- ✅ Add stickers to existing packs
- ✅ Handle both simple and advanced sticker types

## PR Status
The fix is already submitted in PR #25: https://github.com/redox121223233/mybot/pull/25

The PR includes both the transparency mask fix AND the InputSticker API fix.
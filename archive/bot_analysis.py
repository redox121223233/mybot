import os
import re

def analyze_bot_file():
    """Analyze bot.py file structure and potential issues"""
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("=== BOT.PY ANALYSIS ===")
    print(f"Total lines: {len(content.splitlines())}")
    
    # Check for duplicate functions
    function_pattern = r'async def (\w+)\('
    functions = re.findall(function_pattern, content)
    print(f"\nFunctions found: {functions}")
    
    # Check for duplicate function names
    duplicate_functions = []
    seen_functions = set()
    for func in functions:
        if func in seen_functions:
            duplicate_functions.append(func)
        seen_functions.add(func)
    
    if duplicate_functions:
        print(f"⚠️  DUPLICATE FUNCTIONS FOUND: {duplicate_functions}")
    else:
        print("✅ No duplicate functions found")
    
    # Check for PNG vs WEBP handling
    png_mentions = content.lower().count('png')
    webp_mentions = content.lower().count('webp')
    print(f"\nPNG mentions: {png_mentions}")
    print(f"WEBP mentions: {webp_mentions}")
    
    if png_mentions > webp_mentions:
        print("⚠️  More PNG references than WEBP - potential format issue")
    
    # Check for sticker pack creation
    sticker_pack_mentions = content.lower().count('sticker_pack')
    add_sticker_mentions = content.lower().count('add_sticker')
    print(f"\nSticker pack mentions: {sticker_pack_mentions}")
    print(f"Add sticker mentions: {add_sticker_mentions}")
    
    # Look for specific issues
    issues_found = []
    
    if 'png' in content.lower() and 'send_sticker' in content.lower():
        issues_found.append("Sending PNG stickers instead of WEBP")
    
    if 'create_new_sticker_set' in content.lower():
        print("✅ Found sticker set creation function")
    
    if 'add_sticker_to_set' in content.lower():
        print("✅ Found add sticker to set function")
    else:
        issues_found.append("Missing add_sticker_to_set functionality")
    
    # Check for file handling issues
    if 'open(' in content and 'with open(' in content:
        print("✅ Proper file handling with 'with' statement")
    elif 'open(' in content:
        issues_found.append("Potential file handling issues - not using 'with' statement")
    
    return issues_found

if __name__ == "__main__":
    issues = analyze_bot_file()
    
    print("\n=== ISSUES FOUND ===")
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
    else:
        print("✅ No obvious issues detected in analysis")
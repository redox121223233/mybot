
import os
BOT_TOKEN = os.getenv("BOT_TOKEN", "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0")
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATA_DIR = BASE_DIR
os.makedirs(DATA_DIR, exist_ok=True)

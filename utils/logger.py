
import re
import time
import json
import requests
from flask import Flask, request
from waitress import serve

# تنظیم مسیر پایه پروژه
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sticker_bot")


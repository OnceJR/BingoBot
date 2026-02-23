import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

DB_PATH = os.getenv("DB_PATH", "bingo.sqlite3")
ASSETS_DIR = os.getenv("ASSETS_DIR", "assets")
IMAGES_DIR = os.getenv("IMAGES_DIR", "images")

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

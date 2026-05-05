import os

TOKEN = os.getenv("BOT_TOKEN", "Bot Token does not exist")
PROFILE = os.getenv("PROFILE")

WALLAPOP_API_URL = "https://api.wallapop.com/api/v3/search"

LOG_LEVEL = "DEBUG" if PROFILE else "INFO"
LOG_PATH = "wallbot.log" if PROFILE else "/logs/wallbot.log"

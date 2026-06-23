import os

EMBY_URL = os.getenv("EMBY_URL", "http://localhost:8096")
EMBY_API_KEY = os.getenv("EMBY_API_KEY", "")
HEADERS = {"X-Emby-Token": EMBY_API_KEY}

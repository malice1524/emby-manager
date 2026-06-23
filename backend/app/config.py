import os

EMBY_URL = os.getenv("EMBY_URL", "http://localhost:8096")
EMBY_API_KEY = os.getenv("EMBY_API_KEY", "")
HEADERS = {"X-Emby-Token": EMBY_API_KEY}

# Admin credentials for user-level operations (delete, etc.)
EMBY_ADMIN_USER = os.getenv("EMBY_ADMIN_USER", "Malice")
EMBY_ADMIN_PW = os.getenv("EMBY_ADMIN_PW", "")

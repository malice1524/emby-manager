import os
import json
import httpx

EMBY_URL = os.getenv("EMBY_URL", "http://localhost:8096")
EMBY_API_KEY = os.getenv("EMBY_API_KEY", "")
HEADERS = {"X-Emby-Token": EMBY_API_KEY}

# Admin credentials for user-level operations (delete, etc.)
EMBY_ADMIN_USER = os.getenv("EMBY_ADMIN_USER", "Malice")
EMBY_ADMIN_PW = os.getenv("EMBY_ADMIN_PW", "")

MONITOR_DATA_DIR = os.getenv("MONITOR_DATA_DIR", "/data")
CONFIG_PATH = os.path.join(MONITOR_DATA_DIR, "config.json")
MONITORED_SERIES_PATH = os.path.join(MONITOR_DATA_DIR, "monitored_series.json")

def load_tg_config():
    """加载 TG 配置，优先读 JSON 文件，没有则用环境变量兜底"""
    config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "tmdb_api_key": config.get("tmdb_api_key") or os.getenv("TMDB_API_KEY", ""),
        "tg_bot_token": config.get("tg_bot_token") or os.getenv("TG_BOT_TOKEN", ""),
        "tg_chat_id": config.get("tg_chat_id") or os.getenv("TG_CHAT_ID", ""),
        "proxy_url": config.get("proxy_url", ""),
        "update_template": config.get("update_template", ""),
        "end_template": config.get("end_template", ""),
        "check_interval_minutes": config.get("check_interval_minutes", 30),
        "check_cron": config.get("check_cron", "") or os.getenv("CHECK_CRON", "*/30 * * * *"),
    }

def get_http_client():
    """获取带代理的 httpx 客户端（如果有配置代理的话）"""
    cfg = load_tg_config()
    proxy = cfg.get("proxy_url", "")
    if proxy:
        return httpx.AsyncClient(timeout=15, proxies=proxy)
    return httpx.AsyncClient(timeout=15)

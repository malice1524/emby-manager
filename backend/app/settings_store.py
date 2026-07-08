import json
import os
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BATCH_SIZE = 10
SETTINGS_DATA_DIR = Path(os.getenv("MONITOR_DATA_DIR", "/data"))
SETTINGS_PATH = SETTINGS_DATA_DIR / "settings.json"


def _read_settings_file() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_settings_file(data: dict[str, Any]) -> None:
    SETTINGS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_PATH)


def _coerce_batch_size(value: Any) -> int:
    try:
        size = int(value)
    except (TypeError, ValueError):
        return DEFAULT_BATCH_SIZE
    return size if size >= 1 else DEFAULT_BATCH_SIZE


def _normalize_deepseek(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "api_key": str(raw.get("api_key") or "").strip(),
        "base_url": str(raw.get("base_url") or DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
        "model": str(raw.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "batch_size": _coerce_batch_size(raw.get("batch_size", DEFAULT_BATCH_SIZE)),
    }


def _saved_deepseek_settings() -> dict[str, Any]:
    data = _read_settings_file()
    return _normalize_deepseek(data.get("deepseek"))


def load_deepseek_settings() -> dict[str, Any]:
    settings = _saved_deepseek_settings()
    saved_key = settings.get("api_key", "")
    env_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    settings["api_key"] = saved_key or env_key
    settings["api_key_source"] = "saved" if saved_key else ("environment" if env_key else "none")
    return settings


def public_deepseek_settings() -> dict[str, Any]:
    settings = load_deepseek_settings()
    return {
        "base_url": settings["base_url"],
        "model": settings["model"],
        "batch_size": settings["batch_size"],
        "api_key_configured": bool(settings.get("api_key")),
        "api_key_source": settings.get("api_key_source", "none"),
    }


def save_deepseek_settings(payload: dict[str, Any]) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    data = _read_settings_file()
    existing = _normalize_deepseek(data.get("deepseek"))
    updated = existing.copy()

    if "base_url" in payload:
        updated["base_url"] = str(payload.get("base_url") or DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    if "model" in payload:
        updated["model"] = str(payload.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if "batch_size" in payload:
        updated["batch_size"] = _coerce_batch_size(payload.get("batch_size"))
    if "api_key" in payload:
        updated["api_key"] = str(payload.get("api_key") or "").strip()

    data["deepseek"] = updated
    _write_settings_file(data)
    return public_deepseek_settings()

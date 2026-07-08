import json
import re
from typing import Any

import httpx

from .settings_store import load_deepseek_settings

CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
INVALID_FILENAME_CHARS_RE = re.compile(r"[/\\:*?\"<>|]+")


def contains_chinese(text: str) -> bool:
    return bool(CHINESE_RE.search(text or ""))


def sanitize_filename_part(text: str) -> str:
    cleaned = INVALID_FILENAME_CHARS_RE.sub(" ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned


def _success(row_id: str, title: str, skipped: bool = False) -> dict[str, Any]:
    return {"id": row_id, "ok": True, "title": sanitize_filename_part(title), "error": "", "skipped": skipped}


def _failure(row_id: str, error: str, skipped: bool = False) -> dict[str, Any]:
    return {"id": row_id, "ok": False, "title": "", "error": error, "skipped": skipped}


def _extract_content(payload: dict[str, Any]) -> str:
    try:
        return str(payload["choices"][0]["message"]["content"] or "")
    except (KeyError, IndexError, TypeError):
        return ""


def _parse_translation_json(content: str) -> dict[str, str]:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    data = json.loads(text)
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("items missing")
    result: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        row_id = str(item.get("id") or "").strip()
        title = sanitize_filename_part(str(item.get("title") or ""))
        if row_id and title:
            result[row_id] = title
    return result


async def translate_titles(titles: list[dict[str, Any]], settings: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    settings = settings or load_deepseek_settings()
    rows = []
    skipped = []
    for item in titles:
        row_id = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        if not row_id:
            continue
        if contains_chinese(title):
            skipped.append(_success(row_id, title, skipped=True))
        else:
            rows.append({"id": row_id, "title": title})
    if not rows:
        return skipped

    api_key = str(settings.get("api_key") or "").strip()
    if not api_key:
        return skipped + [_failure(row["id"], "DeepSeek API Key 未配置") for row in rows]

    base_url = str(settings.get("base_url") or "https://api.deepseek.com").rstrip("/")
    model = str(settings.get("model") or "deepseek-chat")
    prompt = (
        "你是媒体库文件名翻译助手。把输入标题翻译成简短自然的中文媒体标题，"
        "不要包含文件扩展名，不要解释。可以去掉明显无意义广告词。"
        "只返回 JSON，格式为 {\"items\":[{\"id\":\"...\",\"title\":\"...\"}]}。\n"
        f"输入：{json.dumps({'items': rows}, ensure_ascii=False)}"
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
            parsed = _parse_translation_json(_extract_content(response.json()))
    except Exception as exc:
        message = "DeepSeek 响应解析失败" if isinstance(exc, (json.JSONDecodeError, ValueError)) else "DeepSeek 翻译失败"
        return skipped + [_failure(row["id"], message) for row in rows]

    output = []
    for row in rows:
        title = parsed.get(row["id"], "")
        if title:
            output.append(_success(row["id"], title))
        else:
            output.append(_failure(row["id"], "DeepSeek 响应缺少该文件翻译"))
    return skipped + output

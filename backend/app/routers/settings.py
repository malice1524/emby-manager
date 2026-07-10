from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..deepseek_client import translate_titles
from ..settings_store import (
    public_deepseek_settings,
    save_deepseek_settings,
    load_deepseek_settings,
    public_metube_settings,
    save_metube_settings,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class DeepSeekSettingsRequest(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    batch_size: int | None = None


class TestTranslationRequest(BaseModel):
    title: str


@router.get("/deepseek")
def get_deepseek_settings():
    return public_deepseek_settings()


@router.put("/deepseek")
def put_deepseek_settings(payload: dict[str, Any]):
    return save_deepseek_settings(payload)


@router.get("/metube")
def get_metube_settings():
    return public_metube_settings()


@router.put("/metube")
def put_metube_settings(payload: dict[str, Any]):
    return save_metube_settings(payload)


@router.post("/deepseek/test-translation")
async def test_deepseek_translation(payload: TestTranslationRequest):
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="测试标题不能为空")
    result = await translate_titles([{"id": "test", "title": title}], load_deepseek_settings())
    item = result[0] if result else {"ok": False, "error": "翻译失败"}
    if not item.get("ok"):
        raise HTTPException(status_code=400, detail=item.get("error") or "翻译失败")
    return {"ok": True, "title": item.get("title", ""), "skipped": item.get("skipped", False)}

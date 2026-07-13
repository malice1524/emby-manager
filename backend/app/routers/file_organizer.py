from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..deepseek_client import translate_titles
from ..file_organizer import (
    browse_directory,
    execute_metadata_copy,
    execute_video_moves,
    precheck_metadata_copy,
    precheck_video_moves,
    scan_videos,
    suggest_next_episode,
)
from ..settings_store import load_deepseek_settings


async def translate_titles_batched(rows: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        batch_size = int(settings.get("batch_size") or 10)
    except (TypeError, ValueError):
        batch_size = 10
    batch_size = max(1, min(batch_size, 50))
    output: list[dict[str, Any]] = []
    for start in range(0, len(rows), batch_size):
        output.extend(await translate_titles(rows[start:start + batch_size], settings))
    return output

router = APIRouter(prefix="/api/file-organizer", tags=["file-organizer"])


def _handle_error(exc: Exception):
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.get("/browse")
def browse(root: str = Query("cloud115"), path: str | None = None):
    try:
        return browse_directory(root, path)
    except Exception as exc:
        _handle_error(exc)


@router.post("/scan")
def scan(payload: dict[str, Any]):
    try:
        return scan_videos(
            str(payload.get("source_dir") or ""),
            bool(payload.get("recursive", False)),
            str(payload.get("sort") or "name"),
        )
    except Exception as exc:
        _handle_error(exc)


@router.post("/translate")
async def translate(payload: dict[str, Any]):
    rows = payload.get("items") or []
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="翻译项目必须是列表")
    settings = load_deepseek_settings()
    return {"items": await translate_titles_batched(rows, settings)}


@router.post("/suggest-next-episode")
def suggest_next(payload: dict[str, Any]):
    try:
        return suggest_next_episode(str(payload.get("target_dir") or ""), int(payload.get("season") or 1))
    except Exception as exc:
        _handle_error(exc)


@router.post("/precheck")
def precheck(payload: dict[str, Any]):
    try:
        return precheck_video_moves(payload)
    except Exception as exc:
        _handle_error(exc)


@router.post("/execute")
def execute(payload: dict[str, Any]):
    try:
        return execute_video_moves(payload)
    except Exception as exc:
        _handle_error(exc)


@router.post("/metadata/precheck")
def metadata_precheck(payload: dict[str, Any]):
    try:
        return precheck_metadata_copy(payload)
    except Exception as exc:
        _handle_error(exc)


@router.post("/metadata/execute")
def metadata_execute(payload: dict[str, Any]):
    try:
        return execute_metadata_copy(payload)
    except Exception as exc:
        _handle_error(exc)

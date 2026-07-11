from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

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
from . import nfo as nfo_router

router = APIRouter(prefix="/api/media-organizer", tags=["media-organizer"])


def _handle_error(exc: Exception):
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.get("/browse")
def browse(root: str = Query("cloud115"), path: str | None = None):
    try:
        if root == "strm":
            current = nfo_router._safe_browse_dir(path)
            dirs = []
            for child in current.iterdir():
                if not child.is_dir():
                    continue
                dirs.append({
                    "name": child.name,
                    "path": str(child),
                    "is_actor_dir": (child / "Season 1").is_dir(),
                    "has_tvshow": (child / "tvshow.nfo").exists(),
                })
            dirs.sort(key=lambda item: item["name"].lower())
            parent = ""
            root_path = nfo_router._media_root()
            if current != root_path:
                parent_path = current.parent.resolve()
                try:
                    parent_path.relative_to(root_path)
                    parent = str(parent_path)
                except ValueError:
                    parent = ""
            return {"media_root": str(root_path), "path": str(current), "parent": parent, "dirs": dirs}
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
    return {"items": await translate_titles(rows, settings)}


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


@router.post("/tvshow")
async def tvshow(req: nfo_router.TvshowRequest):
    return await nfo_router.save_tvshow(req)


@router.post("/upload-artwork")
async def upload_artwork(
    actor_dir: str = Form(...),
    kind: str = Form(...),
    overwrite: bool = Form(False),
    image: UploadFile = File(...),
):
    return await nfo_router.upload_artwork(actor_dir=actor_dir, kind=kind, overwrite=overwrite, image=image)


@router.post("/upload-episode-images")
async def upload_episode_images(actor_dir: str = Form(...), images: list[UploadFile] = File(...)):
    return await nfo_router.upload_episode_images(actor_dir=actor_dir, images=images)


@router.post("/refresh-emby")
async def refresh_emby(req: nfo_router.RefreshEmbyRequest | None = None):
    return await nfo_router.refresh_emby_automation(req)


@router.post("/execute-episodes")
async def execute_episodes(req: nfo_router.ExecuteRequest):
    return await nfo_router.execute_automation(req)

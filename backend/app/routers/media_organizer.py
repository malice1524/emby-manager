import os
from pathlib import Path
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

router = APIRouter(prefix="/api/media-organizer", tags=["media-organizer"])


def _candidate_roots(root: str) -> list[Path]:
    if root == "strm":
        values = [os.getenv("NFO_MEDIA_ROOT"), os.getenv("STRM_ROOT"), "/vol1/1000/docker/strm", "/strm"]
    else:
        values = [os.getenv("CLOUD115_ROOT"), "/CloudDrive115", "/vol1/1000/docker/CloudDrive115/CloudDrive"]
    return [Path(value).expanduser().resolve() for value in values if value]


def _existing_root(root: str) -> Path:
    candidates = _candidate_roots(root)
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return candidates[0]


def _browse_dir(root: str, path: str | None = None) -> tuple[Path, Path]:
    root_path = _existing_root(root)
    current = Path(path).expanduser().resolve() if path else root_path
    try:
        current.relative_to(root_path)
    except ValueError:
        raise ValueError(f"路径必须位于允许根目录内: {root_path}")
    if not current.exists() or not current.is_dir():
        raise FileNotFoundError(f"目录不存在: {current}")
    return root_path, current


def _handle_error(exc: Exception):
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.get("/browse")
def browse(root: str = Query("cloud115"), path: str | None = None):
    try:
        root_path, current = _browse_dir(root, path)
        directories = []
        for child in current.iterdir():
            if not child.is_dir():
                continue
            item = {"name": child.name, "path": str(child)}
            if root == "strm":
                item["is_actor_dir"] = (child / "Season 1").is_dir()
                item["has_tvshow"] = (child / "tvshow.nfo").exists()
            directories.append(item)
        directories.sort(key=lambda item: item["name"].lower())
        parent = ""
        if current != root_path:
            parent_path = current.parent.resolve()
            try:
                parent_path.relative_to(root_path)
                parent = str(parent_path)
            except ValueError:
                parent = ""
        if root == "strm":
            return {
                "media_root": str(root_path),
                "root": str(root_path),
                "path": str(current),
                "parent": parent,
                "dirs": directories,
                "directories": directories,
            }
        return {"root": str(root_path), "path": str(current), "parent": parent, "directories": directories}
    except Exception as exc:
        _handle_error(exc)


@router.post("/actor-info")
def actor_info(payload: dict[str, Any]):
    try:
        _, actor_dir = _browse_dir("strm", str(payload.get("actor_dir") or ""))
        tvshow = nfo_router._read_tvshow_nfo(actor_dir)
        return {
            "actor_dir": str(actor_dir),
            "actor_name": actor_dir.name,
            "tvshow_exists": (actor_dir / "tvshow.nfo").exists(),
            "poster_exists": (actor_dir / "poster.jpg").exists(),
            "fanart_exists": (actor_dir / "fanart.jpg").exists(),
            "logo_exists": (actor_dir / "logo.png").exists(),
            "tvshow": tvshow,
        }
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

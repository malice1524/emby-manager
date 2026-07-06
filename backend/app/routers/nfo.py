import os
import re
import shutil
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/nfo", tags=["nfo"])

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
PENDING_IMAGE_RE = re.compile(r"^IMG_\d+", re.I)
STRM_RE = re.compile(r"^(?P<actor>.+)\.S(?P<season>\d+)E(?P<episode>\d+)\.(?P<title>.+)\.strm$", re.I)


class ActorDirRequest(BaseModel):
    actor_dir: str


class RefreshEmbyRequest(BaseModel):
    actor_dir: str | None = None


class ExecuteRequest(BaseModel):
    actor_dir: str
    refresh_emby: bool = True


class TvshowRequest(BaseModel):
    actor_dir: str
    title: str
    plot: str = ""
    outline: str = ""
    tmdb_id: str = ""
    dateadded: str = ""
    lockdata: bool = False
    sorttitle: str = ""
    displayorder: str = "aired"
    overwrite: bool = False


def _media_root() -> Path:
    return Path(os.getenv("NFO_MEDIA_ROOT", "/vol1/1000/docker/strm")).resolve()


def _safe_actor_dir(actor_dir: str) -> Path:
    path = Path(actor_dir).expanduser().resolve()
    root = _media_root()
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"演员目录必须位于媒体根目录内: {root}")
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=404, detail="演员目录不存在")
    return path


def _safe_browse_dir(path_value: str | None = None) -> Path:
    root = _media_root()
    path = Path(path_value).expanduser().resolve() if path_value else root
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"浏览目录必须位于媒体根目录内: {root}")
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在")
    return path


def _season_dir(actor_dir: Path) -> Path:
    season = actor_dir / "Season 1"
    if not season.exists() or not season.is_dir():
        raise HTTPException(status_code=404, detail="Season 1 目录不存在")
    return season


def _parse_strms(season: Path):
    items = []
    for path in season.glob("*.strm"):
        match = STRM_RE.match(path.name)
        if not match:
            continue
        items.append({
            "actor": match.group("actor"),
            "season": int(match.group("season")),
            "episode": int(match.group("episode")),
            "episode_code": f"S{int(match.group('season')):02d}E{match.group('episode')}",
            "title": match.group("title"),
            "filename": path.name,
            "path": path,
        })
    items.sort(key=lambda x: (x["season"], x["episode"], x["filename"]))
    return items


def _pending_images(season: Path):
    images = []
    for path in season.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and PENDING_IMAGE_RE.match(path.name):
            images.append(path)
    images.sort(key=lambda p: (p.stat().st_mtime, p.name))
    return images


def _episode_nfo(title: str, season: int, episode: int) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
        '<episodedetails>\n'
        f'  <title>{escape(title)}</title>\n'
        f'  <season>{season}</season>\n'
        f'  <episode>{episode}</episode>\n'
        '</episodedetails>\n'
    )


def _build_scan(actor_dir: Path):
    season = _season_dir(actor_dir)
    strms = _parse_strms(season)
    pending = _pending_images(season)

    episodes = []
    missing_images = []
    missing_nfo = []
    existing_images = 0
    existing_nfo = 0
    for item in strms:
        strm_path = item["path"]
        image_path = strm_path.with_suffix(".JPG")
        nfo_path = strm_path.with_suffix(".nfo")
        has_image = image_path.exists()
        has_nfo = nfo_path.exists() and nfo_path.stat().st_size > 0
        if has_image:
            existing_images += 1
        else:
            missing_images.append({k: item[k] for k in ["season", "episode", "episode_code", "title", "filename"]})
        if has_nfo:
            existing_nfo += 1
        else:
            missing_nfo.append({k: item[k] for k in ["season", "episode", "episode_code", "title", "filename"]})
        episodes.append({
            "season": item["season"],
            "episode": item["episode"],
            "episode_code": item["episode_code"],
            "title": item["title"],
            "filename": item["filename"],
            "has_image": has_image,
            "has_nfo": has_nfo,
            "image_name": image_path.name if has_image else "",
            "nfo_name": nfo_path.name if has_nfo else "",
        })

    image_plan = []
    for src, item in zip(pending, missing_images):
        target = Path(item["filename"]).with_suffix(".JPG").name
        image_plan.append({
            "source": src.name,
            "target": target,
            "episode": item["episode"],
            "title": item["title"],
        })

    return {
        "actor_dir": str(actor_dir),
        "actor_name": actor_dir.name,
        "season_dir": str(season),
        "tvshow_exists": (actor_dir / "tvshow.nfo").exists(),
        "poster_exists": (actor_dir / "poster.jpg").exists(),
        "fanart_exists": (actor_dir / "fanart.jpg").exists(),
        "logo_exists": (actor_dir / "logo.png").exists(),
        "counts": {
            "strm": len(strms),
            "images": existing_images,
            "nfo": existing_nfo,
            "pending_images": len(pending),
        },
        "episodes": episodes,
        "missing_images": missing_images,
        "missing_nfo": missing_nfo,
        "pending_images": [p.name for p in pending],
        "image_plan": image_plan,
    }


def _backup(path: Path):
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.bak.{stamp}")
        shutil.copy2(path, backup)
        return backup.name
    return ""


def _tvshow_xml(req: TvshowRequest) -> str:
    title = req.title.strip()
    sorttitle = (req.sorttitle or title).strip()
    outline = req.outline if req.outline else req.plot
    dateadded = req.dateadded or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    actor_lines = ["  <actor>", f"    <name>{escape(title)}</name>", "    <type>Actor</type>"]
    if req.tmdb_id.strip():
        actor_lines.append(f"    <tmdbid>{escape(req.tmdb_id.strip())}</tmdbid>")
    actor_lines.append("  </actor>")
    actor = "\n".join(actor_lines)
    return (
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
        '<tvshow>\n'
        f'  <plot><![CDATA[{req.plot}]]></plot>\n'
        f'  <outline><![CDATA[{outline}]]></outline>\n'
        f'  <lockdata>{str(req.lockdata).lower()}</lockdata>\n'
        f'  <dateadded>{escape(dateadded)}</dateadded>\n'
        f'  <title>{escape(title)}</title>\n'
        f'{actor}\n'
        f'  <sorttitle>{escape(sorttitle)}</sorttitle>\n'
        '  <season>-1</season>\n'
        '  <episode>-1</episode>\n'
        f'  <displayorder>{escape(req.displayorder or "aired")}</displayorder>\n'
        '</tvshow>\n'
    )


def _emby_settings() -> tuple[str, str]:
    emby_url = os.getenv("EMBY_URL", "").rstrip("/")
    emby_api_key = os.getenv("EMBY_API_KEY", "")
    if not emby_url or not emby_api_key:
        raise HTTPException(status_code=400, detail="缺少 EMBY_URL 或 EMBY_API_KEY，无法刷新 Emby")
    return emby_url, emby_api_key


def _map_to_emby_path(local_path: Path) -> str | None:
    emby_root = os.getenv("EMBY_MEDIA_ROOT", "").rstrip("/")
    if not emby_root:
        return None
    nfo_root = _media_root()
    try:
        relative = local_path.resolve().relative_to(nfo_root)
    except ValueError:
        return None
    relative_text = relative.as_posix()
    return f"{emby_root}/{relative_text}" if relative_text else emby_root


async def _refresh_emby_library() -> dict:
    emby_url, emby_api_key = _emby_settings()
    url = f"{emby_url}/Library/Refresh"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers={"X-Emby-Token": emby_api_key})
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Emby 刷新失败: HTTP {resp.status_code} {resp.text[:200]}")
    return {"ok": True, "mode": "library", "status_code": resp.status_code}


async def _refresh_emby_for_actor(actor_dir: Path) -> dict:
    emby_path = _map_to_emby_path(actor_dir)
    if not emby_path:
        return await _refresh_emby_library()

    emby_url, emby_api_key = _emby_settings()
    headers = {"X-Emby-Token": emby_api_key}
    async with httpx.AsyncClient(timeout=15) as client:
        search = await client.get(
            f"{emby_url}/Items",
            headers=headers,
            params={"Recursive": "true", "Fields": "Path", "Path": emby_path},
        )
        if search.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Emby 查询项目失败: HTTP {search.status_code} {search.text[:200]}")
        items = search.json().get("Items", [])
        if not items:
            fallback = await client.post(f"{emby_url}/Library/Refresh", headers=headers)
            if fallback.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Emby 全库兜底刷新失败: HTTP {fallback.status_code} {fallback.text[:200]}")
            return {"ok": True, "mode": "library_fallback", "path": emby_path, "status_code": fallback.status_code}

        item = items[0]
        item_id = item.get("Id")
        if not item_id:
            raise HTTPException(status_code=502, detail="Emby 查询项目返回缺少 Id")
        refresh = await client.post(
            f"{emby_url}/Items/{item_id}/Refresh",
            headers=headers,
            params={
                "Recursive": "true",
                "MetadataRefreshMode": "FullRefresh",
                "ImageRefreshMode": "FullRefresh",
                "ReplaceAllMetadata": "false",
                "ReplaceAllImages": "false",
            },
        )
        if refresh.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Emby 项目刷新失败: HTTP {refresh.status_code} {refresh.text[:200]}")
        return {
            "ok": True,
            "mode": "item",
            "item_id": item_id,
            "name": item.get("Name") or actor_dir.name,
            "path": emby_path,
            "status_code": refresh.status_code,
        }


@router.get("/automation/browse")
async def browse_automation(path: str | None = Query(default=None)):
    root = _media_root()
    current = _safe_browse_dir(path)
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
    if current != root:
        parent_path = current.parent.resolve()
        try:
            parent_path.relative_to(root)
            parent = str(parent_path)
        except ValueError:
            parent = ""
    return {
        "media_root": str(root),
        "path": str(current),
        "parent": parent,
        "dirs": dirs,
    }


@router.post("/automation/scan")
async def scan_automation(req: ActorDirRequest):
    return _build_scan(_safe_actor_dir(req.actor_dir))


@router.post("/automation/refresh-emby")
async def refresh_emby_automation(req: RefreshEmbyRequest | None = None):
    if req and req.actor_dir:
        return await _refresh_emby_for_actor(_safe_actor_dir(req.actor_dir))
    return await _refresh_emby_library()


@router.post("/automation/execute")
async def execute_automation(req: ExecuteRequest):
    actor_dir = _safe_actor_dir(req.actor_dir)
    season = _season_dir(actor_dir)
    before = _build_scan(actor_dir)
    logs = []

    missing_by_episode = {item["episode"]: item for item in before["missing_images"]}
    strms = {item["episode"]: item for item in _parse_strms(season)}
    pending = _pending_images(season)
    for src, plan in zip(pending, before["image_plan"]):
        item = missing_by_episode.get(plan["episode"])
        if not item:
            continue
        strm = strms[item["episode"]]["path"]
        target = strm.with_suffix(".JPG")
        if target.exists():
            logs.append(f"跳过已存在图片: {target.name}")
            continue
        src.rename(target)
        logs.append(f"重命名图片: {src.name} -> {target.name}")

    for item in _parse_strms(season):
        nfo = item["path"].with_suffix(".nfo")
        if nfo.exists() and nfo.stat().st_size > 0:
            continue
        nfo.write_text(_episode_nfo(item["title"], item["season"], item["episode"]), encoding="utf-8")
        logs.append(f"生成NFO: {nfo.name}")

    if req.refresh_emby:
        try:
            refresh_result = await _refresh_emby_for_actor(actor_dir)
            if refresh_result.get("mode") == "item":
                logs.append(f"刷新Emby项目: {refresh_result.get('name') or actor_dir.name}")
            elif refresh_result.get("mode") == "library_fallback":
                logs.append("未找到Emby项目，已改为全库刷新")
            else:
                logs.append("刷新Emby媒体库: 已提交")
        except HTTPException as exc:
            logs.append(f"刷新Emby媒体库失败: {exc.detail}")

    return {"ok": True, "logs": logs, "scan": _build_scan(actor_dir)}


@router.post("/automation/tvshow")
async def save_tvshow(req: TvshowRequest):
    actor_dir = _safe_actor_dir(req.actor_dir)
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="演员名不能为空")
    path = actor_dir / "tvshow.nfo"
    if path.exists() and not req.overwrite:
        raise HTTPException(status_code=409, detail="tvshow.nfo 已存在，请确认覆盖")
    backup = _backup(path)
    path.write_text(_tvshow_xml(req), encoding="utf-8")
    return {"ok": True, "path": str(path), "backup": backup}


@router.post("/automation/upload-artwork")
async def upload_artwork(
    actor_dir: str = Form(...),
    kind: str = Form(...),
    overwrite: bool = Form(False),
    image: UploadFile = File(...),
):
    actor = _safe_actor_dir(actor_dir)
    targets = {"poster": "poster.jpg", "fanart": "fanart.jpg", "logo": "logo.png"}
    if kind not in targets:
        raise HTTPException(status_code=400, detail="图片类型必须是 poster/fanart/logo")
    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 jpg/jpeg/png/webp 图片")
    target = actor / targets[kind]
    if target.exists() and not overwrite:
        raise HTTPException(status_code=409, detail=f"{target.name} 已存在，请确认替换")
    backup = _backup(target)
    content = await image.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传图片为空")
    target.write_bytes(content)
    return {"ok": True, "filename": target.name, "backup": backup}


@router.post("/automation/upload-episode-images")
async def upload_episode_images(actor_dir: str = Form(...), images: list[UploadFile] = File(...)):
    actor = _safe_actor_dir(actor_dir)
    season = _season_dir(actor)
    saved = []
    for image in images:
        suffix = Path(image.filename or "").suffix.lower()
        if suffix not in IMAGE_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式: {image.filename}")
        target = season / Path(image.filename or "upload.jpg").name
        if target.exists():
            stem = target.stem
            target = season / f"{stem}.upload.{datetime.now().strftime('%Y%m%d%H%M%S%f')}{target.suffix}"
        content = await image.read()
        if content:
            target.write_bytes(content)
            saved.append(target.name)
    return {"ok": True, "saved": saved, "scan": _build_scan(actor)}

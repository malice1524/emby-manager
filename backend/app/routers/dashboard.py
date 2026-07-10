from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response
from ..config import EMBY_URL, HEADERS
from ..settings_store import load_metube_settings
from collections import Counter
from pathlib import Path
import json
import os
import re
import httpx

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

METUBE_PROGRESS_FILE = Path(os.environ.get("METUBE_PROGRESS_FILE", "/vol1/1000/docker/metube/uploader/upload-progress.json"))
METUBE_STATE_FILE = Path(os.environ.get("METUBE_STATE_FILE", "/vol1/1000/docker/metube/uploader/upload-state.json"))
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}

_SECRET_RE = re.compile(r"(?i)('?(?:user_key|token|cookie|password|secret)'?\s*[:=]\s*)'[^']*'")


def _read_json_file(path: Path, fallback):
    try:
        if not path.exists():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _format_bytes(size: int | float | None) -> str:
    try:
        value = float(size or 0)
    except Exception:
        value = 0.0
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.2f} {units[idx]}" if idx else f"{int(value)} B"


def _redact_error(text: str) -> str:
    if not text:
        return ""
    redacted = _SECRET_RE.sub(lambda m: f"{m.group(1)}'[redacted]'", text)
    if len(redacted) > 1000:
        return redacted[:1000] + "..."
    return redacted


def _error_type(text: str) -> str:
    if not text:
        return ""
    return text.split(":", 1)[0].strip()[:80]


def _is_video_filename(filename: str) -> bool:
    return Path(filename or "").suffix.lower() in VIDEO_EXTS


async def _fetch_metube_history() -> dict:
    metube_url = load_metube_settings()["url"].rstrip("/")
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(f"{metube_url}/history")
        resp.raise_for_status()
        return resp.json()


def _summarize_metube(history: dict) -> dict:
    counts = Counter()
    total = 0
    for items in history.values():
        if not isinstance(items, list):
            continue
        for item in items:
            total += 1
            counts[item.get("status") or "unknown"] += 1
    return {
        "finished": counts.get("finished", 0),
        "downloading": counts.get("downloading", 0),
        "pending": counts.get("pending", 0),
        "preparing": counts.get("preparing", 0),
        "failed": counts.get("failed", 0) + counts.get("error", 0),
        "total": total,
    }


@router.get("/metube")
async def get_metube_dashboard_status():
    """Read MeTube queue and 115 uploader progress for the dashboard."""
    progress = _read_json_file(METUBE_PROGRESS_FILE, {})
    if not isinstance(progress, dict) or not _is_video_filename(str(progress.get("filename") or "")):
        progress = {}
    state = _read_json_file(METUBE_STATE_FILE, {})
    status_counts = Counter()
    failed = []
    if isinstance(state, dict):
        for filename, entry in state.items():
            if not isinstance(entry, dict):
                continue
            status = entry.get("status") or "unknown"
            status_counts[status] += 1
            if status == "upload_failed":
                raw_error = str(entry.get("error") or "")
                failed.append({
                    "filename": filename,
                    "size": entry.get("size") or 0,
                    "size_text": _format_bytes(entry.get("size") or 0),
                    "updated_at": entry.get("updated_at") or "",
                    "error_type": _error_type(raw_error),
                    "error": _redact_error(raw_error),
                })

    try:
        history = await _fetch_metube_history()
        metube = _summarize_metube(history)
        available = True
        error = ""
    except Exception as exc:
        metube = {"finished": 0, "downloading": 0, "pending": 0, "preparing": 0, "failed": 0, "total": 0}
        available = False
        error = f"MeTube 不可用: {type(exc).__name__}: {exc}"

    return {
        "available": available,
        "error": error,
        "progress": progress if isinstance(progress, dict) else {},
        "metube": metube,
        "uploader": {
            "total": sum(status_counts.values()),
            "statuses": dict(status_counts),
        },
        "failed": failed,
    }


@router.get("/images/{item_id}")
async def proxy_image(
    item_id: str,
    w: int = Query(default=400, ge=50, le=1200),
    type: str = Query(default="item"),
):
    """Proxy Emby images through backend.
    type=item -> Item images, type=user -> User profile images."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if type == "user":
                url = f"{EMBY_URL}/emby/Users/{item_id}/Images/Primary"
            else:
                url = f"{EMBY_URL}/emby/Items/{item_id}/Images/Primary"
            resp = await client.get(url, params={"maxWidth": w, "api_key": HEADERS["X-Emby-Token"]})
            if resp.status_code != 200:
                raise HTTPException(status_code=404)
            return Response(
                content=resp.content,
                media_type=resp.headers.get("content-type", "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image proxy timeout")


@router.get("/overview")
async def get_dashboard_overview():
    """Aggregated overview for the dashboard."""
    async with httpx.AsyncClient(timeout=30) as client:
        import asyncio

        async def fetch_counts():
            r = await client.get(f"{EMBY_URL}/Items/Counts", headers=HEADERS)
            return r.json() if r.status_code == 200 else {}

        async def fetch_sessions():
            r = await client.get(f"{EMBY_URL}/Sessions", headers=HEADERS)
            return r.json() if r.status_code == 200 else []

        async def fetch_users():
            r = await client.get(f"{EMBY_URL}/Users/Public", headers=HEADERS)
            return r.json() if r.status_code == 200 else []

        async def fetch_libraries():
            r = await client.get(f"{EMBY_URL}/Library/VirtualFolders", headers=HEADERS)
            return r.json() if r.status_code == 200 else []

        async def fetch_system():
            r = await client.get(f"{EMBY_URL}/System/Info", headers=HEADERS)
            return r.json() if r.status_code == 200 else {}

        counts, sessions, users, libraries, system = await asyncio.gather(
            fetch_counts(), fetch_sessions(), fetch_users(),
            fetch_libraries(), fetch_system()
        )

        admin_count = 0
        for u in users:
            if u.get("Policy", {}).get("IsAdministrator", False):
                admin_count += 1

        active_streams = []
        for s in sessions:
            np = s.get("NowPlayingItem", {})
            play_state = s.get("PlayState", {})
            item_id = np.get("Id", "")
            has_playing = bool(np)
            position_ticks = play_state.get("PositionTicks", 0) if has_playing else 0
            runtime_ticks = np.get("RunTimeTicks", 0) if has_playing else 0
            progress = (position_ticks / runtime_ticks * 100) if runtime_ticks > 0 else 0
            active_streams.append({
                "username": s.get("UserName", "Unknown"),
                "client": s.get("Client", "Unknown"),
                "device": s.get("DeviceName", "Unknown"),
                "now_playing": np.get("Name", "Idle") if has_playing else None,
                "play_state": "playing" if (has_playing and not play_state.get("IsPaused", True)) else "paused" if has_playing else "idle",
                "item_id": item_id,
                "progress": round(progress, 1),
                "has_playing": has_playing,
                "image_url": f"/api/dashboard/images/{item_id}?w=200" if item_id else None,
            })

        return {
            "media": {
                "movies": counts.get("MovieCount", 0),
                "series": counts.get("SeriesCount", 0),
                "episodes": counts.get("EpisodeCount", 0),
            },
            "users": {
                "total": len(users),
                "admins": admin_count,
            },
            "sessions": {
                "active": len(sessions),
                "streams": active_streams,
            },
            "libraries": len(libraries),
            "server": {
                "name": system.get("ServerName", "Emby"),
                "version": system.get("Version", "Unknown"),
            },
        }


@router.get("/recent")
async def get_recent_items(
    limit: int = Query(default=12, ge=1, le=50),
    types: str = Query(default="Movie,Series"),
    parent_id: str = Query(default=""),
    exclude_parent_ids: str = Query(default=""),
):
    """Get recently added media items (image URLs use proxy).
    exclude_parent_ids: comma-separated library IDs to exclude.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        # If excluding libraries, fetch their item IDs first
        excluded_ids = set()
        if exclude_parent_ids:
            for pid in exclude_parent_ids.split(","):
                pid = pid.strip()
                if not pid:
                    continue
                try:
                    eresp = await client.get(
                        f"{EMBY_URL}/emby/Items",
                        params={
                            "Recursive": "true",
                            "ParentId": pid,
                            "Limit": 200,
                            "Fields": "",
                        },
                        headers=HEADERS,
                    )
                    if eresp.status_code == 200:
                        for eitem in eresp.json().get("Items", []):
                            excluded_ids.add(eitem.get("Id", ""))
                except Exception:
                    pass

        params = {
            "Recursive": "true",
            "SortBy": "DateCreated",
            "SortOrder": "Descending",
            "IncludeItemTypes": types,
            "Limit": limit + 100,
            "Fields": "PrimaryImageAspectRatio,Overview,CommunityRating",
        }
        if parent_id:
            params["ParentId"] = parent_id

        resp = await client.get(
            f"{EMBY_URL}/emby/Items",
            params=params,
            headers=HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

        items = []
        for item in data.get("Items", []):
            item_id = item.get("Id", "")
            if item_id in excluded_ids:
                continue
            has_image = bool(item.get("ImageTags", {}).get("Primary"))
            items.append({
                "id": item_id,
                "name": item.get("Name", "Unknown"),
                "type": item.get("Type", ""),
                "year": item.get("ProductionYear"),
                "overview": (item.get("Overview") or "")[:200],
                "rating": item.get("CommunityRating"),
                "image_url": f"/api/dashboard/images/{item_id}?w=400" if has_image else None,
            })
            if len(items) >= limit:
                break

        return {"items": items}


@router.get("/item/{item_id}")
async def get_item_detail(item_id: str):
    """Get detailed item info including TMDB ID, cast, genres."""
    async with httpx.AsyncClient(timeout=15) as client:
        fields = "ProviderIds,People,Genres,CommunityRating,Overview,ProductionYear"
        admin_user_id = await _get_admin_user_id(client)
        urls = []
        if admin_user_id:
            urls.append(f"{EMBY_URL}/emby/Users/{admin_user_id}/Items/{item_id}")
        urls.append(f"{EMBY_URL}/emby/Items/{item_id}")

        data = None
        for url in urls:
            resp = await client.get(url, params={"Fields": fields}, headers=HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                break
        if data is None:
            raise HTTPException(status_code=404, detail="Item not found")
        provider_ids = data.get("ProviderIds", {})
        tmdb_id = provider_ids.get("Tmdb")
        imdb_id = provider_ids.get("Imdb")
        item_type = data.get("Type", "Movie")
        tmdb_type = "tv" if item_type == "Series" else "movie"

        cast = []
        for p in data.get("People", []):
            pid = p.get("Id", "")
            has_img = bool(p.get("PrimaryImageTag"))
            cast.append({
                "name": p.get("Name", ""),
                "role": p.get("Role", ""),
                "type": p.get("Type", ""),
                "person_id": pid,
                "avatar_url": f"/api/dashboard/images/{pid}?w=100" if pid and has_img else None,
            })

        return {
            "id": item_id,
            "name": data.get("Name", ""),
            "overview": data.get("Overview", ""),
            "type": item_type,
            "year": data.get("ProductionYear"),
            "rating": data.get("CommunityRating"),
            "genres": data.get("Genres", []),
            "tmdb_id": tmdb_id,
            "imdb_id": imdb_id,
            "tmdb_url": f"https://www.themoviedb.org/{tmdb_type}/{tmdb_id}" if tmdb_id else None,
            "imdb_url": f"https://www.imdb.com/title/{imdb_id}" if imdb_id else None,
            "cast": cast,
            "image_url": f"/api/dashboard/images/{item_id}?w=400",
        }


@router.get("/stats")
async def get_dashboard_stats():
    """Legacy stats endpoint with activity log."""
    async with httpx.AsyncClient(timeout=30) as client:
        activity = await client.get(
            f"{EMBY_URL}/System/ActivityLog/Entries",
            params={"Limit": 15},
            headers=HEADERS
        )
        system = await client.get(
            f"{EMBY_URL}/System/Info",
            headers=HEADERS
        )

        activity_data = activity.json() if activity.status_code == 200 else {"Items": []}
        system_data = system.json() if system.status_code == 200 else {}

        return {
            "activity": [
                {
                    "name": a.get("Name", ""),
                    "short_overview": a.get("ShortOverview", ""),
                    "date": a.get("Date", ""),
                    "severity": a.get("Severity", ""),
                }
                for a in activity_data.get("Items", [])[:15]
            ],
            "system": system_data,
        }


async def _get_admin_user_id(client: httpx.AsyncClient) -> str:
    users_resp = await client.get(f"{EMBY_URL}/emby/Users", headers=HEADERS)
    if users_resp.status_code == 200:
        users = users_resp.json()
        for user in users:
            if user.get("Policy", {}).get("IsAdministrator"):
                return user.get("Id", "")
        if users:
            return users[0].get("Id", "")
    return ""


def _emby_auth_headers(token: str, user_id: str = "") -> dict:
    """Build Emby headers with optional user context for user-scoped operations."""
    headers = {"X-Emby-Token": token}
    if user_id:
        headers["X-Emby-Authorization"] = (
            'MediaBrowser Client="Emby Manager", Device="Server", '
            f'DeviceId="emby-manager", Version="1.0.0", UserId="{user_id}"'
        )
    return headers


async def _get_user_token(client: httpx.AsyncClient) -> str:
    """Get a user access token for admin operations."""
    from ..config import EMBY_ADMIN_USER, EMBY_ADMIN_PW
    if not EMBY_ADMIN_PW:
        return ""
    auth_header = 'MediaBrowser Client="Emby Manager", Device="Server", DeviceId="emby-manager", Version="1.0.0"'
    resp = await client.post(
        f"{EMBY_URL}/emby/Users/AuthenticateByName",
        json={"Username": EMBY_ADMIN_USER, "Pw": EMBY_ADMIN_PW},
        headers={"X-Emby-Authorization": auth_header},
    )
    if resp.status_code == 200:
        return resp.json().get("AccessToken", "")
    return ""


@router.delete("/item/{item_id}")
async def delete_media_item(item_id: str):
    """Delete a media item from Emby."""
    async with httpx.AsyncClient(timeout=20) as client:
        errors = []
        delete_urls = [
            f"{EMBY_URL}/emby/Items/{item_id}",
            f"{EMBY_URL}/Items/{item_id}",
        ]

        admin_user_id = await _get_admin_user_id(client)

        # First try the configured API key with an explicit admin user context.
        for url in delete_urls:
            resp = await client.request(
                "DELETE",
                url,
                params={"UserId": admin_user_id} if admin_user_id else None,
                headers=_emby_auth_headers(HEADERS["X-Emby-Token"], admin_user_id),
            )
            if resp.status_code in (200, 204):
                return {"status": "ok"}
            errors.append(f"API key {resp.status_code}: {resp.text[:120]}")

        # Fall back to an authenticated admin user token when configured.
        token = await _get_user_token(client)
        if token:
            for url in delete_urls:
                resp = await client.request("DELETE", url, headers=_emby_auth_headers(token, admin_user_id))
                if resp.status_code in (200, 204):
                    return {"status": "ok"}
                errors.append(f"admin token {resp.status_code}: {resp.text[:120]}")
        else:
            if any("Parameter 'user'" in err or "Parameter &#39;user&#39;" in err for err in errors):
                raise HTTPException(
                    status_code=403,
                    detail="删除失败：当前 Emby API Key 无法执行删除，请在 Docker 环境变量中配置 EMBY_ADMIN_USER 和 EMBY_ADMIN_PW 后重启容器。",
                )
            errors.append("admin token unavailable: set EMBY_ADMIN_PW if API key deletion is not allowed")

        raise HTTPException(status_code=403, detail="删除失败：" + " | ".join(errors[-3:]))

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response
from ..config import EMBY_URL, HEADERS
import httpx

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


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
):
    """Get recently added media items (image URLs use proxy)."""
    async with httpx.AsyncClient(timeout=30) as client:
        params = {
            "Recursive": "true",
            "SortBy": "DateCreated",
            "SortOrder": "Descending",
            "IncludeItemTypes": types,
            "Limit": limit,
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

        return {"items": items}


@router.get("/item/{item_id}")
async def get_item_detail(item_id: str):
    """Get detailed item info including TMDB ID, cast, genres."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{EMBY_URL}/Users/fb1f0470dfae4ecc8649529346f199fc/Items/{item_id}",
            params={
                "Fields": "ProviderIds,People,Genres,CommunityRating,Overview,ProductionYear",
            },
            headers=HEADERS,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Item not found")

        data = resp.json()
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


@router.delete("/item/{item_id}")
async def delete_media_item(item_id: str):
    """Delete a media item from Emby."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.delete(
            f"{EMBY_URL}/emby/Items/{item_id}",
            headers=HEADERS,
        )
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=resp.status_code, detail="Failed to delete item")
        return {"status": "ok"}

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response
from ..config import EMBY_URL, HEADERS
import httpx

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/images/{item_id}")
async def proxy_image(item_id: str, w: int = Query(default=400, ge=50, le=1200)):
    """Proxy Emby images through backend to avoid cross-origin/LAN issues."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{EMBY_URL}/emby/Items/{item_id}/Images/Primary",
                params={"maxWidth": w, "api_key": HEADERS["X-Emby-Token"]},
            )
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
            item_id = np.get("Id", "")
            active_streams.append({
                "username": s.get("UserName", "Unknown"),
                "client": s.get("Client", "Unknown"),
                "device": s.get("DeviceName", "Unknown"),
                "now_playing": np.get("Name", "Idle") if np else "Idle",
                "play_state": s.get("PlayState", {}).get("PlayMethod", "Idle"),
                "item_id": item_id,
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
):
    """Get recently added media items (image URLs use proxy)."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{EMBY_URL}/emby/Items",
            params={
                "Recursive": "true",
                "SortBy": "DateCreated",
                "SortOrder": "Descending",
                "IncludeItemTypes": types,
                "Limit": limit,
                "Fields": "PrimaryImageAspectRatio,Overview,CommunityRating",
            },
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
                "backdrop_url": f"/api/dashboard/images/{item_id}?w=800" if has_image else None,
            })

        return {"items": items}


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

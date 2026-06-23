from fastapi import APIRouter, Query
from ..config import EMBY_URL, HEADERS
import httpx

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _make_image_url(item_id: str, max_width: int = 400) -> str:
    """Construct Emby primary image URL."""
    return f"{EMBY_URL}/emby/Items/{item_id}/Images/Primary?maxWidth={max_width}&api_key={HEADERS['X-Emby-Token']}"


def _make_backdrop_url(item_id: str, max_width: int = 800) -> str:
    """Construct Emby backdrop image URL."""
    return f"{EMBY_URL}/emby/Items/{item_id}/Images/Backdrop?maxWidth={max_width}&api_key={HEADERS['X-Emby-Token']}"


@router.get("/overview")
async def get_dashboard_overview():
    """Aggregated overview for the dashboard."""
    async with httpx.AsyncClient(timeout=30) as client:
        # Parallel fetches
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

        # Count admins
        admin_count = 0
        for u in users:
            if u.get("Policy", {}).get("IsAdministrator", False):
                admin_count += 1

        # Active streams
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
                "image_url": _make_image_url(item_id, 200) if item_id else None,
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
    """Get recently added media items with poster URLs."""
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
                "image_url": _make_image_url(item_id, 400) if has_image else None,
                "backdrop_url": _make_backdrop_url(item_id, 800) if has_image else None,
            })

        return {"items": items}

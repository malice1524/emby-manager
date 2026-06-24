from fastapi import APIRouter, Query, HTTPException
from ..config import EMBY_URL, HEADERS
import httpx

router = APIRouter(prefix="/api/libraries", tags=["libraries"])


@router.get("")
async def get_libraries():
    async with httpx.AsyncClient(timeout=30) as client:
        # Get user's library view order
        users_resp = await client.get(f"{EMBY_URL}/emby/Users", headers=HEADERS)
        uid = ""
        if users_resp.status_code == 200:
            for u in users_resp.json():
                if u.get("Policy", {}).get("IsAdministrator"):
                    uid = u["Id"]
                    break

        views_resp = await client.get(
            f"{EMBY_URL}/emby/Users/{uid}/Views",
            headers=HEADERS
        )
        folders = []
        if views_resp.status_code == 200:
            for item in views_resp.json().get("Items", []):
                folders.append({
                    "ItemId": item.get("Id", ""),
                    "Name": item.get("Name", "Unknown"),
                    "CollectionType": item.get("CollectionType", "mixed"),
                    "Locations": item.get("Locations", []),
                })

        libraries = []
        for folder in folders:

            size_info = await client.get(
                f"{EMBY_URL}/Items/Counts",
                headers=HEADERS,
                params={"ParentId": folder.get("ItemId", "")}
            )
            counts = size_info.json() if size_info.status_code == 200 else {}

            libraries.append({
                "id": folder.get("ItemId", ""),
                "name": folder.get("Name", "Unknown"),
                "type": folder.get("CollectionType", "mixed"),
                "locations": [],
                "counts": {
                    "movies": counts.get("MovieCount", 0),
                    "series": counts.get("SeriesCount", 0),
                    "episodes": counts.get("EpisodeCount", 0),
                    "albums": counts.get("AlbumCount", 0),
                    "songs": counts.get("SongCount", 0),
                    "total": sum(counts.values()) if isinstance(counts, dict) else 0,
                },
            })

        return {"libraries": libraries}


@router.get("/{item_id}/items")
async def get_library_items(
    item_id: str,
    limit: int = Query(default=30, le=100),
    page: int = Query(default=0),
    search: str = Query(default=""),
    types: str = Query(default=""),
):
    """Get items within a library with pagination and search.
    types=movies -> Movie only, types=tvshows -> Series only.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        params = {
            "Recursive": "true",
            "ParentId": item_id,
            "Limit": limit,
            "StartIndex": page * limit,
        }
        if types == "tvshows":
            params["IncludeItemTypes"] = "Series"
        elif types == "movies":
            params["IncludeItemTypes"] = "Movie"
        elif types:
            params["IncludeItemTypes"] = types
        if search:
            params["SearchTerm"] = search

        resp = await client.get(
            f"{EMBY_URL}/emby/Items",
            params=params,
            headers=HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

        items = []
        for item in data.get("Items", []):
            items.append({
                "id": item.get("Id", ""),
                "name": item.get("Name", "Unknown"),
                "type": item.get("Type", ""),
                "year": item.get("ProductionYear"),
                "runtime_min": item.get("RunTimeTicks", 0) // 600000000
                if item.get("RunTimeTicks") else None,
                "has_image": bool(item.get("ImageTags", {}).get("Primary")),
            })

        return {
            "items": items,
            "total": data.get("TotalRecordCount", 0),
        }

from fastapi import APIRouter, Query, HTTPException
from ..config import EMBY_URL, HEADERS
import httpx

router = APIRouter(prefix="/api/libraries", tags=["libraries"])


@router.get("")
async def get_libraries():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{EMBY_URL}/Library/VirtualFolders",
            headers=HEADERS
        )
        resp.raise_for_status()
        folders = resp.json()

        libraries = []
        for folder in folders:
            primary_type = folder.get("CollectionType", "mixed")

            size_info = await client.get(
                f"{EMBY_URL}/Items/Counts",
                headers=HEADERS,
                params={"ParentId": folder.get("ItemId", "")}
            )
            counts = size_info.json() if size_info.status_code == 200 else {}

            libraries.append({
                "id": folder.get("ItemId", ""),
                "name": folder.get("Name", "Unknown"),
                "type": primary_type,
                "locations": folder.get("Locations", []),
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
):
    """Get items within a library with pagination and search."""
    async with httpx.AsyncClient(timeout=30) as client:
        params = {
            "Recursive": "true",
            "ParentId": item_id,
            "Limit": limit,
            "StartIndex": page * limit,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
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
            })

        return {
            "items": items,
            "total": data.get("TotalRecordCount", 0),
        }

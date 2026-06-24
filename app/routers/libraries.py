from fastapi import APIRouter, Query, HTTPException
from ..config import EMBY_URL, HEADERS
import httpx

router = APIRouter(prefix="/api/libraries", tags=["libraries"])


@router.get("")
async def get_libraries():
    async with httpx.AsyncClient(timeout=60) as client:
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
                })

        import asyncio

        async def get_lib_counts(folder):
            parent_id = folder["ItemId"]
            async def count_type(itype):
                r = await client.get(
                    f"{EMBY_URL}/emby/Items",
                    headers=HEADERS,
                    params={
                        "ParentId": parent_id,
                        "Recursive": "true",
                        "Limit": 0,
                        "IncludeItemTypes": itype,
                    }
                )
                if r.status_code == 200:
                    return r.json().get("TotalRecordCount", 0)
                return 0

            c_movies, c_series, c_episodes, c_albums, c_songs = await asyncio.gather(
                count_type("Movie"),
                count_type("Series"),
                count_type("Episode"),
                count_type("MusicAlbum"),
                count_type("Audio"),
            )
            return {
                "movies": c_movies,
                "series": c_series,
                "episodes": c_episodes,
                "albums": c_albums,
                "songs": c_songs,
                "total": c_movies + c_series + c_episodes + c_albums + c_songs,
            }

        libraries = []
        for folder in folders:
            counts = await get_lib_counts(folder)
            libraries.append({
                "id": folder.get("ItemId", ""),
                "name": folder.get("Name", "Unknown"),
                "type": folder.get("CollectionType", "mixed"),
                "locations": [],
                "counts": counts,
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

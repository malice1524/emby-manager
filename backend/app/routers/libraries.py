from fastapi import APIRouter
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

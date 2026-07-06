from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote

TVMAZE_API_BASE = "https://api.tvmaze.com"
BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def format_beijing_airtime(episode: dict) -> str:
    """Format a TVmaze episode airing time in Beijing time, falling back to date."""
    airstamp = episode.get("airstamp") or ""
    if airstamp:
        try:
            dt = datetime.fromisoformat(airstamp.replace("Z", "+00:00"))
            return dt.astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M 北京时间")
        except ValueError:
            pass
    return episode.get("airdate") or ""


async def lookup_show_by_external_ids(tvdb_id=None, imdb_id=None):
    """Find a TVmaze show using TheTVDB first, then IMDb."""
    from .config import get_http_client

    lookups = []
    if tvdb_id:
        lookups.append(("thetvdb", str(tvdb_id)))
    if imdb_id:
        lookups.append(("imdb", str(imdb_id)))

    async with get_http_client() as client:
        for key, value in lookups:
            try:
                resp = await client.get(f"{TVMAZE_API_BASE}/lookup/shows", params={key: value})
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                continue
    return None


async def get_episode_airtime(tvmaze_id: int, season_number: int, episode_number: int):
    """Return the TVmaze episode matching season/episode with Beijing display time."""
    from .config import get_http_client

    try:
        async with get_http_client() as client:
            resp = await client.get(f"{TVMAZE_API_BASE}/shows/{tvmaze_id}/episodes")
            if resp.status_code != 200:
                return None
            for episode in resp.json():
                if episode.get("season") == season_number and episode.get("number") == episode_number:
                    return {
                        "airdate": episode.get("airdate", ""),
                        "airtime": episode.get("airtime", ""),
                        "airstamp": episode.get("airstamp", ""),
                        "runtime": episode.get("runtime"),
                        "url": episode.get("url", ""),
                        "air_time_display": format_beijing_airtime(episode),
                    }
    except Exception:
        return None
    return None


async def get_episode_airtime_by_external_ids(tvdb_id=None, imdb_id=None, season_number: int = 0, episode_number: int = 0):
    """Lookup show by external ids and return episode airing information."""
    show = await lookup_show_by_external_ids(tvdb_id=tvdb_id, imdb_id=imdb_id)
    if not show or not show.get("id"):
        return None
    return await get_episode_airtime(show["id"], season_number, episode_number)

import httpx

TMDB_API_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"

def _get_api_key():
    from .config import load_tg_config
    cfg = load_tg_config()
    return cfg.get("tmdb_api_key", "")

async def verify_api_key():
    """验证 TMDB API Key 是否有效"""
    key = _get_api_key()
    if not key:
        return {"valid": False, "error": "API Key 未配置"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{TMDB_API_BASE}/configuration", params={"api_key": key})
            if resp.status_code == 200:
                return {"valid": True}
            elif resp.status_code == 401:
                return {"valid": False, "error": "API Key 无效"}
            else:
                return {"valid": False, "error": f"TMDB 返回错误: {resp.status_code}"}
    except httpx.TimeoutException:
        return {"valid": False, "error": "连接 TMDB 超时"}
    except Exception as e:
        return {"valid": False, "error": str(e)}

async def search_tv(query: str, page: int = 1):
    """搜索剧集"""
    key = _get_api_key()
    if not key:
        return {"results": [], "error": "API Key 未配置"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{TMDB_API_BASE}/search/tv",
                params={"api_key": key, "query": query, "language": "zh-CN", "page": page}
            )
            if resp.status_code != 200:
                return {"results": [], "error": f"搜索失败: {resp.status_code}"}
            data = resp.json()
            results = []
            for item in data.get("results", [])[:10]:
                poster = f"{POSTER_BASE}{item.get('poster_path')}" if item.get("poster_path") else ""
                results.append({
                    "tmdb_id": item["id"],
                    "title": item.get("name", ""),
                    "original_title": item.get("original_name", ""),
                    "year": item.get("first_air_date", "")[:4] if item.get("first_air_date") else "",
                    "poster_url": poster,
                    "overview": item.get("overview", ""),
                    "vote_average": round(item.get("vote_average", 0), 1),
                    "genre_ids": item.get("genre_ids", []),
                    "media_type": "tv"
                })
            return {"results": results, "total_pages": data.get("total_pages", 1)}
    except httpx.TimeoutException:
        return {"results": [], "error": "连接 TMDB 超时"}
    except Exception as e:
        return {"results": [], "error": str(e)}

GENRE_MAP = {
    10759: "动作冒险", 16: "动画", 35: "喜剧", 80: "犯罪", 99: "纪录片",
    18: "剧情", 10751: "家庭", 10762: "儿童", 10763: "新闻", 10764: "真人秀",
    10765: "科幻", 10766: "肥皂剧", 10767: "脱口秀", 10768: "战争政治",
    37: "西部", 28: "动作", 12: "冒险", 14: "奇幻", 36: "历史",
    27: "恐怖", 10402: "音乐", 9648: "悬疑", 10749: "爱情", 878: "科幻",
    53: "惊悚", 10752: "战争", 10770: "电视电影"
}

async def get_tv_detail(tmdb_id: int):
    """获取剧集详情（状态、下一集、最新集、总集数、类型、评分、简介）"""
    key = _get_api_key()
    if not key:
        return {"error": "API Key 未配置"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{TMDB_API_BASE}/tv/{tmdb_id}",
                params={"api_key": key, "language": "zh-CN"}
            )
            if resp.status_code != 200:
                return {"error": f"获取详情失败: {resp.status_code}"}
            data = resp.json()

            poster = f"{POSTER_BASE}{data.get('poster_path')}" if data.get("poster_path") else ""
            genres = [g.get("name", "") for g in data.get("genres", [])]
            genre_str = " / ".join(genres) if genres else "未知"

            next_ep = data.get("next_episode_to_air")
            last_ep = data.get("last_episode_to_air")

            return {
                "tmdb_id": data["id"],
                "title": data.get("name", ""),
                "original_title": data.get("original_name", ""),
                "year": data.get("first_air_date", "")[:4] if data.get("first_air_date") else "",
                "poster_url": poster,
                "overview": data.get("overview", ""),
                "status": data.get("status", "Unknown"),
                "type": genre_str,
                "vote_average": round(data.get("vote_average", 0), 1),
                "number_of_seasons": data.get("number_of_seasons", 0),
                "number_of_episodes": data.get("number_of_episodes", 0),
                "in_production": data.get("in_production", False),
                "first_air_date": data.get("first_air_date", ""),
                "last_air_date": data.get("last_air_date", ""),
                "next_episode_to_air": {
                    "air_date": next_ep.get("air_date", "") if next_ep else "",
                    "episode_number": next_ep.get("episode_number", 0) if next_ep else 0,
                    "season_number": next_ep.get("season_number", 0) if next_ep else 0,
                    "name": next_ep.get("name", "") if next_ep else ""
                } if next_ep else None,
                "last_episode_to_air": {
                    "air_date": last_ep.get("air_date", "") if last_ep else "",
                    "episode_number": last_ep.get("episode_number", 0) if last_ep else 0,
                    "season_number": last_ep.get("season_number", 0) if last_ep else 0,
                    "name": last_ep.get("name", "") if last_ep else ""
                } if last_ep else None
            }
    except httpx.TimeoutException:
        return {"error": "连接 TMDB 超时"}
    except Exception as e:
        return {"error": str(e)}

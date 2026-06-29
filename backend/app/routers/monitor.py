from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from .. import tmdb_client, tg_notifier, series_monitor
from ..config import MONITORED_SERIES_PATH, CONFIG_PATH, MONITOR_DATA_DIR, load_tg_config
import json
import os

router = APIRouter(prefix="/api", tags=["monitor"])

# ==================== TMDB 接口 ====================

@router.get("/tmdb/search")
async def tmdb_search(q: str = Query(..., min_length=1), page: int = Query(1, ge=1)):
    result = await tmdb_client.search_tv(q, page)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/tmdb/detail/{tmdb_id}")
async def tmdb_detail(tmdb_id: int):
    result = await tmdb_client.get_tv_detail(tmdb_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/tmdb/verify")
async def tmdb_verify():
    result = await tmdb_client.verify_api_key()
    return result

# ==================== 监控列表接口 ====================

@router.get("/monitor/list")
async def monitor_list():
    series_list = series_monitor._load_series()
    # 异步刷新每部剧的最新状态
    refreshed = []
    for s in series_list:
        detail = await tmdb_client.get_tv_detail(s["tmdb_id"])
        if "error" not in detail:
            s["current_status"] = detail.get("status", s.get("last_status", ""))
            s["type"] = detail.get("type", "")
            s["vote_average"] = detail.get("vote_average", 0)
            next_ep = detail.get("next_episode_to_air")
            s["next_episode"] = {
                "air_date": next_ep.get("air_date", "") if next_ep else "",
                "episode_number": next_ep.get("episode_number", 0) if next_ep else 0,
                "season_number": next_ep.get("season_number", 0) if next_ep else 0
            } if next_ep else None
            last_ep = detail.get("last_episode_to_air")
            s["last_episode"] = {
                "air_date": last_ep.get("air_date", "") if last_ep else "",
                "episode_number": last_ep.get("episode_number", 0) if last_ep else 0,
                "season_number": last_ep.get("season_number", 0) if last_ep else 0
            } if last_ep else None
            s["total_episodes"] = detail.get("number_of_episodes", 0)
            s["last_air_date"] = detail.get("last_air_date", "")
        else:
            s["current_status"] = s.get("last_status", "")
        refreshed.append(s)
    return {"series": refreshed}

class AddSeriesRequest(BaseModel):
    tmdb_id: int
    title: str
    year: str = ""
    poster_url: str = ""

@router.post("/monitor/add")
async def monitor_add(req: AddSeriesRequest):
    series_list = series_monitor._load_series()

    # 检查是否已存在
    for s in series_list:
        if s["tmdb_id"] == req.tmdb_id:
            raise HTTPException(status_code=400, detail="该剧集已在监控列表中")

    # 获取 TMDB 详情
    detail = await tmdb_client.get_tv_detail(req.tmdb_id)
    if "error" in detail:
        raise HTTPException(status_code=400, detail=detail["error"])

    current_status = detail.get("status", "Unknown")
    last_ep = detail.get("last_episode_to_air")

    new_entry = {
        "tmdb_id": req.tmdb_id,
        "title": req.title,
        "poster_url": req.poster_url,
        "added_at": "",
        "last_status": current_status,
        "last_episode_air_date": last_ep.get("air_date", "") if last_ep else "",
        "last_episode_number": last_ep.get("episode_number", 0) if last_ep else 0,
        "notified_ended": False
    }
    series_list.append(new_entry)
    series_monitor._save_series(series_list)

    # 获取模板
    cfg = load_tg_config()
    update_template = cfg.get("update_template", "")
    end_template = cfg.get("end_template", "")

    # 首次添加：根据状态发通知
    notification_sent = False
    if current_status == "Ended":
        # 已完结 → 发完结通知
        result = await tg_notifier.send_end_notification(
            series_name=req.title,
            end_date=detail.get("last_air_date", "未知"),
            total_episodes=detail.get("number_of_episodes", 0),
            series_type=detail.get("type", "未知"),
            rating=detail.get("vote_average", 0),
            overview=detail.get("overview", ""),
            poster_url=req.poster_url,
            custom_template=end_template if end_template else None
        )
        if result.get("success"):
            new_entry["notified_ended"] = True
            series_monitor._save_series(series_list)
            notification_sent = True
    elif current_status == "Returning Series" and last_ep:
        # 连载中 → 发更新提醒
        episode_info = f"S{last_ep['season_number']:02d}E{last_ep['episode_number']:02d}" if last_ep.get("season_number") else f"E{last_ep['episode_number']:02d}"
        progress = f"{last_ep['episode_number']}/{detail.get('number_of_episodes', 0)}" if detail.get("number_of_episodes") else str(last_ep['episode_number'])

        result = await tg_notifier.send_update_notification(
            series_name=req.title,
            episode_info=episode_info,
            air_date=last_ep.get("air_date", ""),
            progress=progress,
            series_type=detail.get("type", "未知"),
            rating=detail.get("vote_average", 0),
            poster_url=req.poster_url,
            custom_template=update_template if update_template else None
        )
        notification_sent = result.get("success", False)

    return {"success": True, "notification_sent": notification_sent}

@router.delete("/monitor/{tmdb_id}")
async def monitor_delete(tmdb_id: int):
    series_list = series_monitor._load_series()
    new_list = [s for s in series_list if s["tmdb_id"] != tmdb_id]
    if len(new_list) == len(series_list):
        raise HTTPException(status_code=404, detail="未找到该剧集")
    series_monitor._save_series(new_list)
    return {"success": True}

# ==================== 配置接口 ====================

@router.get("/config")
async def get_config():
    cfg = load_tg_config()
    return {
        "tmdb_api_key": bool(cfg.get("tmdb_api_key")),
        "tg_bot_token": bool(cfg.get("tg_bot_token")),
        "tg_chat_id": bool(cfg.get("tg_chat_id")),
        "proxy_url": cfg.get("proxy_url", ""),
        "update_template": cfg.get("update_template", ""),
        "end_template": cfg.get("end_template", ""),
        "check_interval_minutes": cfg.get("check_interval_minutes", 30)
    }

class SaveConfigRequest(BaseModel):
    tmdb_api_key: str = ""
    tg_bot_token: str = ""
    tg_chat_id: str = ""
    proxy_url: str = ""
    update_template: str = ""
    end_template: str = ""
    check_interval_minutes: int = 30

@router.put("/config")
async def save_config(req: SaveConfigRequest):
    os.makedirs(MONITOR_DATA_DIR, exist_ok=True)
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
        except:
            cfg = {}

    if req.tmdb_api_key and req.tmdb_api_key != "__skip__":
        cfg["tmdb_api_key"] = req.tmdb_api_key
    if req.tg_bot_token and req.tg_bot_token != "__skip__":
        cfg["tg_bot_token"] = req.tg_bot_token
    if req.tg_chat_id and req.tg_chat_id != "__skip__":
        cfg["tg_chat_id"] = req.tg_chat_id
    if req.proxy_url and req.proxy_url != "__skip__":
        cfg["proxy_url"] = req.proxy_url
    if req.update_template and req.update_template != "__skip__":
        cfg["update_template"] = req.update_template
    if req.end_template and req.end_template != "__skip__":
        cfg["end_template"] = req.end_template
    cfg["check_interval_minutes"] = max(1, req.check_interval_minutes)

    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    # 如果间隔变了，重启定时任务
    series_monitor.restart_monitor()

    return {"success": True}

@router.post("/config/test")
async def test_config():
    result = await tg_notifier.send_test_message()
    return result

# ==================== 状态/日志接口 ====================

@router.get("/monitor/status")
async def monitor_status():
    return series_monitor.get_status()

@router.get("/monitor/logs")
async def monitor_logs(limit: int = Query(50, ge=1, le=100)):
    return series_monitor.get_logs(limit)

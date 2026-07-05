import json
import os
import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from .config import MONITORED_SERIES_PATH, MONITOR_DATA_DIR, load_tg_config
from . import tmdb_client, tg_notifier

LOG_PATH = os.path.join(MONITOR_DATA_DIR, "monitor_log.json")
MAX_LOG_ENTRIES = 100

MONITOR_TIMEZONE = ZoneInfo(os.getenv("TZ", "Asia/Shanghai") if os.getenv("TZ", "Asia/Shanghai") in {"UTC", "Asia/Shanghai"} else "Asia/Shanghai")

scheduler = AsyncIOScheduler(timezone=MONITOR_TIMEZONE)
_last_check_time = None
_next_check_time = None
_last_notification_time = None

def _load_series():
    if not os.path.exists(MONITORED_SERIES_PATH):
        return []
    try:
        with open(MONITORED_SERIES_PATH, "r") as f:
            data = json.load(f)
            return data.get("series", [])
    except (json.JSONDecodeError, IOError):
        return []

def _save_series(series_list):
    os.makedirs(MONITOR_DATA_DIR, exist_ok=True)
    with open(MONITORED_SERIES_PATH, "w") as f:
        json.dump({"series": series_list}, f, ensure_ascii=False, indent=2)

def _add_log(entry):
    os.makedirs(MONITOR_DATA_DIR, exist_ok=True)
    logs = []
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, IOError):
            logs = []
    logs.insert(0, entry)
    logs = logs[:MAX_LOG_ENTRIES]
    with open(LOG_PATH, "w") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def get_status():
    return {
        "last_check_time": _last_check_time,
        "next_check_time": _next_check_time,
        "monitored_count": len(_load_series()),
        "last_notification_time": _last_notification_time,
        "is_running": scheduler.running
    }

def get_logs(limit: int = 50):
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH, "r") as f:
            logs = json.load(f)
            return logs[:limit]
    except:
        return []

async def check_series():
    """核心检测逻辑"""
    global _last_check_time, _last_notification_time

    series_list = _load_series()
    _last_check_time = datetime.now(timezone.utc).isoformat()

    if not series_list:
        _add_log({"time": _last_check_time, "status": "ok", "message": "监控列表为空，跳过检查"})
        return

    updated_count = 0
    ended_count = 0
    error_count = 0

    for idx, series in enumerate(series_list):
        try:
            detail = await tmdb_client.get_tv_detail(series["tmdb_id"])
            if "error" in detail:
                error_count += 1
                continue

            current_status = detail.get("status", "")
            last_ep = detail.get("last_episode_to_air")
            total_eps = detail.get("number_of_episodes", 0)

            # 获取模板
            cfg = load_tg_config()
            update_template = cfg.get("update_template", "")
            end_template = cfg.get("end_template", "")

            # ---- 更新检测 ----
            if last_ep and last_ep.get("air_date"):
                last_air_date = last_ep["air_date"]
                last_ep_num = last_ep["episode_number"]
                last_season = last_ep["season_number"]

                if last_air_date > series.get("last_episode_air_date", ""):
                    # 有新集
                    episode_info = f"S{last_season:02d}E{last_ep_num:02d}" if last_season else f"E{last_ep_num:02d}"
                    progress = f"{last_ep_num}/{total_eps}" if total_eps else f"{last_ep_num}"
                    air_date = last_air_date

                    result = await tg_notifier.send_update_notification(
                        series_name=series["title"],
                        episode_info=episode_info,
                        air_date=air_date,
                        progress=progress,
                        series_type=detail.get("type", "未知"),
                        rating=detail.get("vote_average", 0),
                        poster_url=series.get("poster_url"),
                        custom_template=update_template if update_template else None
                    )
                    if result.get("success"):
                        updated_count += 1
                        _last_notification_time = datetime.now(timezone.utc).isoformat()

                    # 更新记录
                    series_list[idx]["last_episode_air_date"] = last_air_date
                    series_list[idx]["last_episode_number"] = last_ep_num

            # ---- 完结检测 ----
            if series.get("last_status") == "Returning Series" and current_status == "Ended":
                if not series.get("notified_ended"):
                    result = await tg_notifier.send_end_notification(
                        series_name=series["title"],
                        end_date=detail.get("last_air_date", "未知"),
                        total_episodes=total_eps,
                        series_type=detail.get("type", "未知"),
                        rating=detail.get("vote_average", 0),
                        overview=detail.get("overview", ""),
                        poster_url=series.get("poster_url"),
                        custom_template=end_template if end_template else None
                    )
                    if result.get("success"):
                        ended_count += 1
                        _last_notification_time = datetime.now(timezone.utc).isoformat()
                        series_list[idx]["notified_ended"] = True

            # 更新状态
            series_list[idx]["last_status"] = current_status

        except Exception as e:
            error_count += 1

    _save_series(series_list)

    # 记录日志
    parts = []
    if updated_count:
        parts.append(f"{updated_count} 更新")
    if ended_count:
        parts.append(f"{ended_count} 完结")
    if error_count:
        parts.append(f"{error_count} 错误")

    msg = f"检查完成 · {len(series_list)} 部剧"
    if parts:
        msg += " · " + " · ".join(parts)

    _add_log({
        "time": _last_check_time,
        "status": "ok" if error_count == 0 else "warning",
        "message": msg
    })

def _get_cron_expression():
    """从配置获取 cron 表达式，旧配置自动兼容为分钟间隔"""
    cfg = load_tg_config()
    cron_expr = cfg.get("check_cron", "")
    if cron_expr:
        return cron_expr
    interval = max(1, int(cfg.get("check_interval_minutes", 30) or 30))
    return f"*/{interval} * * * *"

def _build_trigger():
    """构建 cron 触发器，支持标准 5 段 crontab 规则"""
    return CronTrigger.from_crontab(_get_cron_expression(), timezone=MONITOR_TIMEZONE)

def start_monitor():
    """启动定时任务"""
    trigger = _build_trigger()

    scheduler.add_job(
        _run_async_check,
        trigger=trigger,
        id="series_monitor",
        replace_existing=True
    )
    scheduler.start()

def _run_async_check():
    """在调度器中运行异步检查"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(check_series())
    finally:
        loop.close()

def restart_monitor():
    """重启定时任务（配置变更后调用）"""
    if scheduler.running:
        scheduler.reschedule_job(
            "series_monitor",
            trigger=_build_trigger()
        )

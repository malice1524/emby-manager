import httpx
import asyncio

TG_API_BASE = "https://api.telegram.org/bot"

DEFAULT_UPDATE_TEMPLATE = """📺 剧集更新提醒

{series_name} {episode_info} 已更新 🆕"""

DEFAULT_END_TEMPLATE = """🎬 剧集完结通知

{series_name} 已完结 🎉

完结日期：{end_date}
总集数：{total_episodes} 集
类型：{type}
评分：{rating}

简介：
{overview}"""

ALLOWED_UPDATE_VARS = {
    "update_title", "series_name", "episode_info", "air_date", "air_time", "progress", "type", "rating",
    "episode_name", "episode_overview", "episode_rating", "runtime", "episode_still_url"
}
ALLOWED_END_VARS = {"end_title", "series_name", "end_date", "total_episodes", "type", "rating", "overview"}

def _get_config():
    from .config import load_tg_config
    return load_tg_config()

def validate_template(template: str, template_type: str):
    """校验模板中使用的变量是否合法，返回未知变量列表"""
    allowed = ALLOWED_UPDATE_VARS if template_type == "update" else ALLOWED_END_VARS
    import re
    found = set(re.findall(r'\{(\w+)\}', template))
    unknown = found - allowed
    return list(unknown)

async def _send_message(text: str, chat_id: str = None, bot_token: str = None, poster_url: str = None):
    """发送 TG 消息，支持带图片"""
    cfg = _get_config()
    token = bot_token or cfg.get("tg_bot_token", "")
    cid = chat_id or cfg.get("tg_chat_id", "")

    if not token or not cid:
        return {"success": False, "error": "TG 配置不完整"}

    try:
        from .config import get_http_client
        async with get_http_client() as client:
            if poster_url:
                resp = await client.post(
                    f"{TG_API_BASE}{token}/sendPhoto",
                    data={"chat_id": cid, "photo": poster_url, "caption": text, "parse_mode": "HTML"}
                )
                # 如果发图片失败（比如海报URL过期），回退到纯文本
                if resp.status_code != 200:
                    resp = await client.post(
                        f"{TG_API_BASE}{token}/sendMessage",
                        data={"chat_id": cid, "text": text, "parse_mode": "HTML"}
                    )
            else:
                resp = await client.post(
                    f"{TG_API_BASE}{token}/sendMessage",
                    data={"chat_id": cid, "text": text, "parse_mode": "HTML"}
                )
            if resp.status_code == 200:
                return {"success": True}
            else:
                err = resp.json().get("description", "未知错误")
                return {"success": False, "error": err}
    except httpx.TimeoutException:
        return {"success": False, "error": "连接 TG 超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def send_test_message():
    """发送测试消息"""
    text = "🔔 测试通知\n\n如果你收到这条消息，说明 TG 配置正确，通知功能正常工作！\n\n#EmbyManager"
    return await _send_message(text)

async def send_update_notification(series_name: str, episode_info: str, air_date: str,
                                    progress: str, series_type: str, rating: float,
                                    poster_url: str = None, custom_template: str = None,
                                    episode_name: str = "", air_time: str = "",
                                    episode_rating: float = 0, runtime: int = 0,
                                    episode_overview: str = "", episode_still_url: str = ""):
    """发送更新提醒，支持 TMDB 单集详情与 TVmaze 精确播出时间"""
    values = {
        "update_title": "📺 剧集更新提醒",
        "series_name": series_name,
        "episode_info": episode_info,
        "air_date": air_date,
        "air_time": air_time,
        "progress": progress,
        "type": series_type,
        "rating": f"⭐ {rating}" if rating else "暂无",
        "episode_name": episode_name or "",
        "episode_overview": episode_overview or "",
        "episode_rating": f"⭐ {episode_rating}" if episode_rating else "",
        "runtime": runtime or "",
        "episode_still_url": episode_still_url or "",
        "poster_url": poster_url or "",
    }

    if custom_template:
        text = custom_template.format(**values)
    else:
        lines = [DEFAULT_UPDATE_TEMPLATE.format(**values), ""]
        if episode_name:
            lines.append(f"标题：{episode_name}")
        if air_time:
            lines.append(f"播出时间：{air_time}")
        else:
            lines.append(f"播出日期：{air_date}")
        lines.extend([
            f"当前进度：{progress} 集",
            f"类型：{series_type}",
            f"剧集评分：{values['rating']}",
        ])
        if episode_rating:
            lines.append(f"单集评分：{values['episode_rating']}")
        if runtime:
            lines.append(f"片长：{runtime} 分钟")
        if episode_overview:
            lines.extend(["", "本集简介：", episode_overview])
        text = "\n".join(lines)

    return await _send_message(text, poster_url=episode_still_url or poster_url)

async def send_end_notification(series_name: str, end_date: str, total_episodes: int,
                                 series_type: str, rating: float, overview: str,
                                 poster_url: str = None, custom_template: str = None):
    """发送完结提醒，简介只显示前4行"""
    # 截断简介为前4行
    if overview:
        lines = overview.split("\n")
        overview = "\n".join(lines[:4])
        if len(lines) > 4:
            overview += "\n..."

    template = custom_template or DEFAULT_END_TEMPLATE
    text = template.format(
        end_title="🎬 剧集完结通知",
        series_name=series_name,
        end_date=end_date,
        total_episodes=total_episodes,
        type=series_type,
        rating=f"⭐ {rating}" if rating else "暂无",
        overview=overview,
        poster_url=poster_url or ""
    )
    return await _send_message(text, poster_url=poster_url)

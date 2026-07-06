import asyncio
import json
from datetime import datetime, timedelta

from backend.app import series_monitor


def test_check_series_notifies_for_next_episode_airing_today(tmp_path, monkeypatch):
    """TMDB may keep today's episode in next_episode_to_air until after airing time.

    The monitor should not wait until TMDB moves it to last_episode_to_air on the next day.
    """
    data_path = tmp_path / "monitored_series.json"
    log_path = tmp_path / "monitor_log.json"
    today = datetime.now(series_monitor.MONITOR_TIMEZONE).date()
    yesterday = today - timedelta(days=1)

    data_path.write_text(
        json.dumps(
            {
                "series": [
                    {
                        "tmdb_id": 123,
                        "title": "今天更新的剧",
                        "poster_url": "https://example.com/poster.jpg",
                        "last_status": "Returning Series",
                        "last_episode_air_date": yesterday.isoformat(),
                        "last_episode_number": 7,
                        "notified_ended": False,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(series_monitor, "MONITORED_SERIES_PATH", str(data_path))
    monkeypatch.setattr(series_monitor, "LOG_PATH", str(log_path))
    monkeypatch.setattr(series_monitor, "MONITOR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(series_monitor, "load_tg_config", lambda: {"update_template": "", "end_template": ""})

    async def fake_get_tv_detail(tmdb_id):
        assert tmdb_id == 123
        return {
            "status": "Returning Series",
            "type": "动画",
            "vote_average": 8.6,
            "number_of_episodes": 12,
            "last_air_date": yesterday.isoformat(),
            "last_episode_to_air": {
                "air_date": yesterday.isoformat(),
                "season_number": 1,
                "episode_number": 7,
            },
            "next_episode_to_air": {
                "air_date": today.isoformat(),
                "season_number": 1,
                "episode_number": 8,
            },
        }

    sent = []

    async def fake_send_update_notification(**kwargs):
        sent.append(kwargs)
        return {"success": True}

    monkeypatch.setattr(series_monitor.tmdb_client, "get_tv_detail", fake_get_tv_detail)
    monkeypatch.setattr(series_monitor.tg_notifier, "send_update_notification", fake_send_update_notification)

    asyncio.run(series_monitor.check_series())

    assert len(sent) == 1
    assert sent[0]["episode_info"] == "S01E08"
    assert sent[0]["air_date"] == today.isoformat()

    saved = json.loads(data_path.read_text(encoding="utf-8"))["series"][0]
    assert saved["last_episode_air_date"] == today.isoformat()
    assert saved["last_episode_number"] == 8

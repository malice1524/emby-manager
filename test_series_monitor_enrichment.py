import asyncio
import json
from datetime import datetime, timedelta

from backend.app import series_monitor


def test_check_series_enriches_update_notification(tmp_path, monkeypatch):
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
                        "title": "孤独摇滚！",
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
        return {
            "status": "Returning Series",
            "type": "动画 / 喜剧",
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

    async def fake_get_tv_external_ids(tmdb_id):
        return {"tvdb_id": 321, "imdb_id": "tt7654321"}

    async def fake_get_episode_detail(tmdb_id, season_number, episode_number):
        return {
            "name": "波奇·摇滚",
            "overview": "后藤一里终于站上正式舞台……",
            "still_url": "https://image.tmdb.org/t/p/w500/still.jpg",
            "runtime": 24,
            "vote_average": 8.2,
        }

    async def fake_get_episode_airtime_by_external_ids(tvdb_id=None, imdb_id=None, season_number=None, episode_number=None):
        assert (tvdb_id, imdb_id, season_number, episode_number) == (321, "tt7654321", 1, 8)
        return {"air_time_display": "2026-07-06 23:30 北京时间", "runtime": 24}

    sent = []

    async def fake_send_update_notification(**kwargs):
        sent.append(kwargs)
        return {"success": True}

    monkeypatch.setattr(series_monitor.tmdb_client, "get_tv_detail", fake_get_tv_detail)
    monkeypatch.setattr(series_monitor.tmdb_client, "get_tv_external_ids", fake_get_tv_external_ids)
    monkeypatch.setattr(series_monitor.tmdb_client, "get_episode_detail", fake_get_episode_detail)
    monkeypatch.setattr(series_monitor.tvmaze_client, "get_episode_airtime_by_external_ids", fake_get_episode_airtime_by_external_ids)
    monkeypatch.setattr(series_monitor.tg_notifier, "send_update_notification", fake_send_update_notification)

    asyncio.run(series_monitor.check_series())

    assert len(sent) == 1
    assert sent[0]["episode_name"] == "波奇·摇滚"
    assert sent[0]["air_time"] == "2026-07-06 23:30 北京时间"
    assert sent[0]["episode_rating"] == 8.2
    assert sent[0]["runtime"] == 24
    assert sent[0]["episode_overview"] == "后藤一里终于站上正式舞台……"
    assert sent[0]["episode_still_url"] == "https://image.tmdb.org/t/p/w500/still.jpg"

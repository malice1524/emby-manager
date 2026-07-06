import asyncio

from backend.app import tvmaze_client


def test_format_beijing_airtime_from_airstamp():
    result = tvmaze_client.format_beijing_airtime({"airstamp": "2026-07-06T15:30:00+00:00"})

    assert result == "2026-07-06 23:30 北京时间"


def test_format_beijing_airtime_falls_back_to_airdate():
    result = tvmaze_client.format_beijing_airtime({"airdate": "2026-07-06", "airtime": ""})

    assert result == "2026-07-06"


def test_get_episode_airtime_by_external_ids_uses_tvdb_then_episode(monkeypatch):
    calls = []

    async def fake_lookup_show_by_external_ids(tvdb_id=None, imdb_id=None):
        calls.append(("lookup", tvdb_id, imdb_id))
        return {"id": 456, "name": "Test Show"}

    async def fake_get_episode_airtime(tvmaze_id, season_number, episode_number):
        calls.append(("episode", tvmaze_id, season_number, episode_number))
        return {
            "airdate": "2026-07-06",
            "airtime": "23:30",
            "airstamp": "2026-07-06T15:30:00+00:00",
            "runtime": 24,
            "air_time_display": "2026-07-06 23:30 北京时间",
        }

    monkeypatch.setattr(tvmaze_client, "lookup_show_by_external_ids", fake_lookup_show_by_external_ids)
    monkeypatch.setattr(tvmaze_client, "get_episode_airtime", fake_get_episode_airtime)

    result = asyncio.run(
        tvmaze_client.get_episode_airtime_by_external_ids(
            tvdb_id=12345,
            imdb_id="tt1234567",
            season_number=1,
            episode_number=8,
        )
    )

    assert result["air_time_display"] == "2026-07-06 23:30 北京时间"
    assert calls == [("lookup", 12345, "tt1234567"), ("episode", 456, 1, 8)]

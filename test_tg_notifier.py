import asyncio

from backend.app import tg_notifier


def test_update_notification_includes_enriched_episode_fields(monkeypatch):
    sent = []

    async def fake_send_message(text, poster_url=None):
        sent.append({"text": text, "poster_url": poster_url})
        return {"success": True}

    monkeypatch.setattr(tg_notifier, "_send_message", fake_send_message)

    result = asyncio.run(
        tg_notifier.send_update_notification(
            series_name="孤独摇滚！",
            episode_info="S01E08",
            air_date="2026-07-06",
            progress="8/12",
            series_type="动画 / 喜剧",
            rating=8.6,
            poster_url="https://example.com/poster.jpg",
            episode_name="波奇·摇滚",
            air_time="2026-07-06 23:30 北京时间",
            episode_rating=8.2,
            runtime=24,
            episode_overview="后藤一里终于站上正式舞台……",
            episode_still_url="https://example.com/still.jpg",
        )
    )

    assert result == {"success": True}
    assert sent[0]["poster_url"] == "https://example.com/still.jpg"
    assert "孤独摇滚！ S01E08 已更新" in sent[0]["text"]
    assert "标题：波奇·摇滚" in sent[0]["text"]
    assert "播出时间：2026-07-06 23:30 北京时间" in sent[0]["text"]
    assert "当前进度：8/12 集" in sent[0]["text"]
    assert "剧集评分：⭐ 8.6" in sent[0]["text"]
    assert "单集评分：⭐ 8.2" in sent[0]["text"]
    assert "片长：24 分钟" in sent[0]["text"]
    assert "本集简介：\n后藤一里终于站上正式舞台……" in sent[0]["text"]


def test_update_notification_hides_missing_enriched_fields(monkeypatch):
    sent = []

    async def fake_send_message(text, poster_url=None):
        sent.append(text)
        return {"success": True}

    monkeypatch.setattr(tg_notifier, "_send_message", fake_send_message)

    asyncio.run(
        tg_notifier.send_update_notification(
            series_name="测试剧",
            episode_info="S01E01",
            air_date="2026-07-06",
            progress="1/12",
            series_type="动画",
            rating=0,
        )
    )

    assert "播出日期：2026-07-06" in sent[0]
    assert "标题：" not in sent[0]
    assert "播出时间：" not in sent[0]
    assert "单集评分：" not in sent[0]
    assert "片长：" not in sent[0]
    assert "本集简介：" not in sent[0]

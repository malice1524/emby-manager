import os
from pathlib import Path

os.environ["MONITOR_DATA_DIR"] = "/tmp/emby-monitor-test-nfo"

from fastapi.testclient import TestClient
from backend.app.main import app


def _make_actor_tree(tmp_path: Path):
    root = tmp_path / "strm"
    actor = root / "已整理" / "PornHub" / "Sienna Moore"
    season = actor / "Season 1"
    season.mkdir(parents=True)
    for ep, title in [
        (1, "已有剧集"),
        (2, "新增剧集A"),
        (3, "新增剧集B"),
    ]:
        (season / f"Sienna Moore.S01E{ep:02d}.{title}.strm").write_text("http://example/video", encoding="utf-8")
    (season / "Sienna Moore.S01E01.已有剧集.JPG").write_bytes(b"old-jpg")
    (season / "Sienna Moore.S01E01.已有剧集.nfo").write_text("old-nfo", encoding="utf-8")
    img1 = season / "IMG_1001.JPG"
    img2 = season / "IMG_1002.JPG"
    img1.write_bytes(b"img1")
    img2.write_bytes(b"img2")
    os.utime(img1, (1000, 1000))
    os.utime(img2, (1001, 1001))
    return root, actor, season


def test_nfo_automation_scans_executes_and_writes_tvshow(tmp_path, monkeypatch):
    root, actor, season = _make_actor_tree(tmp_path)
    monkeypatch.setenv("NFO_MEDIA_ROOT", str(root))

    with TestClient(app) as client:
        res = client.post("/api/nfo/automation/scan", json={"actor_dir": str(actor)})
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["actor_name"] == "Sienna Moore"
        assert data["counts"] == {"strm": 3, "images": 1, "nfo": 1, "pending_images": 2}
        assert [item["episode"] for item in data["missing_images"]] == [2, 3]
        assert [item["source"] for item in data["image_plan"]] == ["IMG_1001.JPG", "IMG_1002.JPG"]

        tv = client.post("/api/nfo/automation/tvshow", json={
            "actor_dir": str(actor),
            "title": "Sienna Moore",
            "plot": "简介内容",
            "outline": "简介内容",
            "tmdb_id": "6329873",
            "dateadded": "2026-07-06 18:00:00",
            "overwrite": True,
        })
        assert tv.status_code == 200, tv.text
        tvshow = (actor / "tvshow.nfo").read_text(encoding="utf-8")
        assert "<title>Sienna Moore</title>" in tvshow
        assert "<tmdbid>6329873</tmdbid>" in tvshow
        assert tvshow.index("<plot>") < tvshow.index("<outline>") < tvshow.index("<lockdata>")

        ex = client.post("/api/nfo/automation/execute", json={"actor_dir": str(actor)})
        assert ex.status_code == 200, ex.text
        assert (season / "Sienna Moore.S01E02.新增剧集A.JPG").read_bytes() == b"img1"
        assert (season / "Sienna Moore.S01E03.新增剧集B.JPG").read_bytes() == b"img2"
        e2nfo = (season / "Sienna Moore.S01E02.新增剧集A.nfo").read_text(encoding="utf-8")
        assert "<title>新增剧集A</title>" in e2nfo
        assert "<episode>2</episode>" in e2nfo
        outside = tmp_path / "outside"
        outside.mkdir()
        monkeypatch.setenv("NFO_MEDIA_ROOT", str(root))
        bad = client.post("/api/nfo/automation/scan", json={"actor_dir": str(outside)})
        assert bad.status_code == 400
        assert "媒体根目录" in bad.text

        browse_root = client.get("/api/nfo/automation/browse")
        assert browse_root.status_code == 200, browse_root.text
        root_data = browse_root.json()
        assert root_data["path"] == str(root.resolve())
        assert root_data["parent"] == ""
        assert root_data["media_root"] == str(root.resolve())
        assert [d["name"] for d in root_data["dirs"]] == ["已整理"]

        browse_pornhub = client.get("/api/nfo/automation/browse", params={"path": str(root / "已整理" / "PornHub")})
        assert browse_pornhub.status_code == 200, browse_pornhub.text
        ph_data = browse_pornhub.json()
        assert ph_data["parent"] == str(root / "已整理")
        assert ph_data["dirs"][0]["name"] == "Sienna Moore"
        assert ph_data["dirs"][0]["is_actor_dir"] is True

        bad_browse = client.get("/api/nfo/automation/browse", params={"path": str(outside)})
        assert bad_browse.status_code == 400
        assert "媒体根目录" in bad_browse.text


def test_nfo_automation_refreshes_emby_after_execute(tmp_path, monkeypatch):
    root, actor, _season = _make_actor_tree(tmp_path)
    monkeypatch.setenv("NFO_MEDIA_ROOT", str(root))
    monkeypatch.setenv("EMBY_URL", "http://emby.local:8096")
    monkeypatch.setenv("EMBY_API_KEY", "test-key")
    calls = []

    class FakeResponse:
        status_code = 204
        text = ""

    class FakeAsyncClient:
        def __init__(self, timeout=15):
            self.timeout = timeout
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def post(self, url, headers=None, params=None):
            calls.append((url, headers, params))
            return FakeResponse()

    from backend.app.routers import nfo
    monkeypatch.setattr(nfo.httpx, "AsyncClient", FakeAsyncClient)

    with TestClient(app) as client:
        manual = client.post("/api/nfo/automation/refresh-emby")
        assert manual.status_code == 200, manual.text
        assert manual.json()["ok"] is True

        ex = client.post("/api/nfo/automation/execute", json={"actor_dir": str(actor), "refresh_emby": True})
        assert ex.status_code == 200, ex.text
        logs = ex.json()["logs"]
        assert "刷新Emby媒体库: 已提交" in logs

    assert len(calls) == 2
    assert all(url == "http://emby.local:8096/Library/Refresh" for url, _headers, _params in calls)
    assert all(headers["X-Emby-Token"] == "test-key" for _url, headers, _params in calls)


def test_nfo_automation_refreshes_current_actor_directory_when_emby_root_is_configured(tmp_path, monkeypatch):
    root, actor, _season = _make_actor_tree(tmp_path)
    nfo_root = root / "已整理" / "PornHub"
    monkeypatch.setenv("NFO_MEDIA_ROOT", str(nfo_root))
    monkeypatch.setenv("EMBY_MEDIA_ROOT", "/pron/PornHub")
    monkeypatch.setenv("EMBY_URL", "http://emby.local:8096")
    monkeypatch.setenv("EMBY_API_KEY", "test-key")
    calls = []

    class FakeResponse:
        def __init__(self, status_code=200, data=None, text=""):
            self.status_code = status_code
            self._data = data or {}
            self.text = text
        def json(self):
            return self._data

    class FakeAsyncClient:
        def __init__(self, timeout=15):
            self.timeout = timeout
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def get(self, url, headers=None, params=None):
            calls.append(("GET", url, params))
            assert params["Path"] == "/pron/PornHub/Sienna Moore"
            return FakeResponse(data={"Items": [{"Id": "emby-actor-id", "Name": "Sienna Moore"}]})
        async def post(self, url, headers=None, params=None):
            calls.append(("POST", url, params))
            return FakeResponse(status_code=204)

    from backend.app.routers import nfo
    monkeypatch.setattr(nfo.httpx, "AsyncClient", FakeAsyncClient)

    with TestClient(app) as client:
        ex = client.post("/api/nfo/automation/execute", json={"actor_dir": str(actor), "refresh_emby": True})
        assert ex.status_code == 200, ex.text
        logs = ex.json()["logs"]
        assert "刷新Emby项目: Sienna Moore" in logs

    assert calls == [
        ("GET", "http://emby.local:8096/Items", {"Recursive": "true", "Fields": "Path", "Path": "/pron/PornHub/Sienna Moore"}),
        ("POST", "http://emby.local:8096/Items/emby-actor-id/Refresh", {
            "Recursive": "true",
            "MetadataRefreshMode": "FullRefresh",
            "ImageRefreshMode": "FullRefresh",
            "ReplaceAllMetadata": "false",
            "ReplaceAllImages": "false",
        }),
    ]

    # Covered in the main TestClient session above to avoid restarting the app scheduler twice.
    assert True

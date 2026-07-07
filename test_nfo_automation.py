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


def test_uploaded_episode_images_are_renamed_to_pending_img_files_and_matched(tmp_path, monkeypatch):
    root = tmp_path / "strm"
    actor = root / "已整理" / "PornHub" / "Sienna Moore"
    season = actor / "Season 1"
    season.mkdir(parents=True)
    (season / "Sienna Moore.S01E37.重新上传测试.strm").write_text("http://example/video", encoding="utf-8")
    monkeypatch.setenv("NFO_MEDIA_ROOT", str(root))

    with TestClient(app) as client:
        upload = client.post(
            "/api/nfo/automation/upload-episode-images",
            data={"actor_dir": str(actor)},
            files=[("images", ("cover-from-phone.jpg", b"new-cover", "image/jpeg"))],
        )
        assert upload.status_code == 200, upload.text
        saved = upload.json()["saved"]
        assert len(saved) == 1
        assert saved[0].startswith("IMG_UPLOAD_")
        assert saved[0].endswith(".JPG")
        assert upload.json()["scan"]["image_plan"][0]["source"] == saved[0]
        assert upload.json()["scan"]["image_plan"][0]["target"] == "Sienna Moore.S01E37.重新上传测试.JPG"

        ex = client.post("/api/nfo/automation/execute", json={"actor_dir": str(actor), "refresh_emby": False})
        assert ex.status_code == 200, ex.text
        assert (season / "Sienna Moore.S01E37.重新上传测试.JPG").read_bytes() == b"new-cover"
        assert (season / "Sienna Moore.S01E37.重新上传测试.nfo").exists()


def test_uploaded_episode_images_take_priority_over_old_pending_images(tmp_path, monkeypatch):
    root = tmp_path / "strm"
    actor = root / "已整理" / "PornHub" / "Sienna Moore"
    season = actor / "Season 1"
    season.mkdir(parents=True)
    (season / "Sienna Moore.S01E37.重新上传测试.strm").write_text("http://example/video", encoding="utf-8")
    old = season / "IMG_0001.JPG"
    old.write_bytes(b"old-leftover")
    os.utime(old, (1, 1))
    monkeypatch.setenv("NFO_MEDIA_ROOT", str(root))

    with TestClient(app) as client:
        upload = client.post(
            "/api/nfo/automation/upload-episode-images",
            data={"actor_dir": str(actor)},
            files=[("images", ("cover-from-phone.jpg", b"new-cover", "image/jpeg"))],
        )
        assert upload.status_code == 200, upload.text
        assert upload.json()["scan"]["image_plan"][0]["source"].startswith("IMG_UPLOAD_")
        ex = client.post("/api/nfo/automation/execute", json={"actor_dir": str(actor), "refresh_emby": False})
        assert ex.status_code == 200, ex.text
        assert (season / "Sienna Moore.S01E37.重新上传测试.JPG").read_bytes() == b"new-cover"
        assert old.exists()



def test_pornhub_metadata_preview_returns_only_chinese_tags(monkeypatch):
    html = """
    <html><head>
      <script type="application/ld+json">
      {"uploadDate":"2024-06-01T12:34:56+00:00","keywords":"Chinese,国产,巨乳,Asian,4K中文"}
      </script>
    </head></html>
    """

    class FakeResponse:
        status_code = 200
        text = html

    class FakeClient:
        def __init__(self, timeout=20, follow_redirects=True, headers=None):
            self.timeout = timeout
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def get(self, url):
            return FakeResponse()

    from backend.app.routers import nfo
    monkeypatch.setattr(nfo, "get_http_client", lambda: FakeClient())

    with TestClient(app) as client:
        res = client.post('/api/nfo/automation/pornhub-metadata/preview', json={
            'url': 'https://cn.pornhub.com/view_video.php?viewkey=test'
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert data['published_at'] == '2024-06-01'
        assert data['tags'] == ['国产', '巨乳', '4K中文']
        assert data['all_tag_count'] == 5
        assert data['chinese_tag_count'] == 3


def test_pornhub_metadata_preview_extracts_chinese_search_link_tags(monkeypatch):
    html = """
    <html><head>
      <script type="application/ld+json">
      {"uploadDate":"2024-06-01T12:34:56+00:00","keywords":"Chinese,Asian"}
      </script>
    </head><body>
      <a href="/video/search?search=%E5%9B%BD%E4%BA%A7">国产</a>
      <a href="/video/search?search=%E5%B7%A8%E4%B9%B3">巨乳</a>
      <a href="/video/search?search=Asian">Asian</a>
    </body></html>
    """

    class FakeResponse:
        status_code = 200
        text = html

    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def get(self, url, **kwargs):
            return FakeResponse()

    from backend.app.routers import nfo
    monkeypatch.setattr(nfo, "get_http_client", lambda: FakeClient())

    with TestClient(app) as client:
        res = client.post('/api/nfo/automation/pornhub-metadata/preview', json={
            'url': 'https://cn.pornhub.com/view_video.php?viewkey=test'
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert data['published_at'] == '2024-06-01'
        assert data['tags'] == ['国产', '巨乳']
        assert data['chinese_tag_count'] == 2


    class FakeClient:
        def __init__(self, timeout=20, follow_redirects=True, headers=None):
            self.timeout = timeout
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def get(self, url):
            raise Exception('connect failed')

    from backend.app.routers import nfo
    monkeypatch.setattr(nfo, "get_http_client", lambda: FakeClient())

    with TestClient(app) as client:
        res = client.post('/api/nfo/automation/pornhub-metadata/preview', json={
            'url': 'https://cn.pornhub.com/view_video.php?viewkey=test'
        })
        assert res.status_code == 502, res.text
        assert 'PornHub 页面抓取失败' in res.json()['detail']


def test_pornhub_metadata_write_merges_selected_chinese_tags(tmp_path, monkeypatch):
    root, actor, season = _make_actor_tree(tmp_path)
    monkeypatch.setenv('NFO_MEDIA_ROOT', str(root))
    nfo_path = season / 'Sienna Moore.S01E02.新增剧集A.nfo'
    nfo_path.write_text(
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
        '<episodedetails>\n'
        '  <title>新增剧集A</title>\n'
        '  <season>1</season>\n'
        '  <episode>2</episode>\n'
        '  <tag>旧标签</tag>\n'
        '</episodedetails>\n',
        encoding='utf-8'
    )

    with TestClient(app) as client:
        res = client.post('/api/nfo/automation/pornhub-metadata/write', json={
            'actor_dir': str(actor),
            'strm_filename': 'Sienna Moore.S01E02.新增剧集A.strm',
            'published_at': '2024-06-01',
            'tags': ['国产', '巨乳', 'Asian', '4K中文'],
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert data['tags'] == ['国产', '巨乳', '4K中文']
        assert data['backup'].startswith('Sienna Moore.S01E02.新增剧集A.nfo.bak.')

    written = nfo_path.read_text(encoding='utf-8')
    assert '<title>新增剧集A</title>' in written
    assert '<season>1</season>' in written
    assert '<episode>2</episode>' in written
    assert '<aired>2024-06-01</aired>' in written
    assert '<premiered>2024-06-01</premiered>' in written
    assert '<tag>国产</tag>' in written
    assert '<tag>巨乳</tag>' in written
    assert '<tag>4K中文</tag>' in written
    assert '<tag>Asian</tag>' not in written
    assert '<tag>旧标签</tag>' not in written
    backups = list(season.glob('Sienna Moore.S01E02.新增剧集A.nfo.bak.*'))
    assert backups

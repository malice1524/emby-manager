from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import file_organizer
from backend.app.main import app


def setup_roots(monkeypatch, tmp_path):
    cloud = tmp_path / "CloudDrive115"
    strm = tmp_path / "strm"
    data = tmp_path / "data"
    cloud.mkdir()
    strm.mkdir()
    data.mkdir()
    monkeypatch.setenv("MONITOR_DATA_DIR", str(data))
    monkeypatch.setattr(file_organizer, "ROOTS", {"cloud115": cloud, "strm": strm})
    monkeypatch.setattr(file_organizer, "DATA_ROOT", data)
    return cloud, strm, data


def touch(path: Path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_settings_api_does_not_return_secret(monkeypatch, tmp_path):
    setup_roots(monkeypatch, tmp_path)
    monkeypatch.setenv("MONITOR_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    put = client.put("/api/settings/deepseek", json={"api_key": "secret", "model": "deepseek-chat"})
    assert put.status_code == 200
    assert "secret" not in put.text

    get = client.get("/api/settings/deepseek")
    assert get.status_code == 200
    data = get.json()
    assert data["api_key_configured"] is True
    assert data["api_key_source"] == "saved"
    assert "api_key" not in data
    assert "secret" not in get.text


def test_browse_rejects_outside_root(monkeypatch, tmp_path):
    cloud, _, _ = setup_roots(monkeypatch, tmp_path)
    client = TestClient(app)

    ok = client.get("/api/file-organizer/browse", params={"root": "cloud115", "path": str(cloud)})
    assert ok.status_code == 200

    bad = client.get("/api/file-organizer/browse", params={"root": "cloud115", "path": str(tmp_path)})
    assert bad.status_code == 400


def test_scan_and_video_precheck(monkeypatch, tmp_path):
    cloud, _, _ = setup_roots(monkeypatch, tmp_path)
    src = touch(cloud / "src" / "2.mkv")
    target = cloud / "target" / "Actor.S01E01.Title.mkv"
    client = TestClient(app)

    scan = client.post("/api/file-organizer/scan", json={"source_dir": str(src.parent), "recursive": False, "sort": "name"})
    assert scan.status_code == 200
    assert scan.json()["items"][0]["name"] == "2.mkv"

    pre = client.post("/api/file-organizer/precheck", json={"confirmed": True, "items": [{"id": "1", "source_path": str(src), "target_path": str(target)}]})
    assert pre.status_code == 200
    assert pre.json()["ok"] is True

    touch(target)
    conflict = client.post("/api/file-organizer/precheck", json={"confirmed": True, "items": [{"id": "1", "source_path": str(src), "target_path": str(target)}]})
    assert conflict.status_code == 200
    assert conflict.json()["ok"] is False
    assert "已存在" in conflict.json()["items"][0]["error"]


def test_metadata_precheck_reports_overwrite(monkeypatch, tmp_path):
    cloud, strm, _ = setup_roots(monkeypatch, tmp_path)
    source = strm / "Actor"
    target = cloud / "Actor"
    touch(source / "tvshow.nfo", "new")
    touch(source / "Season 1" / "a.jpg", "jpg")
    touch(source / "Season 1" / "a.strm", "strm")
    touch(target / "tvshow.nfo", "old")
    client = TestClient(app)

    pre = client.post("/api/file-organizer/metadata/precheck", json={"source_dir": str(source), "target_dir": str(target), "confirmed": True})
    assert pre.status_code == 200
    data = pre.json()
    assert [item["relative_path"] for item in data["items"]] == ["Season 1/a.jpg", "tvshow.nfo"]
    assert any(item["will_overwrite"] for item in data["items"] if item["relative_path"] == "tvshow.nfo")

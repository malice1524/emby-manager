import json
import os
import tempfile

os.environ["MONITOR_DATA_DIR"] = tempfile.mkdtemp(prefix="emby-monitor-")

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.routers import dashboard


def test_dashboard_metube_hides_non_video_upload_progress(tmp_path, monkeypatch):
    progress = tmp_path / "upload-progress.json"
    state = tmp_path / "upload-state.json"
    progress.write_text(json.dumps({
        "filename": "cover.jpg",
        "status": "upload_returned",
        "uploaded_bytes": 10,
        "total_bytes": 10,
        "percent": 100.0,
        "updated_at": "2026-07-10 21:57:22",
        "error": "",
    }), encoding="utf-8")
    state.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(dashboard, "METUBE_PROGRESS_FILE", progress)
    monkeypatch.setattr(dashboard, "METUBE_STATE_FILE", state)

    async def fake_history():
        return {"done": [], "queue": [], "pending": []}

    monkeypatch.setattr(dashboard, "_fetch_metube_history", fake_history)

    with TestClient(app) as client:
        response = client.get("/api/dashboard/metube")
    assert response.status_code == 200
    data = response.json()
    assert data["progress"] == {}


def test_dashboard_metube_status_reads_progress_state_and_redacts_errors(tmp_path, monkeypatch):
    progress = tmp_path / "upload-progress.json"
    state = tmp_path / "upload-state.json"
    progress.write_text(json.dumps({
        "filename": "movie.mp4",
        "status": "uploading",
        "uploaded_bytes": 50,
        "total_bytes": 100,
        "percent": 50.0,
        "updated_at": "2026-07-10 21:57:22",
        "error": "",
    }), encoding="utf-8")
    state.write_text(json.dumps({
        "movie.mp4": {"status": "upload_failed", "size": 1048576, "updated_at": "2026-07-10 21:58:00", "error": "MultipartUploadAbort: {'user_key': 'secret-key', 'token': 'secret-token'}"},
        "done.mp4": {"status": "deleted_local_after_confirm", "size": 1, "updated_at": "2026-07-10 21:00:00", "error": ""},
    }), encoding="utf-8")

    monkeypatch.setattr(dashboard, "METUBE_PROGRESS_FILE", progress)
    monkeypatch.setattr(dashboard, "METUBE_STATE_FILE", state)

    async def fake_history():
        return {
            "done": [{"status": "finished"}],
            "queue": [{"status": "downloading"}, {"status": "pending"}, {"status": "preparing"}],
            "pending": [],
        }

    monkeypatch.setattr(dashboard, "_fetch_metube_history", fake_history)

    with TestClient(app) as client:
        response = client.get("/api/dashboard/metube")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["progress"]["percent"] == 50.0
    assert data["metube"] == {"finished": 1, "downloading": 1, "pending": 1, "preparing": 1, "failed": 0, "total": 4}
    assert data["uploader"]["statuses"]["upload_failed"] == 1
    assert data["failed"][0]["filename"] == "movie.mp4"
    assert data["failed"][0]["size_text"] == "1.00 MB"
    assert "secret-key" not in data["failed"][0]["error"]
    assert "[redacted]" in data["failed"][0]["error"]

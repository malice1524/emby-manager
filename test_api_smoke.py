import os
import tempfile

os.environ["MONITOR_DATA_DIR"] = tempfile.mkdtemp(prefix="emby-monitor-")

from fastapi.testclient import TestClient
from backend.app.main import app


def test_api_smoke_and_spa_contains_monitor_and_nfo():
    with TestClient(app) as client:
        for path in [
            "/api/health",
            "/api/monitor/list",
            "/api/monitor/status",
            "/api/monitor/logs",
            "/api/config",
        ]:
            response = client.get(path)
            assert response.status_code == 200, (path, response.status_code, response.text[:200])

        response = client.get("/")
        assert response.status_code == 200
        assert "完结监控" in response.text
        assert "NFO 自动化" in response.text
        assert "浏览选择演员目录" in response.text
        assert "placeholder=\"/vol1/1000/docker/strm" not in response.text

        response = client.put("/api/config", json={"check_cron": "*/15 * * * *"})
        assert response.status_code == 200, response.text
        response = client.get("/api/config")
        assert response.status_code == 200
        assert response.json()["check_cron"] == "*/15 * * * *"

        response = client.put("/api/config", json={"check_cron": "bad cron"})
        assert response.status_code == 400
        assert "Cron 规则无效" in response.text

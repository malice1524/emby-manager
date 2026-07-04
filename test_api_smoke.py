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
        assert "NFO 生成" in response.text

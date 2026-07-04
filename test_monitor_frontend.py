from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_static():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")


def read_frontend():
    return (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")


def assert_monitor_frontend(html: str):
    assert 'href="#/monitor"' in html
    assert '完结监控' in html
    assert 'const Monitor = {' in html
    assert "{path:'/monitor',component:Monitor}" in html
    assert "fetchJSON('/tmdb/search?q='" in html
    assert "fetchJSON('/monitor/add'" in html
    assert "fetchJSON('/monitor/list'" in html
    assert "fetchJSON('/config'" in html
    assert "fetchJSON('/monitor/status'" in html
    assert "fetchJSON('/monitor/logs?limit=50'" in html
    assert 'class="monitor-search-results"' in html
    assert 'class="monitor-search-result-item"' in html
    assert 'class="monitor-search-overview"' in html
    assert '-webkit-line-clamp:2' in html
    assert 'overflow-wrap:anywhere' in html
    assert 'const NfoGenerator = {' in html
    assert "{path:'/nfo',component:NfoGenerator}" in html


def test_static_frontend_has_monitor_and_nfo():
    assert_monitor_frontend(read_static())


def test_frontend_copy_matches_static_and_has_monitor():
    static_html = read_static()
    frontend_html = read_frontend()
    assert frontend_html == static_html
    assert_monitor_frontend(frontend_html)

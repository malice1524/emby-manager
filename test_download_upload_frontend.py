from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_static():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")


def read_frontend():
    return (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")


def assert_download_upload_frontend(html: str):
    assert 'href="#/download-upload"' in html
    assert '下载上传' in html
    assert 'const DownloadUpload = {' in html
    assert "{path:'/download-upload',component:DownloadUpload}" in html
    assert "fetchJSON('/dashboard/metube')" in html
    assert 'class="du-progress-card"' in html
    assert 'class="du-progress-fill"' in html
    assert '上传失败' in html
    assert '失败项' in html
    assert 'formatBytes(bytes)' in html
    assert 'statusLabel(status)' in html
    assert "fetchJSON('/settings/metube')" in html
    assert "fetchJSON('/settings/metube',{method:'PUT'" in html
    assert 'PornHub 查漏补缺' in html
    assert "fetchJSON('/pornhub-gap/check'" in html
    assert "fetchJSON('/pornhub-gap/fix'" in html
    assert '选择 115 目录' in html
    assert 'gapBrowsePath' in html
    assert 'MeTube 地址' in html
    assert 'class="du-home-card fade-in"' in html
    assert "goDownloadUpload" in html
    assert "homeProgressPercent" in html
    assert "homeProgressLabel" in html


def test_static_has_download_upload_page():
    assert_download_upload_frontend(read_static())


def test_frontend_matches_static_and_has_download_upload_page():
    static_html = read_static()
    frontend_html = read_frontend()
    assert frontend_html == static_html
    assert_download_upload_frontend(frontend_html)

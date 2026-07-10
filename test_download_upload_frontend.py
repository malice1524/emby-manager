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


def test_static_has_download_upload_page():
    assert_download_upload_frontend(read_static())


def test_frontend_matches_static_and_has_download_upload_page():
    static_html = read_static()
    frontend_html = read_frontend()
    assert frontend_html == static_html
    assert_download_upload_frontend(frontend_html)

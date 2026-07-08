from pathlib import Path

ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend" / "index.html"
STATIC = ROOT / "static" / "index.html"


def read_pair():
    return FRONTEND.read_text(encoding="utf-8"), STATIC.read_text(encoding="utf-8")


def test_settings_sidebar_route_and_api_markers_exist():
    frontend, static = read_pair()
    for html in (frontend, static):
        assert '#/settings' in html
        assert 'DeepSeek API Key' in html
        assert '测试翻译' in html
        assert '/settings/deepseek' in html
        assert '/settings/deepseek/test-translation' in html
        assert "{path:'/settings',component:Settings}" in html
    assert frontend.count("#/settings") == static.count("#/settings")


def test_file_organizer_sidebar_route_and_api_markers_exist():
    frontend, static = read_pair()
    for html in (frontend, static):
        assert '#/file-organizer' in html
        assert '文件整理' in html
        assert '选择 115 源文件夹' in html
        assert '扫描视频' in html
        assert 'DeepSeek 翻译标题' in html
        assert '预检查' in html
        assert '执行移动' in html
        assert '元数据复制到 115' in html
        assert '/file-organizer/scan' in html
        assert '/file-organizer/metadata/precheck' in html
        assert "{path:'/file-organizer',component:FileOrganizer}" in html
    assert frontend.count("#/file-organizer") == static.count("#/file-organizer")


def test_settings_link_is_after_file_organizer_link():
    frontend, static = read_pair()
    for html in (frontend, static):
        assert html.index('#/file-organizer') < html.index('#/settings')

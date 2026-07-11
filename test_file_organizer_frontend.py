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
        assert "{path:'/settings',component:Settings}" in html
    assert frontend.count("#/settings") == static.count("#/settings")


def test_file_organizer_sidebar_route_and_api_markers_exist():
    frontend, static = read_pair()
    for html in (frontend, static):
        assert '#/media-organizer' in html
        assert '媒体整理' in html
        assert '生成 tvshow.nfo / poster.jpg / fanart.jpg / logo.png' in html
        assert '选择源文件夹' in html
        assert '选择目标文件夹' in html
        assert '选择目录' in html
        assert '生成 tvshow.nfo' in html
        assert 'poster.jpg' in html
        assert 'fanart.jpg' in html
        assert 'logo.png' in html
        assert '/media-organizer/browse' in html
        assert '/media-organizer/suggest-next-episode' in html
        assert 'suggestNextEpisode' in html
        assert 'episodeHint' in html
        assert 'actorNameFromPath' in html
        assert '/strm' in html
        assert 'browsePicker' in html
        assert 'fo-path-row' in html
        assert 'fo-episode-grid' in html
        assert 'fo-action-row' in html
        assert '.file-organizer-page .el-button' in html
        assert '.file-organizer-page .el-select' in html
        assert '.file-organizer-page .el-checkbox__label' in html
        assert '.file-organizer-page .el-tag' in html
        assert '.file-organizer-page .fo-result-pre' in html
        assert 'class="fo-result-pre"' in html
        assert '@media (max-width: 640px)' in html
        assert '扫描视频' in html
        assert 'DeepSeek 翻译标题' in html
        assert '调整顺序' in html
        assert 'moveItem' in html
        assert '集数预览' in html
        assert '预检查' in html
        assert '执行移动' in html
        assert '扫描视频 / 翻译标题 / 生成每集 NFO / 移动到目标目录' in html
        assert '/media-organizer/scan' in html
        assert "file-organizer-page" in html
        assert ".file-organizer-page .el-collapse" in html
        assert "{path:'/media-organizer',component:FileOrganizer}" in html
        assert '/media-organizer/tvshow' in html
        assert '/media-organizer/upload-artwork' in html
        assert 'opts.body instanceof FormData' in html
        assert 'Array.isArray(detail)' in html
        assert "await this.loadActorInfo(this.mediaDir)" in html
        assert '/media-organizer/actor-info' in html
        assert 'loadActorInfo' in html
        assert 'applyActorInfo' in html
        assert 'mediaInfo.tvshow_exists' in html
        assert '已读取 tvshow.nfo' in html
    assert frontend.count("#/media-organizer") == static.count("#/media-organizer")


def test_file_organizer_has_published_date_artwork_and_nfo_controls():
    frontend, static = read_pair()
    for html in (frontend, static):
        assert 'label="按发布时间从早到晚" value="published_date"' in html
        assert 'prop="published_date" label="发布时间"' in html
        assert 'label="图片"' in html
        assert '生成每集 NFO' in html
        assert 'generateNfo' in html
        assert 'target_artwork_path' in html
        assert 'target_nfo_path' in html
        assert "plot:i.title||''" in html
        assert 'published_date' in html


def test_settings_link_is_after_file_organizer_link():
    frontend, static = read_pair()
    for html in (frontend, static):
        assert html.index('#/media-organizer') < html.index('#/settings')

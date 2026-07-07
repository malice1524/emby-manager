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
    assert 'class="monitor-search-results-header"' in html
    assert '@click="clearSearchResults"' in html
    assert 'onSearchInput()' in html
    assert 'class="monitor-search-result-item"' in html
    assert 'class="monitor-search-overview"' in html
    assert '-webkit-line-clamp:2' in html
    assert 'overflow-wrap:anywhere' in html
    assert 'check_cron' in html
    assert '检查 Cron 规则' in html
    assert 'setTimeout(()=>this.loadList({background:true}),2000)' in html
    assert '更新通知模板' not in html
    assert '完结通知模板' not in html
    assert '检查间隔（分钟）' not in html
    assert 'class="monitor-refresh-btn"' in html
    assert 'class="monitor-refresh-icon"' in html
    assert ':class="{spinning:refreshing}"' in html
    assert 'aria-label="刷新监控列表"' in html
    assert "name==='欧美电影'" in html
    assert 'dashboard-library-filter' in html
    assert 'libCountText(lib)' in html
    assert "return '点击查看全部'" in html
    assert 'grid-template-columns: repeat(5, 1fr)' in html
    assert 'grid-template-columns: repeat(4, 1fr)' in html
    assert 'class="library-items-dialog"' in html
    assert 'class="library-items-panel"' in html
    assert 'class="library-items-scroll"' in html
    assert 'class="library-pagination"' in html
    assert 'layout="total, prev, pager, next, jumper"' in html
    assert ':pager-count="isMobile ? 5 : 7"' in html
    assert ':page-size="pageSize"' in html
    assert 'top="48px"' in html
    assert '.el-overlay-dialog:has(.library-items-dialog) { overflow: hidden; }' in html
    assert 'position: fixed !important; top: 48px !important; bottom: 48px !important;' in html
    assert '.library-items-dialog .el-dialog__body { height: calc(100% - 56px); padding: 12px 16px 14px; overflow: hidden; }' in html
    assert '.library-items-panel { display: flex; flex-direction: column; height: 100%; min-height: 0; }' in html
    assert '.library-items-scroll { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding-right: 4px; }' in html
    assert '.library-items-dialog .poster-grid { grid-template-columns: repeat(6, 1fr); gap: 8px; }' in html
    assert 'max-height: 165px' not in html
    assert "calc(100vw - 320px)" in html
    assert 'margin-left: calc(240px +' in html
    assert 'translateX(calc(-50% + 120px))' not in html
    assert '个路径' not in html
    assert "ElementPlus.ElMessage.error(e.message||'删除失败')" in html
    assert 'class="nfo-image-plan-row"' in html
    assert 'class="nfo-image-plan-source"' in html
    assert 'class="nfo-image-plan-target"' in html
    assert '.nfo-image-plan-row { display:flex; align-items:center; gap:8px; padding:10px; border:1px solid var(--glass-border); border-radius:10px; background:rgba(255,255,255,0.03); font-size:13px; min-width:0; max-width:100%; overflow:hidden; }' in html
    assert '.nfo-image-plan-source, .nfo-image-plan-target { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }' in html
    assert '.nfo-image-plan-source { flex:0 1 42%; }' in html
    assert '.nfo-image-plan-target { flex:1 1 0; }' in html
    assert 'this.tv.tags = (data.tags || []).slice(0, 6);' in html
    assert 'class="nfo-pornhub-fields"' in html
    assert 'class="nfo-published-scroll"' in html
    assert 'filter(ep => !ep.has_published_date)' in html
    assert '所有剧集都已写入发布时间' in html
    assert 'class="nfo-published-row"' in html
    assert 'batchWritePublished' in html
    assert '/api/nfo/automation/pornhub-published/batch-write' in html
    assert '.nfo-pornhub-fields { display:grid; grid-template-columns:minmax(0,2fr) minmax(120px,auto); gap:10px; margin-bottom:10px; min-width:0; max-width:100%; overflow:hidden; }' in html
    assert '.nfo-published-scroll { max-height:360px; overflow-y:auto;' in html
    assert '@media (max-width: 640px) { .nfo-pornhub-fields { grid-template-columns:1fr; } }' in html
    assert 'applyTvshowData(this.scanData.tvshow)' in html
    assert 'applyTvshowData(data)' in html
    assert 'this.tv.tags = Array.isArray(data.tags) ? data.tags.slice() : [];' in html
    assert 'displayTvTags()' in html
    assert 'addCustomTvTags' in html
    assert 'tagTool: { url:\'\', custom:\'\', preview:null, previewing:false }' in html
    assert '手动填写中文标签' in html
    assert 'refreshActorMetadataAfterChange' in html
    assert '元数据已改动，已自动刷新当前 Emby 演员目录' in html
    assert 'class="nfo-missing-lists"' in html
    assert '缺图片 {{scanData.missing_images.length}}' in html
    assert '缺 NFO {{scanData.missing_nfo.length}}' in html
    assert '.nfo-missing-scroll { max-height:180px; overflow-y:auto;' in html
    assert 'tagTool.preview ? `' not in html
    assert 'const NfoGenerator = {' in html
    assert "{path:'/nfo',component:NfoGenerator}" in html


def test_static_frontend_has_monitor_and_nfo():
    assert_monitor_frontend(read_static())


def test_frontend_copy_matches_static_and_has_monitor():
    static_html = read_static()
    frontend_html = read_frontend()
    assert frontend_html == static_html
    assert_monitor_frontend(frontend_html)

# AI_CONTEXT.md — Emby Manager 高频上下文 ⭐⭐⭐⭐⭐

> 用途：每次开启新的 AI 会话优先发送/读取。目标是让 AI 快速知道项目规则、当前状态、常用命令和容易踩坑的地方。

## 项目定位

Emby Manager 是一个 Emby 媒体服务器 Web 管理面板，提供仪表盘、用户管理、媒体库浏览、完结监控、NFO 自动化等能力。

- 仓库：`malice1524/emby-manager`
- 本地常用路径：`/var/minis/workspace/emby-manager`
- Docker 镜像：`1524566636/emby-manager:latest`
- 部署方式：单 Docker 容器，`main` 分支推送后 DockerHub 自动构建 latest

## 技术栈

- 后端：Python 3.12 + FastAPI + httpx + APScheduler
- 前端：Vue 3 + Vue Router + Element Plus，单文件 SPA
- 存储：无数据库；配置、监控列表、日志使用 JSON 文件
- 运行：`uvicorn app.main:app --host 0.0.0.0 --port 8000`

## 重要目录和文件

```text
Dockerfile                    # 实际镜像构建入口，复制 backend/app 与 static
backend/app/                  # Docker 实际使用的后端代码
backend/app/main.py           # FastAPI 入口、路由注册、SPA fallback
backend/app/routers/          # dashboard/users/libraries/monitor/nfo API
backend/app/config.py         # 环境变量 + JSON 配置读取
backend/app/series_monitor.py # 完结监控定时任务
backend/app/tmdb_client.py    # TMDB API 封装（剧集详情、external_ids、单集详情）
backend/app/tvmaze_client.py  # TVmaze 免 Key 播出时间补充
backend/app/tg_notifier.py    # Telegram 通知
frontend/index.html           # 前端源文件
static/index.html             # Docker 实际服务的前端文件
VERSION                       # 项目版本
static/VERSION                # 静态版本，需和 VERSION 同步
README.md                     # GitHub 展示文档
AI_CONTEXT.md                 # 高频 AI 上下文
PROJECT.md                    # 架构/大功能上下文
API.md                        # API 文档
DATABASE.md                   # JSON 持久化/数据说明
```

注意：根目录 `app/` 是旧副本/兼容副本；Dockerfile 使用的是 `backend/app/`。除非明确需要同步旧副本，否则优先改 `backend/app/`。

## 前端修改规则

前端主要改：

```text
frontend/index.html
```

但实际 Docker 读取：

```text
static/index.html
```

所以前端改动必须同步到 `static/index.html`。如果没有同步脚本，就对两个文件做同样修改，并用测试确认：

```bash
python3 -m pytest test_monitor_frontend.py -q
```

## 当前版本规则

当前已知版本：`1.32`。

每次用户明确要求“推送”时，若包含代码/功能/接口/数据结构等实际项目变更，推送前必须版本号 +0.01。

**纯文档更新不推进版本号**，例如只改 `AI_CONTEXT.md`、`PROJECT.md`、`DATABASE.md`、`API.md` 时，不需要修改 `VERSION` 或侧边栏版本。

```text
1.21 → 1.22 → 1.23 → 1.24 → 1.25
```

必须同步四处：

```text
VERSION
static/VERSION
frontend/index.html 里的侧边栏 vX.XX
static/index.html 里的侧边栏 vX.XX
```

## Git 推送规则

- 未经用户明确允许，不能执行 `git push`。
- 用户说“推送”后才允许推送。
- 非纯文档变更推送前必须先升级版本号；纯文档更新不推进版本号。
- 推送前必须跑完整检查。

推荐流程：

```bash
git status --short
# 非纯文档变更：修改版本号；纯文档更新：跳过版本号
# 修改代码/文档
git diff --check
python3 -m py_compile backend/app/config.py backend/app/routers/monitor.py backend/app/series_monitor.py
python3 -m pytest test_monitor_frontend.py test_api_smoke.py -q
git add ...
git commit -m "..."
git push origin main
```

如果 HTTPS 推送缺凭据，但环境变量 `GITHUB_TOKEN` 已设置，可用临时 header 推送；不要输出 token：

```bash
HEADER=$(python3 -c 'import os,base64; print("AUTHORIZATION: basic "+base64.b64encode(("x-access-token:"+os.environ["GITHUB_TOKEN"]).encode()).decode())')
git -c http.https://github.com/.extraheader="$HEADER" push origin main
```

## 常用验证命令

最常用完整检查：

```bash
git diff --check && python3 -m py_compile backend/app/config.py backend/app/routers/monitor.py backend/app/series_monitor.py && python3 -m pytest test_monitor_frontend.py test_api_smoke.py -q
```

当前预期：`3 passed`。

其他：

```bash
python3 -m pytest test_monitor_frontend.py -q
python3 -m pytest test_dashboard_delete_backend.py -q
python3 -m pytest test_api_smoke.py -q
```

## 最近重点功能/状态

### 媒体库弹窗

当前方向是正确的：

- 桌面/iPad 端媒体库弹窗固定位置
- 上下留白一致
- 外层不再上下拖动/滚动
- 搜索框与分页固定可见
- 海报列表在弹窗内部滚动
- 关键 CSS：`.library-items-dialog`、`.library-items-panel`、`.library-items-scroll`、`.library-pagination`

不要再通过单纯增大 `top` 解决遮挡，否则会造成上方空隙。

### 媒体库卡片

- 不显示“0个路径”
- 显示电影/剧集数量
- 副文案统一为“点击查看全部”

### 完结监控

- 搜索结果简介两行省略
- 搜索结果区域有“关闭”按钮；搜索框清空时应清空搜索结果
- 添加订阅后先乐观插入列表，再后台刷新，并延迟二次刷新以等待 TMDB 异步详情更新
- 已监控剧集列表在卡片内部滚动，不让整个页面被长列表撑开
- 已监控剧集使用 `localStorage` 缓存，进入页面先展示缓存再后台刷新
- 调度配置使用标准 5 段 cron 规则，例如 `*/30 * * * *`
- 设置页不再暴露“更新通知模板/完结通知模板”输入项
- `overflow-wrap:anywhere` 防止长文本撑宽页面
- 刷新按钮使用 `monitor-refresh-btn` + 单个旋转图标
- 更新检测不仅看 `last_episode_to_air`，也会把 `next_episode_to_air.air_date <= 今天(项目 TZ)` 的剧集视为新集，避免 TMDB 延迟移动字段导致 TG 通知晚一天
- 更新通知会补拉 TMDB 单集详情（标题、简介、剧照、评分、片长）和 TVmaze 精确播出时间（免 API Key，转北京时间）；任一数据源失败时自动降级为原有播出日期/海报通知

### 删除接口

如果删除用户/媒体提示 API Key 不能删除，需要在 Docker Compose 配置：

```yaml
EMBY_ADMIN_USER=管理员用户名
EMBY_ADMIN_PW=管理员密码
```

### SPA 缓存

`backend/app/main.py` 的 SPA fallback 已加：

```text
Cache-Control: no-cache, no-store, must-revalidate
```

用于减少浏览器缓存导致 UI 不一致。

## 功能概览

- 仪表盘：概览、最近添加、活动日志、正在播放、详情、删除媒体
- 用户管理：列表、新建、删除、改密码、启用/禁用
- 媒体库：列表、数量统计、海报墙、搜索、分页、跳页、详情弹窗
- 完结监控：TMDB 搜索/详情/验证、TMDB 单集详情、TVmaze 播出时间补充、监控列表、定时检测、TG 通知、日志
- 配置：TMDB Key、TG Bot、代理、Cron 检查规则
- NFO 自动化：浏览选择演员目录、tvshow.nfo 表单、poster/fanart/logo 上传、PornHub 单集页面抓取发布时间和中文标签并勾选写入、剧集图片重命名、每集 nfo 批量生成；执行自动化后按 `NFO_MEDIA_ROOT → EMBY_MEDIA_ROOT` 映射精准刷新当前 Emby 演员目录（失败/找不到时兜底全库刷新）；单独保存/上传元数据后需手动点“刷新 Emby 元数据”避免频繁扫描

## 环境变量

核心：

```text
EMBY_URL
EMBY_API_KEY
EMBY_ADMIN_USER       # 删除功能需要
EMBY_ADMIN_PW         # 删除功能需要
MONITOR_DATA_DIR=/data
TMDB_API_KEY          # 可由 Web 配置覆盖/兜底
TG_BOT_TOKEN          # 可由 Web 配置覆盖/兜底
TG_CHAT_ID            # 可由 Web 配置覆盖/兜底
```

配置优先级：JSON 文件 > 环境变量兜底。

## 文档分层

- `AI_CONTEXT.md`：⭐⭐⭐⭐⭐ 新会话从 GitHub 拉取/接手 Emby Manager 时开头读一次，了解项目后同一对话不必重复读取
- `PROJECT.md`：⭐⭐⭐ 大功能、架构相关时发
- `DATABASE.md`：⭐⭐ 数据库/JSON 持久化改动时发
- `API.md`：⭐⭐ 接口改动时发

## 开发注意事项

1. Docker 实际使用 `backend/app/` 和 `static/`。
2. 前端修改必须保持 `frontend/index.html` 与 `static/index.html` 一致。
3. 新 API 路由要在 `backend/app/main.py` include。
4. 不要读取或输出密钥/token。
5. 推送前必须升级版本号并跑测试。
6. 未经用户明确允许不能 push。

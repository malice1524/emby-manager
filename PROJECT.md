# PROJECT.md — Emby Manager 项目文档 ⭐⭐⭐

> 用途：大功能开发、架构调整、部署改动、目录理解时发送/读取。日常新会话优先读 `AI_CONTEXT.md`；只有大功能、架构相关时再读本文件。

## 1. 项目简介

Emby Manager 是一个面向 NAS/自建媒体库用户的 Emby Web 管理面板，用一个单容器应用提供：

- Emby 仪表盘
- 用户管理
- 媒体库浏览
- 图片代理
- 全局搜索
- 剧集完结监控
- Telegram 通知
- 媒体整理（生成 tvshow/封面、115 视频扫描翻译重命名移动、每集 NFO 生成）

项目目标：减少进入 Emby 原生后台的频率，让常用管理操作在一个移动端/桌面端友好的页面里完成。

## 2. 当前架构

```text
用户浏览器
  ↓
Vue 3 单页应用（static/index.html）
  ↓ /api/*
FastAPI / uvicorn
  ├─ Emby API
  ├─ TMDB API
  ├─ TVmaze API
  ├─ Telegram Bot API
  ├─ JSON 文件持久化 /data/*.json
  └─ APScheduler 完结监控定时任务
```

特点：

1. **单容器**：前端静态文件、后端 API、定时任务在同一容器内。
2. **无传统数据库**：配置、监控列表、日志存 JSON 文件。
3. **前端无构建步骤**：Vue/Element Plus 通过本地静态依赖加载，主要代码在单个 HTML。
4. **图片代理**：前端图片请求通过后端代理，解决跨域/内外网访问问题。
5. **Web 配置优先**：TMDB/TG/代理/Cron 检查规则等配置优先读 `/data/config.json`，环境变量兜底。

## 3. 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| Python 3.12 | 运行环境 |
| FastAPI | Web API |
| uvicorn | ASGI 服务 |
| httpx | 异步请求 Emby/TMDB/TVmaze/TG |
| APScheduler | 完结监控定时任务 |
| JSON 文件 | 配置/监控数据持久化 |

### 前端

| 技术 | 用途 |
|------|------|
| Vue 3 Options API | SPA 组件逻辑 |
| Vue Router | 前端路由 |
| Element Plus | UI 组件 |
| CSS 变量 | 暗色毛玻璃设计系统 |

### 部署

| 文件 | 用途 |
|------|------|
| `Dockerfile` | 单容器镜像构建 |
| `docker-compose.yml` | 本地/NAS 部署模板 |
| `.github/workflows/docker-publish.yml` | GitHub Actions 自动构建 DockerHub 镜像 |

## 4. 目录结构

```text
emby-manager/
├── .github/workflows/
│   └── docker-publish.yml       # main 推送后构建 DockerHub latest
├── backend/
│   ├── requirements.txt
│   └── app/                     # Docker 实际使用的后端代码
│       ├── main.py              # FastAPI 入口、路由注册、SPA fallback
│       ├── config.py            # 环境变量 + JSON 配置
│       ├── emby_client.py       # Emby 客户端/兼容逻辑（如存在）
│       ├── tmdb_client.py       # TMDB 查询封装
│       ├── tvmaze_client.py     # TVmaze 播出时间补充
│       ├── tg_notifier.py       # Telegram 通知
│       ├── series_monitor.py    # 完结监控核心
│       └── routers/
│           ├── dashboard.py     # 仪表盘/最近添加/详情/图片/删除媒体
│           ├── users.py         # 用户管理
│           ├── libraries.py     # 媒体库
│           ├── monitor.py       # TMDB/监控/配置
│           ├── nfo.py           # 旧 NFO 自动化/媒体元数据复用接口
│           ├── file_organizer.py# 文件整理核心 API
│           └── media_organizer.py # 媒体整理统一入口 API
├── app/                         # 旧副本/兼容副本，Docker 默认不用
├── frontend/
│   ├── index.html               # 前端源文件
│   └── lib/                     # Vue/Router/Element Plus 静态依赖
├── static/
│   ├── index.html               # Docker 实际服务的 SPA
│   ├── VERSION
│   └── lib/
├── test_monitor_frontend.py
├── test_dashboard_delete_backend.py
├── test_api_smoke.py
├── VERSION
├── README.md
├── AI_CONTEXT.md
├── PROJECT.md
├── API.md
└── DATABASE.md
```

## 5. 核心模块

### 5.1 仪表盘

主要文件：

```text
backend/app/routers/dashboard.py
frontend/index.html
static/index.html
```

能力：

- 服务器信息
- 媒体统计
- 最近添加
- 媒体库筛选
- 活动日志
- 正在播放
- 媒体详情
- 图片代理
- 删除媒体

删除媒体通常需要管理员凭据，见环境变量：

```text
EMBY_ADMIN_USER
EMBY_ADMIN_PW
```

### 5.2 用户管理

主要文件：

```text
backend/app/routers/users.py
```

能力：

- 用户列表
- 创建用户
- 删除用户
- 修改密码
- 启用/禁用用户

### 5.3 媒体库

主要文件：

```text
backend/app/routers/libraries.py
frontend/index.html
static/index.html
```

当前 UI 要点：

- 媒体库卡片显示电影/剧集数量
- 副文案为“点击查看全部”
- 弹窗固定位置，上下留白一致
- 搜索框和分页固定可见
- 海报列表内部滚动
- 分页支持 total、prev、pager、next、jumper

### 5.4 完结监控

主要文件：

```text
backend/app/routers/monitor.py
backend/app/series_monitor.py
backend/app/tmdb_client.py
backend/app/tvmaze_client.py
backend/app/tg_notifier.py
backend/app/config.py
```

流程：

```text
用户搜索 TMDB 剧集
  → 添加到 monitored_series.json
  → APScheduler 定时检查 TMDB 状态
  → 对比 last_episode/status；当天或更早的 next_episode_to_air 也按新集处理
  → 新集补拉 TMDB 单集详情（标题/简介/剧照/评分/片长）
  → 通过 TMDB external_ids 匹配 TVmaze，补充北京时间播出时间
  → Telegram 更新/完结通知（缺失字段自动降级）
  → 写 monitor_log.json
```

### 5.5 媒体整理

媒体整理把旧版 `NFO 自动化` 与 `文件整理` 合并为一个统一页面，按实际整理顺序分两步完成。

主要文件：

```text
backend/app/routers/media_organizer.py   # 页面统一 API：/api/media-organizer
backend/app/file_organizer.py            # 视频扫描/翻译/移动/日志核心
backend/app/routers/nfo.py               # tvshow.nfo、封面上传、Emby 刷新等复用能力
frontend/index.html
static/index.html
```

流程：

```text
1. 生成 tvshow.nfo / poster.jpg / fanart.jpg / logo.png
  → 通过 /api/media-organizer/browse?root=strm 浏览 /strm 下演员目录
  → 保存 tvshow.nfo（title/plot/outline/tmdb_id/dateadded/sorttitle/displayorder/tags 等），tags 同时写入 <tag>/<genre>
  → 上传 poster/fanart/logo 到演员目录

2. 扫描视频 / 翻译标题 / 生成每集 NFO / 移动到目标目录
  → 通过 /api/media-organizer/browse?root=cloud115 选择源目录和目标目录
  → 扫描 CloudDrive115 视频，可按文件名、mtime、发布时间排序；扫描结果提供 title 与 clean_title，clean_title 用于每集 NFO 英文简介
  → DeepSeek 翻译标题，支持手动调整顺序和起始集数
  → 预检查目标冲突
  → 移动/重命名视频与同名图片，并按勾选生成每集 .nfo（title=中文标题，plot=去日期/去 viewkey/下划线转空格后的英文标题）
```

前端注意：

- `fetchJSON` 会自动加 `/api`，媒体整理前端应调用 `/media-organizer/...`，不要写 `/api/media-organizer/...`，否则会变成 `/api/api/media-organizer/...`。
- 目录选择弹窗必须 `append-to-body`，并使用 `media-browse-dialog` 可见性样式，避免页面滚动到第二步后只显示遮罩、弹窗本体不可见。
- `frontend/index.html` 与 `static/index.html` 必须保持一致。

安全规则：

- `root=strm` 只允许浏览候选 STRM 根目录：`NFO_MEDIA_ROOT`、`STRM_ROOT`、`/vol1/1000/docker/strm`、`/strm`。
- `root=cloud115` 只允许浏览候选 115 根目录：`CLOUD115_ROOT`、`/CloudDrive115`、`/vol1/1000/docker/CloudDrive115/CloudDrive`。
- 后端浏览响应统一返回 `directories`；`root=strm` 同时保留 `dirs` 兼容旧字段。

### 7.1 前端修改

1. 改 `frontend/index.html`
2. 同步到 `static/index.html`
3. 跑测试：

```bash
python3 -m pytest test_monitor_frontend.py -q
```

### 7.2 后端修改

1. 优先改 `backend/app/`
2. 如测试或旧副本依赖根目录 `app/`，再同步根目录旧副本
3. 新路由必须在 `backend/app/main.py` 注册
4. 跑对应测试

### 7.3 推送前

必须：

```bash
git diff --check
python3 -m py_compile backend/app/config.py backend/app/routers/monitor.py backend/app/series_monitor.py
python3 -m pytest test_monitor_frontend.py test_api_smoke.py -q
```

用户明确说“推送”后：

1. 非纯文档变更：版本号 +0.01；纯文档更新：不推进版本号
2. 非纯文档变更需同步四处版本号
3. 测试通过
4. commit
5. push

## 8. 版本号规则

非纯文档变更每次推送前版本号 +0.01；纯文档更新不推进版本号。当前已知版本：`1.25`。

```text
1.21 → 1.22 → 1.23 → 1.24 → 1.25
1.22 → 1.23
1.23 → 1.24
```

同步：

```text
VERSION
static/VERSION
frontend/index.html: vX.XX
static/index.html: vX.XX
```

## 9. 测试说明

现有测试：

```text
test_monitor_frontend.py          # 前端关键字符串/同步检查
test_dashboard_delete_backend.py  # 删除接口提示/凭据相关测试，可按需单独跑
test_api_smoke.py                 # API smoke test + 配置接口校验
```

常用命令：

```bash
git diff --check && python3 -m py_compile backend/app/config.py backend/app/routers/monitor.py backend/app/series_monitor.py && python3 -m pytest test_monitor_frontend.py test_api_smoke.py -q
```

## 10. 常见坑

1. 只改 `frontend/index.html`，忘记同步 `static/index.html`。
2. 非纯文档变更只改 `VERSION`，忘记 `static/VERSION` 和侧边栏版本；纯文档更新则不要改版本号。
3. 未经用户允许直接 `git push`。
4. 用增大 `top` 解决媒体库弹窗遮挡，导致上方空隙。
5. 删除接口失败时只看 API Key，忽略 `EMBY_ADMIN_USER/PW`。
6. 输出 token/API key 到日志或聊天。
7. 新增路由后忘记在 `main.py` include。

## 11. 文档发送优先级

- `AI_CONTEXT.md`：⭐⭐⭐⭐⭐ 新会话从 GitHub 拉取/接手 Emby Manager 时开头读一次，了解项目后同一对话不必重复读取
- `PROJECT.md`：⭐⭐⭐ 大功能、架构相关时发
- `DATABASE.md`：⭐⭐ 数据库/JSON 持久化改动时发
- `API.md`：⭐⭐ 接口改动时发

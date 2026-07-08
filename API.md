# API.md — Emby Manager 接口文档 ⭐⭐

> 用途：接口新增、接口修改、前后端联调、排查 API 问题时发送/读取。日常开发先读 `AI_CONTEXT.md`。

## 0. 基础信息

- 服务基础地址：`http://localhost:8000` 或 Docker 映射端口，如 `http://NAS:8117`
- API 前缀：`/api`
- 前端 SPA：`/` 和非 `/api` 路径由 `static/index.html` 兜底
- 静态依赖：`/lib/*`
- 认证：后端通过环境变量/配置中的 Emby 凭据访问 Emby；前端接口本身当前无登录鉴权

## 1. 系统

### 1.1 健康检查

```http
GET /api/health
```

返回：

```json
{"status":"ok"}
```

## 2. 仪表盘 `/api/dashboard`

主要文件：`backend/app/routers/dashboard.py`

### 2.1 图片代理

```http
GET /api/dashboard/images/{item_id}?w=400&type=item
```

参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `w` | int | 否 | 400 | 图片宽度 |
| `type` | string | 否 | item | `item` 媒体图片；`user` 用户头像 |

返回：图片二进制。

### 2.2 概览

```http
GET /api/dashboard/overview
```

返回示例：

```json
{
  "media": {"movies": 5832, "series": 206, "episodes": 5817},
  "users": {"total": 4, "admins": 2},
  "sessions": {"active": 1, "streams": []},
  "libraries": 19,
  "server": {"name": "Emby", "version": "4.8.11.0"}
}
```

### 2.3 最近添加

```http
GET /api/dashboard/recent?limit=12&types=Movie,Series&parent_id=&exclude_parent_ids=&search=
```

参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `limit` | int | 否 | 12 | 返回数量，通常 1-50 |
| `types` | string | 否 | Movie,Series | Emby 类型，逗号分隔 |
| `parent_id` | string | 否 | 空 | 指定媒体库 ID |
| `exclude_parent_ids` | string | 否 | 空 | 排除媒体库 ID，逗号分隔 |
| `search` | string | 否 | 空 | 搜索关键词 |

返回：

```json
{"items":[{"id":"...","name":"...","type":"Movie","year":2026,"overview":"...","rating":8.1,"image_url":"..."}]}
```

### 2.4 媒体详情

```http
GET /api/dashboard/item/{item_id}
```

返回字段包含：

```text
id, name, overview, type, year, rating, genres,
tmdb_id, imdb_id, tmdb_url, imdb_url, cast
```

### 2.5 活动/系统统计

```http
GET /api/dashboard/stats
```

返回：

```json
{"activity": [], "system": {}}
```

### 2.6 删除媒体

```http
DELETE /api/dashboard/item/{item_id}
```

返回：

```json
{"status":"ok"}
```

注意：删除能力需要管理员凭据。若提示 API Key 不能删除，在 Docker Compose 配置：

```text
EMBY_ADMIN_USER
EMBY_ADMIN_PW
```

## 3. 用户管理 `/api/users`

主要文件：`backend/app/routers/users.py`

### 3.1 用户列表

```http
GET /api/users
```

返回：

```json
{
  "users": [{
    "id": "...",
    "name": "user",
    "avatar_url": "...",
    "has_password": true,
    "is_admin": false,
    "is_disabled": false,
    "last_login": "...",
    "last_active": "...",
    "created": "..."
  }]
}
```

### 3.2 创建用户

```http
POST /api/users?name=用户名&password=密码
```

返回：

```json
{"status":"ok","id":"..."}
```

### 3.3 删除用户

```http
DELETE /api/users/{user_id}
```

返回：

```json
{"status":"ok"}
```

### 3.4 修改密码

```http
PUT /api/users/{user_id}/password
Content-Type: application/json

{"new_pw":"新密码"}
```

返回：

```json
{"status":"ok"}
```

### 3.5 修改用户策略

```http
PUT /api/users/{user_id}/policy
Content-Type: application/json

{"IsDisabled":true}
```

返回：

```json
{"status":"ok"}
```

## 4. 媒体库 `/api/libraries`

主要文件：`backend/app/routers/libraries.py`

### 4.1 媒体库列表

```http
GET /api/libraries
```

返回：

```json
{
  "libraries": [{
    "id": "...",
    "name": "欧美电影",
    "type": "movies",
    "counts": {"movies": 359, "series": 0, "episodes": 0, "total": 359}
  }]
}
```

### 4.2 媒体库内容

```http
GET /api/libraries/{item_id}/items?limit=30&page=1&search=&types=
```

参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `limit` | int | 否 | 30 | 每页数量 |
| `page` | int | 否 | 1/0 | 页码；以前端实际传值为准 |
| `search` | string | 否 | 空 | 搜索关键词 |
| `types` | string | 否 | 空 | 类型过滤，如 movies/tvshows |

返回：

```json
{"items":[{"id":"...","name":"...","type":"Movie","year":2026,"has_image":true}],"total":76}
```

前端依赖 `total` 做分页显示。

## 5. TMDB 与完结监控

主要文件：`backend/app/routers/monitor.py`、`backend/app/series_monitor.py`、`backend/app/tmdb_client.py`、`backend/app/tvmaze_client.py`、`backend/app/tg_notifier.py`

### 5.1 TMDB 搜索剧集

```http
GET /api/tmdb/search?q=关键词&page=1
```

返回：

```json
{
  "results": [{
    "tmdb_id": 95557,
    "title": "凡人修仙传",
    "year": "2020",
    "poster_url": "https://image.tmdb.org/t/p/w500/...",
    "overview": "...",
    "vote_average": 8.5,
    "media_type": "tv"
  }]
}
```

### 5.2 TMDB 剧集详情

```http
GET /api/tmdb/detail/{tmdb_id}
```

返回字段包含：

```text
tmdb_id, title, status, type, vote_average,
number_of_episodes, next_episode_to_air,
last_episode_to_air, last_air_date, overview
```

说明：定时检测更新时，后端除了使用 `last_episode_to_air`，也会把 `next_episode_to_air.air_date <= 今天(项目 TZ)` 且比本地记录更新的单集视为已更新，避免 TMDB 当天未及时移动字段导致 TG 通知晚一天。

### 5.3 验证 TMDB Key

```http
GET /api/tmdb/verify
```

返回：

```json
{"valid":true}
```

或：

```json
{"valid":false,"error":"..."}
```

### 5.4 获取监控列表

```http
GET /api/monitor/list
```

返回：

```json
{
  "series": [{
    "tmdb_id": 95557,
    "title": "凡人修仙传",
    "poster_url": "...",
    "current_status": "Returning Series",
    "notified_ended": false,
    "next_episode": {"air_date": "2026-07-06", "episode_number": 181},
    "last_episode": {"air_date": "2026-06-29", "episode_number": 180},
    "total_episodes": 200,
    "type": "动画",
    "vote_average": 8.5
  }]
}
```

### 5.5 添加监控

```http
POST /api/monitor/add
Content-Type: application/json

{"tmdb_id":95557,"title":"凡人修仙传","year":"2020","poster_url":"..."}
```

返回：

```json
{"success":true,"notification_sent":false}
```

说明：接口尽快返回，后续详情查询/通知可异步处理。更新通知默认会尽量补充 TMDB 单集详情（标题、简介、剧照、评分、片长）和 TVmaze 北京时间播出时间；任一外部数据源失败时自动降级，不影响基础通知。

### 5.6 删除监控

```http
DELETE /api/monitor/{tmdb_id}
```

返回：

```json
{"success":true}
```

### 5.7 监控状态

```http
GET /api/monitor/status
```

返回：监控任务状态、下次检测时间等，具体字段以实现为准。

### 5.8 监控日志

```http
GET /api/monitor/logs?limit=50
```

返回：最近检测日志。

### 5.9 更新通知增强数据源

定时检测发现新集后，后端会在发送 TG 更新通知前临时补充：

```text
TMDB /tv/{id}/season/{season}/episode/{episode}
  → 单集标题、简介、剧照、单集评分、片长
TMDB /tv/{id}/external_ids
  → tvdb_id / imdb_id
TVmaze /lookup/shows + /shows/{id}/episodes
  → 单集精确播出时间，转换为北京时间
```

这些增强数据不新增对外 API，也不写入 `/data/monitored_series.json`；只用于当次通知。TVmaze 不需要 API Key，匹配失败或无时间时自动降级为 TMDB 的 `air_date`。

## 6. 配置 `/api/config`

主要文件：`backend/app/routers/monitor.py` + `backend/app/config.py`

### 6.1 获取配置

```http
GET /api/config
```

返回字段：

```text
tmdb_api_key, tg_bot_token, tg_chat_id, proxy_url, check_cron
```

注意：前端会回显配置；不要在日志/聊天里输出真实 token。

### 6.2 保存配置

```http
PUT /api/config
Content-Type: application/json

{
  "tmdb_api_key":"...",
  "tg_bot_token":"...",
  "tg_chat_id":"...",
  "proxy_url":"http://host:port",
  "check_cron":"*/30 * * * *"
}
```

返回：

```json
{"success":true}
```

`check_cron` 使用标准 5 段 crontab 表达式。非法规则返回：

```http
400 Bad Request
```

示例错误：

```json
{"detail":"Cron 规则无效：..."}
```

### 6.3 测试 Telegram

```http
POST /api/config/test
```

返回：测试发送结果。

### 6.4 测试代理

```http
POST /api/config/test-proxy
```

返回：代理连通性测试结果。

## 7. NFO 自动化 `/api/nfo`

主要文件：`backend/app/routers/nfo.py`

### 7.1 浏览媒体目录

```http
GET /api/nfo/automation/browse?path=/vol1/1000/docker/strm/已整理/PornHub
```

`path` 可省略；省略时从 `NFO_MEDIA_ROOT` 根目录开始。返回当前目录、父目录、媒体根目录、子目录列表，以及每个子目录是否包含 `Season 1`（可作为演员目录选择）。前端只通过这个目录浏览器选择演员目录，不提供手动路径输入。

### 7.2 扫描演员目录

```http
POST /api/nfo/automation/scan
Content-Type: application/json

{"actor_dir":"/vol1/1000/docker/strm/已整理/PornHub/Sienna Moore"}
```

返回：演员名、Season 1 路径、`tvshow/poster/fanart/logo` 存在状态、`.strm/同名图片(.jpg/.jpeg/.png/.webp)/.nfo` 计数、缺图/缺 nfo 集数、是否已有单集发布时间、`IMG_*` 图片重命名预览。

### 7.3 保存 tvshow.nfo

```http
POST /api/nfo/automation/tvshow
Content-Type: application/json

{
  "actor_dir":".../Sienna Moore",
  "title":"Sienna Moore",
  "plot":"简介",
  "outline":"简介",
  "tmdb_id":"6329873",
  "dateadded":"2026-07-06 18:00:00",
  "overwrite":true,
  "tags":["素人情侣", "吃鸡"]
}
```

字段顺序：`plot → outline → lockdata → dateadded → title → actor → sorttitle → tag/genre → season → episode → displayorder`。覆盖已有文件时直接替换；`tags` 只写入包含中文的标签，并同时输出 `<tag>` 与 `<genre>`。

### 7.4 上传演员图片

```http
POST /api/nfo/automation/upload-artwork
multipart/form-data:
  actor_dir=.../Sienna Moore
  kind=poster|fanart|logo
  overwrite=true
  image=<file>
```

保存为固定文件名：`poster.jpg`、`fanart.jpg`、`logo.png`，已存在时直接替换。

### 7.5 上传剧集图片

```http
POST /api/nfo/automation/upload-episode-images
multipart/form-data:
  actor_dir=.../Sienna Moore
  images=<files>
```

图片保存到 `Season 1`，再通过扫描/执行流程按 `IMG_*` 与 mtime 生成重命名计划。

### 7.6 PornHub 单集元数据预览

```http
POST /api/nfo/automation/pornhub-metadata/preview
Content-Type: application/json

{"url":"https://cn.pornhub.com/view_video.php?viewkey=..."}
```

只支持 `pornhub.com` / `*.pornhub.com` 的 `view_video.php` 视频页。后端抓取页面后优先解析 JSON-LD，其次解析 meta/HTML 兜底字段，返回发布时间与中文标签；英文标签会被过滤，不返回给前端勾选。

返回示例：

```json
{
  "ok": true,
  "published_at": "2024-06-01",
  "tags": ["国产", "巨乳", "4K中文"],
  "all_tag_count": 12,
  "chinese_tag_count": 3,
  "message": ""
}
```

### 7.7 批量写入 PornHub 发布时间

```http
POST /api/nfo/automation/pornhub-published/batch-write
Content-Type: application/json

{
  "actor_dir":".../Sienna Moore",
  "items":[
    {"strm_filename":"Sienna Moore.S01E01.标题.strm", "url":"https://cn.pornhub.com/view_video.php?viewkey=..."},
    {"strm_filename":"Sienna Moore.S01E02.标题.strm", "url":"https://cn.pornhub.com/view_video.php?viewkey=..."}
  ]
}
```

只允许选择当前演员目录 `Season 1` 下的 `.strm`。后端逐条抓取 PornHub 页面发布时间，并写入对应同名单集 `.nfo` 的 `aired/premiered`；某一行失败不影响其他行。标签不在此接口写入，中文标签通过保存 `tvshow.nfo` 写入 `<tag>/<genre>`。

返回示例：

```json
{
  "ok": true,
  "results": [
    {"strm_filename":"...E01...strm", "ok":true, "published_at":"2024-06-01", "nfo":"...E01...nfo", "error":""},
    {"strm_filename":"...E02...strm", "ok":false, "published_at":"", "nfo":"", "error":"未解析到发布时间"}
  ]
}
```

### 7.8 刷新 Emby 元数据

```http
POST /api/nfo/automation/refresh-emby
```

调用 Emby 刷新任务。带 `actor_dir` 时优先按 `NFO_MEDIA_ROOT → EMBY_MEDIA_ROOT` 映射精准刷新当前演员目录；不带 `actor_dir` 时调用 `/Library/Refresh` 全库刷新。NFO 自动化执行接口默认会在完成后自动刷新；演员目录扫描概览也提供手动“刷新 Emby 元数据”按钮。

注意：前端在保存 `tvshow.nfo`、上传 `poster/fanart/logo`、批量写入 PornHub 发布时间后，会自动重新扫描当前演员目录并调用本接口精准刷新当前 Emby 演员目录。上传剧集图片本身只是暂存，仍需执行自动化重命名后刷新。

### 7.9 执行自动化

```http
POST /api/nfo/automation/execute
Content-Type: application/json

{"actor_dir":".../Sienna Moore", "refresh_emby": true}
```

执行：

- `IMG_*.JPG` 按 mtime 从早到晚匹配缺图剧集并重命名为同名 `.JPG`
- 为缺失/空的同名 `.nfo` 生成：`episodedetails/title/season/episode`
- 不覆盖已有剧集图片或 nfo
- `refresh_emby` 默认为 `true`，执行完成后优先按 `NFO_MEDIA_ROOT → EMBY_MEDIA_ROOT` 路径映射查找当前演员目录对应的 Emby 项目并精准刷新；找不到项目时自动兜底调用 Emby `/Library/Refresh`，失败只写入日志，不回滚本地 NFO/图片操作

安全：只允许操作 `NFO_MEDIA_ROOT` 下目录，默认 `/vol1/1000/docker/strm`。

## 8. DeepSeek 设置 `/api/settings`

主要文件：`backend/app/routers/settings.py`、`backend/app/settings_store.py`、`backend/app/deepseek_client.py`

### 8.1 获取 DeepSeek 设置

```http
GET /api/settings/deepseek
```

返回非敏感配置和 Key 状态，不返回完整 API Key：

```json
{"base_url":"https://api.deepseek.com","model":"deepseek-chat","batch_size":10,"api_key_configured":true,"api_key_source":"saved"}
```

### 8.2 保存 DeepSeek 设置

```http
PUT /api/settings/deepseek
Content-Type: application/json

{"api_key":"...","base_url":"https://api.deepseek.com","model":"deepseek-chat","batch_size":10}
```

说明：不传 `api_key` 保留已保存 Key；传空字符串清空已保存 Key，并回落 `DEEPSEEK_API_KEY` 环境变量。响应不回显 Key。

### 8.3 测试翻译

```http
POST /api/settings/deepseek/test-translation
Content-Type: application/json

{"title":"Beautiful Girl At Home 1080p"}
```

返回：

```json
{"ok":true,"title":"美丽女孩在家中","skipped":false}
```

## 9. 文件整理 `/api/file-organizer`

主要文件：`backend/app/routers/file_organizer.py`、`backend/app/file_organizer.py`

安全边界：视频整理只允许 `/CloudDrive115` 内路径；元数据源只允许 `/strm`；元数据目标只允许 `/CloudDrive115`。

### 9.1 浏览目录

```http
GET /api/file-organizer/browse?root=cloud115&path=/CloudDrive115
```

`root` 支持 `cloud115` 和 `strm`。返回当前目录、父目录和子目录列表。

### 9.2 扫描视频

```http
POST /api/file-organizer/scan
Content-Type: application/json

{"source_dir":"/CloudDrive115/待整理","recursive":false,"sort":"name"}
```

`sort` 支持 `name` 和 `mtime`。只返回 `.mp4/.mkv/.avi/.mov/.wmv/.flv/.ts/.m2ts/.webm`。

### 9.3 翻译标题

```http
POST /api/file-organizer/translate
Content-Type: application/json

{"items":[{"id":"1","title":"Beautiful Girl At Home"}]}
```

中文标题会跳过 DeepSeek；非中文标题按 DeepSeek 批量翻译返回行级结果。

### 9.4 视频移动预检查与执行

```http
POST /api/file-organizer/precheck
POST /api/file-organizer/execute
```

请求包含 `confirmed` 和 `items[].source_path/target_path`。执行使用挂载文件系统移动，不覆盖目标视频、不删除视频、不自动回滚；部分失败保留失败项用于重试。

### 9.5 元数据复制预检查与执行

```http
POST /api/file-organizer/metadata/precheck
POST /api/file-organizer/metadata/execute
```

请求示例：

```json
{"source_dir":"/strm/PornHub/Sienna Moore","target_dir":"/CloudDrive115/PornHub/Sienna Moore","confirmed":true}
```

只复制 `.nfo/.jpg/.jpeg/.png/.webp`，不复制 `.strm` 或视频文件；保留 `Season 1` 等目录结构；同名元数据确认后覆盖。

## 10. API 开发注意事项

1. 新增后端路由优先放 `backend/app/routers/`。
2. 新路由必须在 `backend/app/main.py` include。
3. Docker 实际使用 `backend/app/`。
4. 修改接口后同步更新 `API.md`。
5. 涉及 JSON 结构时同步更新 `DATABASE.md`。
6. 不要在错误信息或日志中泄露 API key、token、密码。
7. 前端调用统一注意错误提示，不要只显示“失败”。

## 9. 文档发送优先级

- `AI_CONTEXT.md`：⭐⭐⭐⭐⭐ 新会话从 GitHub 拉取/接手 Emby Manager 时开头读一次，了解项目后同一对话不必重复读取
- `PROJECT.md`：⭐⭐⭐ 大功能、架构相关时发
- `DATABASE.md`：⭐⭐ 数据库/JSON 持久化改动时发
- `API.md`：⭐⭐ 接口改动时发

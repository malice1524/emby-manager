# DATABASE.md — Emby Manager 数据/持久化文档 ⭐⭐

> 用途：数据结构、配置迁移、JSON 文件变更、备份恢复、监控状态字段调整时发送/读取。

## 1. 总览

Emby Manager 当前**不使用传统数据库**，没有 MySQL/PostgreSQL/SQLite 表。

运行时数据来源：

```text
Emby API        # 用户、媒体库、媒体详情、会话、图片等
TMDB API        # 剧集监控、单集详情、NFO 人物信息
TVmaze API      # 剧集更新通知的精确播出时间（免 API Key）
Telegram API    # 通知发送
JSON 文件       # 本地配置、监控列表、监控日志
```

本地持久化目录由环境变量控制：

```text
MONITOR_DATA_DIR=/data
```

Docker Compose 通常挂载：

```yaml
volumes:
  - ./monitor_data:/data
```

配置读取优先级：

```text
/data/*.json > 环境变量兜底
```

## 2. JSON 文件清单

```text
/data/config.json             # Web 配置
/data/monitored_series.json   # 监控剧集列表和状态
/data/monitor_log.json        # 完结监控检测日志
```

## 3. `/data/config.json`

### 3.1 用途

保存用户在 Web 设置页面填写的配置。

涉及模块：

```text
backend/app/config.py
backend/app/routers/monitor.py
backend/app/tmdb_client.py
backend/app/tg_notifier.py
backend/app/series_monitor.py
```

### 3.2 字段

| 字段 | 类型 | 说明 | 环境变量兜底 |
|------|------|------|--------------|
| `tmdb_api_key` | string | TMDB API Key | `TMDB_API_KEY` |
| `tg_bot_token` | string | Telegram Bot Token | `TG_BOT_TOKEN` |
| `tg_chat_id` | string | Telegram 接收用户/群 ID | `TG_CHAT_ID` |
| `proxy_url` | string | HTTP/HTTPS 代理地址 | 无或实现内兜底 |
| `check_cron` | string | 标准 5 段 cron 检查规则，如 `*/30 * * * *` | `CHECK_CRON` 或默认值 |
| `check_interval_minutes` | int | 旧版本自动检测间隔分钟，仅用于兼容迁移 | 默认 30 |

### 3.3 示例

```json
{
  "tmdb_api_key": "不要在文档里写真实 key",
  "tg_bot_token": "不要在文档里写真实 token",
  "tg_chat_id": "123456789",
  "proxy_url": "http://192.168.1.100:7890",
  "check_cron": "*/30 * * * *"
}
```

### 3.4 注意事项

- 不要把真实 API Key/Token 提交到 Git。
- AI/日志/错误输出不要打印真实配置值。
- `check_cron` 使用标准 5 段 crontab 表达式；保存配置时后端会校验，非法规则返回 400。
- 旧字段 `check_interval_minutes` 仅用于兼容历史配置；没有 `check_cron` 时会自动转成 `*/N * * * *`。
- 前端设置页不再展示 `update_template` / `end_template`；Telegram 通知使用后端默认模板。

## 4. `/data/monitored_series.json`

### 4.1 用途

保存用户添加的 TMDB 剧集监控列表，以及上次检测状态。

涉及模块：

```text
backend/app/series_monitor.py
backend/app/routers/monitor.py
backend/app/tmdb_client.py
backend/app/tvmaze_client.py
```

### 4.2 主结构

```json
{
  "series": []
}
```

### 4.3 单条记录字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `tmdb_id` | int | TMDB 剧集 ID，逻辑主键 |
| `title` | string | 剧集名称 |
| `year` | string | 年份，可选 |
| `poster_url` | string | TMDB 海报 URL |
| `added_at` | string | 添加时间，ISO 字符串 |
| `current_status` / `last_status` | string | 当前/上次状态，如 `Returning Series`、`Ended`、`Canceled` |
| `last_episode_air_date` | string | 最新一集播出日期 |
| `last_episode_number` | int | 最新集号 |
| `total_episodes` | int | 总集数 |
| `next_episode` | object/null | 下一集信息 |
| `last_episode` | object/null | 最新一集信息 |
| `type` | string | 类型，如动画/剧集等 |
| `vote_average` | number | TMDB 评分 |
| `overview` | string | 简介 |
| `notified_ended` | bool | 是否已发送完结通知 |

字段可能随 TMDB 返回和历史版本存在差异，开发时要兼容缺失字段。

### 4.4 示例

```json
{
  "series": [
    {
      "tmdb_id": 95557,
      "title": "凡人修仙传",
      "year": "2020",
      "poster_url": "https://image.tmdb.org/t/p/w500/...",
      "added_at": "2026-07-01T12:00:00",
      "current_status": "Returning Series",
      "last_episode_air_date": "2026-06-29",
      "last_episode_number": 180,
      "total_episodes": 200,
      "notified_ended": false
    }
  ]
}
```

### 4.5 逻辑约束

- `tmdb_id` 应唯一。
- 删除监控按 `tmdb_id` 删除。
- 检测更新通常比较 `last_episode_air_date` / `last_episode_number`。
- 若 TMDB 的 `next_episode_to_air.air_date <= 今天(项目 TZ)` 且比当前记录更新，也会按新集处理，避免 TMDB 延迟把今日集移动到 `last_episode_to_air` 导致通知晚一天。
- TG 更新通知发送前会临时补拉 TMDB 单集详情与 TVmaze 播出时间；这些增强字段不写入 `monitored_series.json`，只用于当次通知。
- 完结通知通常依赖状态变为 `Ended` 且 `notified_ended=false`。

## 5. `/data/monitor_log.json`

### 5.1 用途

记录完结监控每次检测结果，供前端日志面板展示。

### 5.2 主结构

数组：

```json
[
  {
    "time": "2026-07-01T12:00:00",
    "status": "ok",
    "message": "检查完成 · 5 部剧 · 1 更新 · 0 完结"
  }
]
```

### 5.3 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `time` | string | 检查时间，ISO 字符串 |
| `status` | string | 状态，如 `ok`、`warning`、`error` |
| `message` | string | 人类可读日志 |

### 5.4 约束

- 通常保留最近 100 条。
- 前端按时间倒序展示。
- 日志中不要写入真实 token/key/password。

## 6. 外部数据源

### 6.1 Emby API

| 数据 | Emby 端点 | 用途 |
|------|-----------|------|
| 用户 | `/Users`, `/Users/{id}` | 用户列表、详情、策略、密码 |
| 用户头像 | `/Users/{id}/Images/Primary` | 图片代理 |
| 媒体统计 | `/Items/Counts` | 仪表盘统计 |
| 媒体项目 | `/Items`, `/Items/{id}` | 最近添加、详情、媒体库内容 |
| 媒体图片 | `/Items/{id}/Images/Primary` | 图片代理 |
| 媒体库 | `/Users/{uid}/Views` | 媒体库列表 |
| 会话 | `/Sessions` | 正在播放 |
| 系统信息 | `/System/Info` | 服务器名称/版本 |
| 活动日志 | `/System/ActivityLog/Entries` | 最近活动 |

### 6.2 TMDB API

| 数据 | TMDB 端点 | 用途 |
|------|-----------|------|
| 剧集搜索 | `/search/tv` | 完结监控添加 |
| 剧集详情 | `/tv/{id}` | 状态、集数、播出日期、last/next episode |
| 剧集外部 ID | `/tv/{id}/external_ids` | 获取 tvdb_id/imdb_id，用于匹配 TVmaze |
| 单集详情 | `/tv/{id}/season/{season}/episode/{episode}` | 更新通知的单集标题、简介、剧照、评分、片长 |
| 人物详情 | `/person/{id}` | 当前 NFO 自动化不再依赖旧人物 zip 生成流程；保留 TMDB 客户端给其他功能复用 |

### 6.3 TVmaze API

| 数据 | TVmaze 端点 | 用途 |
|------|-------------|------|
| 剧集匹配 | `/lookup/shows?thetvdb={id}` / `/lookup/shows?imdb={id}` | 用 TMDB external_ids 匹配 TVmaze show |
| 单集列表 | `/shows/{tvmaze_id}/episodes` | 匹配 season/episode，获取 `airstamp` 并转北京时间 |

TVmaze 当前不需要 API Key；匹配或请求失败时不影响原有 TMDB 更新通知，会降级为 TMDB 播出日期。

### 6.4 Telegram API

| 数据 | Telegram 端点 | 用途 |
|------|---------------|------|
| 文本消息 | `/bot{token}/sendMessage` | 通知降级发送 |
| 图片消息 | `/bot{token}/sendPhoto` | 带图片通知；更新通知优先单集剧照，缺失时使用剧集海报 |

## 7. 数据流

### 7.1 配置保存

```text
前端设置页
  → PUT /api/config
  → 写 /data/config.json
  → 后续 TMDB/TG/代理读取新配置
```

### 7.2 添加监控

```text
前端搜索 TMDB
  → POST /api/monitor/add
  → 写 /data/monitored_series.json
  → 异步补充 TMDB 详情
  → 可选发送 TG 通知
```

### 7.3 定时检测

```text
APScheduler
  → 读 /data/monitored_series.json
  → 调 TMDB /tv/{id}
  → 对比状态/最新集（含当天或更早的 next_episode_to_air）
  → 新集补拉 TMDB 单集详情
  → 用 TMDB external_ids 匹配 TVmaze 并获取北京时间播出时间
  → 发送 TG 通知（单集剧照优先，缺失自动降级）
  → 写回 monitored_series.json
  → 追加 monitor_log.json
```

### 7.4 NFO 自动化

```text
前端浏览选择演员目录
  → GET /api/nfo/automation/browse 读取 NFO_MEDIA_ROOT 下目录
  → POST /api/nfo/automation/scan 统计 Season 1 内 .strm/同名图片(.jpg/.jpeg/.png/.webp)/.nfo，并返回缺图、缺 nfo、单集发布时间状态
  → POST /api/nfo/automation/tvshow 保存 tvshow.nfo（写媒体目录，不写 /data）
  → POST /api/nfo/automation/upload-artwork 上传 poster/fanart/logo（写媒体目录，不写 /data）
  → POST /api/nfo/automation/upload-episode-images 上传剧集图片为 IMG_UPLOAD_*.JPG
  → POST /api/nfo/automation/pornhub-published/batch-write 批量抓取 PornHub 发布时间并写入每集 aired/premiered
  → POST /api/nfo/automation/execute 重命名剧集图片、生成每集 nfo
  → 默认按 NFO_MEDIA_ROOT → EMBY_MEDIA_ROOT 映射精准刷新当前 Emby 演员目录，找不到则全库刷新
```

NFO 自动化不写入 `/data`。保存 `tvshow.nfo`、上传 `poster/fanart/logo`、批量写入 PornHub 发布时间后，前端会自动重新扫描当前演员目录并调用 `POST /api/nfo/automation/refresh-emby` 精准刷新当前 Emby 演员目录；演员目录扫描概览也提供手动重新扫描和刷新按钮。

## 8. 备份与迁移

需要保留用户配置和监控状态时，备份 Docker volume 对应目录：

```text
monitor_data/config.json
monitor_data/monitored_series.json
monitor_data/monitor_log.json
```

迁移步骤：

1. 停止旧容器。
2. 复制 `monitor_data` 到新机器。
3. 新 docker-compose 挂载同一路径到 `/data`。
4. 启动新容器。
5. 打开 Web 设置页确认配置。

## 9. 数据结构变更注意事项

1. JSON 字段新增必须兼容旧数据缺字段。
2. 不要破坏 `tmdb_id` 唯一定位逻辑。
3. 配置字段变更要同步：
   - `backend/app/config.py`
   - `backend/app/routers/monitor.py`
   - 前端设置表单
   - `DATABASE.md`
   - `API.md`
4. 不要把敏感值写进 README、测试快照或日志。
5. NFO 自动化写媒体目录，不写 `/data`；保存/上传类操作不自动刷新 Emby，执行自动化或手动刷新按钮才触发刷新。

## 10. 文档发送优先级

- `AI_CONTEXT.md`：⭐⭐⭐⭐⭐ 新会话从 GitHub 拉取/接手 Emby Manager 时开头读一次，了解项目后同一对话不必重复读取
- `PROJECT.md`：⭐⭐⭐ 大功能、架构相关时发
- `DATABASE.md`：⭐⭐ 数据库/JSON 持久化改动时发
- `API.md`：⭐⭐ 接口改动时发

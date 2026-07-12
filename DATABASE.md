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

## 6. `/data/settings.json`

### 6.1 用途

保存新侧边栏 `设置` 页面里的 DeepSeek 翻译配置。

涉及模块：

```text
backend/app/settings_store.py
backend/app/routers/settings.py
backend/app/deepseek_client.py
```

### 6.2 主结构

```json
{
  "deepseek": {
    "api_key": "不要在文档里写真实 key",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "batch_size": 10
  }
}
```

字段说明：

| 字段 | 类型 | 说明 | 默认值/兜底 |
|------|------|------|-------------|
| `api_key` | string | DeepSeek API Key；GET 接口不回显完整值 | 空时回落 `DEEPSEEK_API_KEY` |
| `base_url` | string | DeepSeek OpenAI 兼容接口地址 | `https://api.deepseek.com` |
| `model` | string | 翻译模型 | `deepseek-chat` |
| `batch_size` | int | 文件名批量翻译数量 | `10` |

注意事项：

- `api_key` 不允许写入日志或接口响应。
- 保存设置时不传 `api_key` 表示保留旧值；传空字符串表示清空已保存 Key 并回落环境变量。
- 配置读取优先级：`/data/settings.json` 中保存的 Key > `DEEPSEEK_API_KEY` > 未配置。

## 7. 文件整理日志 `/data/file-organizer/logs/*.json`

### 7.1 用途

记录 `媒体整理` 页第二步视频移动/重命名执行结果，便于追踪失败项和历史操作。旧文件名仍保留为 `/data/file-organizer/logs/*.json`。

### 7.2 日志内容

每次执行写一个时间戳 JSON 文件，包含：

```text
task_type
payload
items[].source_path
items[].target_path
items[].relative_path
items[].ok
items[].error
items[].will_overwrite
```

日志中不要写入 DeepSeek API Key。视频移动不覆盖目标视频、不自动回滚；媒体整理会按计划移动/重命名视频、同名图片，并可生成每集 `.nfo`。

## 8. 外部数据源

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

### 7.4 媒体整理

```text
前端媒体整理页
  → GET /api/media-organizer/browse?root=strm 浏览 STRM 根目录并选择演员目录
  → POST /api/media-organizer/tvshow 保存 tvshow.nfo（复用 nfo 路由能力，写媒体目录，不写 /data；tags 同时写入 <tag>/<genre>）
  → POST /api/media-organizer/upload-artwork 上传 poster/fanart/logo（写媒体目录，不写 /data）
  → GET /api/media-organizer/browse?root=cloud115 浏览 115 挂载并选择源/目标目录
  → POST /api/media-organizer/scan 扫描视频与同名图片，识别文件名前缀发布时间，并返回 clean_title 作为每集 NFO 英文简介来源
  → POST /api/media-organizer/translate 调 DeepSeek 翻译标题
  → POST /api/media-organizer/suggest-next-episode 根据目标目录建议下一集集数
  → POST /api/media-organizer/precheck 检查目标冲突
  → POST /api/media-organizer/execute 移动/重命名视频与同名图片，可生成每集 .nfo（title 写中文标题，plot 写清洗后的英文标题，不含日期/viewkey/下划线）
  → 写 /data/file-organizer/logs/*.json 记录执行结果
```

媒体整理页面不写传统数据库。`tvshow.nfo`、封面图、每集 `.nfo`、视频和图片都直接写入挂载媒体目录；执行日志仍写入 `/data/file-organizer/logs/*.json`。目录浏览响应统一使用 `directories` 字段，`root=strm` 额外保留 `dirs` 兼容旧前端。

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
5. 媒体整理写媒体目录，不写传统数据库；执行日志写 `/data/file-organizer/logs/*.json`。前端调用 `/media-organizer/...`，由 `fetchJSON` 自动补 `/api`。

## 10. 文档发送优先级

- `AI_CONTEXT.md`：⭐⭐⭐⭐⭐ 新会话从 GitHub 拉取/接手 Emby Manager 时开头读一次，了解项目后同一对话不必重复读取
- `PROJECT.md`：⭐⭐⭐ 大功能、架构相关时发
- `DATABASE.md`：⭐⭐ 数据库/JSON 持久化改动时发
- `API.md`：⭐⭐ 接口改动时发

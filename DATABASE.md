# DATABASE.md

## 数据库类型

Emby Manager **不维护传统关系型数据库**。运行时通过 API 实时获取数据，本地仅以 **JSON 文件** 形式持久化配置与监控数据。

## 本地持久化存储

### 存储方式
- **类型**: JSON 文件
- **存储路径**: `/data/`（Docker volume 挂载）
- **读取优先级**: JSON 文件 → 环境变量兜底

### 数据表

#### 表：`/data/config.json`

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| tmdb_api_key | string | TMDB API Key | "a1b2c3..." |
| tg_bot_token | string | Telegram Bot Token | "123456:ABC-DEF" |
| tg_chat_id | string | TG 接收用户/群 ID | "123456789" |
| proxy_url | string | HTTP 代理地址 | "http://192.168.1.100:7890" |
| update_template | string | 更新提醒消息模板 | "📺 {update_title}..." |
| end_template | string | 完结提醒消息模板 | "🎬 {end_title}..." |
| check_interval_minutes | int | 检测间隔（分钟） | 30 |

**用途**: 存储用户在 Web 界面配置的 TMDB / TG / 代理 / 模板设置
**索引**: 无（JSON 文件顺序读取）
**外键**: 无

---

#### 表：`/data/monitored_series.json`

主结构：
```json
{
  "series": [ /* 监控剧集列表 */ ]
}
```

每条剧集记录字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| tmdb_id | int | TMDB 剧集 ID（主键） |
| title | string | 剧名 |
| poster_url | string | 海报 URL |
| added_at | string | 添加时间（ISO 格式） |
| last_status | string | 上次检测状态（Returning Series / Ended / Canceled） |
| last_episode_air_date | string | 最新一集播出日期 |
| last_episode_number | int | 最新集号 |
| notified_ended | bool | 是否已发送完结通知 |

**用途**: 存储用户添加的监控剧集及检测状态
**索引**: tmdb_id（唯一标识）
**外键**: 无

---

#### 表：`/data/monitor_log.json`

```json
[
  {
    "time": "2026-06-30T01:00:00",
    "status": "ok",
    "message": "检查完成 · 5 部剧 · 1 更新 · 0 完结"
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| time | string | 检查时间（ISO 格式） |
| status | string | 状态（ok / warning） |
| message | string | 检查结果描述 |

**用途**: 记录每次定时检测的结果
**最大记录数**: 100 条（自动裁剪旧数据）
**索引**: 无（按时间倒序读取）

## 外部 API 数据源

### Emby API 数据

| 数据类型 | Emby 端点 | 获取方式 |
|---------|-----------|---------|
| 用户信息 | `/Users`, `/Users/{id}` | HTTP GET |
| 媒体统计 | `/Items/Counts` | HTTP GET |
| 会话信息 | `/Sessions` | HTTP GET |
| 媒体项目 | `/Items` | HTTP GET |
| 系统信息 | `/System/Info` | HTTP GET |
| 媒体库列表 | `/Users/{uid}/Views` | HTTP GET |
| 活动日志 | `/System/ActivityLog/Entries` | HTTP GET |
| 用户头像 | `/Users/{id}/Images/Primary` | HTTP GET (代理) |
| 媒体图片 | `/Items/{id}/Images/Primary` | HTTP GET (代理) |

### TMDB API 数据

| 数据类型 | TMDB 端点 | 用途 |
|---------|-----------|------|
| 剧集搜索 | `GET /search/tv` | 搜索剧集 |
| 剧集详情 | `GET /tv/{id}` | 获取状态/下集/最新集/总集数/简介/评分 |

### Telegram API

| 数据类型 | TG 端点 | 用途 |
|---------|---------|------|
| 发送消息 | `POST /bot{token}/sendMessage` | 发送文本通知 |
| 发送图片 | `POST /bot{token}/sendPhoto` | 发送带海报的通知 |

## 数据流说明

```
用户操作 → 前端 → API → JSON 文件 / 外部 API
                                             
添加监控:  前端 → POST /api/monitor/add → JSON 保存 → 异步 TMDB 查详情 → TG 通知
定时检测:  APScheduler → 读 JSON → TMDB API → 对比状态 → TG 通知 → 写 JSON
配置保存:  前端 → PUT /api/config → 写入 /data/config.json
配置读取:  前端 → GET /api/config → 读 JSON → 返回（环境变量兜底）
```

## 表关系图

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  /data/         │     │  /data/             │     │  /data/         │
│  config.json    │     │  monitored_series.  │     │  monitor_log.   │
│                 │     │  json               │     │  json           │
│  (独立配置)      │     │                     │     │                 │
│                 │     │  tmdb_id (PK)       │     │  (时间倒序日志)  │
│                 │     │  last_status        │     │                 │
│                 │     │  notified_ended     │     │  max 100 条     │
└─────────────────┘     └─────────────────────┘     └─────────────────┘
        │                        │
        │                        │ (监控列表引用 TMDB ID)
        ▼                        ▼
  环境变量兜底           TMDB API (外部数据源)
```

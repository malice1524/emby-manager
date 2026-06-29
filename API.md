# API.md

## 模块：系统

### 健康检查
- **请求地址**: `GET /api/health`
- **请求参数**: 无
- **返回参数**: `{"status": "ok"}`
- **权限要求**: 无
- **调用示例**:
```bash
curl http://localhost:8117/api/health
```

---

## 模块：仪表盘

### 获取概览数据
- **请求地址**: `GET /api/dashboard/overview`
- **请求参数**: 无
- **返回参数**:
```json
{
  "media": { "movies": 5832, "series": 206, "episodes": 5817 },
  "users": { "total": 4, "admins": 2 },
  "sessions": { "active": 19, "streams": [...] },
  "libraries": 19,
  "server": { "name": "Malice", "version": "4.8.11.0" }
}
```
- **权限要求**: 无

### 获取最近添加
- **请求地址**: `GET /api/dashboard/recent`
- **请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 12 | 返回数量（1-50） |
| types | string | 否 | Movie,Series | 媒体类型 |
| parent_id | string | 否 | "" | 按媒体库 ID 过滤 |
| exclude_parent_ids | string | 否 | "" | 排除的媒体库 ID（逗号分隔） |
| search | string | 否 | "" | 搜索关键词 |

- **返回参数**: `{"items": [{"id", "name", "type", "year", "overview", "rating", "image_url"}]}`

### 获取仪表盘统计（活动日志）
- **请求地址**: `GET /api/dashboard/stats`
- **返回参数**: `{"activity": [...], "system": {...}}`

### 获取媒体详情
- **请求地址**: `GET /api/dashboard/item/{item_id}`
- **返回参数**: `{"id", "name", "overview", "type", "year", "rating", "genres", "tmdb_id", "imdb_id", "tmdb_url", "imdb_url", "cast": [...]}`

### 删除媒体
- **请求地址**: `DELETE /api/dashboard/item/{item_id}`
- **返回参数**: `{"status": "ok"}`
- **权限要求**: 需要配置 `EMBY_ADMIN_PW`

### 图片代理
- **请求地址**: `GET /api/dashboard/images/{item_id}`
- **请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| w | int | 否 | 400 | 图片宽度 |
| type | string | 否 | item | 图片类型：item/user |

- **返回**: 图片二进制（Cache-Control: max-age=86400）

---

## 模块：用户管理

### 获取用户列表
- **请求地址**: `GET /api/users`
- **返回参数**: `{"users": [{"id", "name", "avatar_url", "has_password", "is_admin", "is_disabled", "last_login", "last_active", "created"}]}`

### 创建用户
- **请求地址**: `POST /api/users`
- **请求参数**: `name`(query, 必填), `password`(query, 可选)
- **返回参数**: `{"status": "ok", "id": "..."}`

### 删除用户
- **请求地址**: `DELETE /api/users/{user_id}`
- **返回参数**: `{"status": "ok"}`

### 修改密码
- **请求地址**: `PUT /api/users/{user_id}/password`
- **请求体**: `{"new_pw": "新密码"}`
- **返回参数**: `{"status": "ok"}`

### 修改用户策略
- **请求地址**: `PUT /api/users/{user_id}/policy`
- **请求体**: `{"IsDisabled": true}`
- **返回参数**: `{"status": "ok"}`

---

## 模块：媒体库管理

### 获取媒体库列表
- **请求地址**: `GET /api/libraries`
- **返回参数**:
```json
{
  "libraries": [{
    "id": "f930834e...", "name": "欧美电影", "type": "movies",
    "counts": { "movies": 359, "series": 0, "episodes": 0, "total": 359 }
  }]
}
```

### 获取媒体库内容
- **请求地址**: `GET /api/libraries/{item_id}/items`
- **请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 30 | 返回数量 |
| page | int | 否 | 0 | 页码 |
| search | string | 否 | "" | 搜索关键词 |
| types | string | 否 | "" | 类型过滤：movies/tvshows |

- **返回参数**: `{"items": [...], "total": 76}`

---

## 模块：完结监控

### TMDB 搜索剧集
- **请求地址**: `GET /api/tmdb/search?q=xxx&page=1`
- **权限要求**: 需要配置 TMDB API Key
- **返回参数**:
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

### TMDB 获取剧集详情
- **请求地址**: `GET /api/tmdb/detail/{tmdb_id}`
- **返回参数**:
```json
{
  "tmdb_id": 95557,
  "title": "凡人修仙传",
  "status": "Returning Series",
  "type": "动画",
  "vote_average": 8.5,
  "number_of_episodes": 200,
  "next_episode_to_air": { "air_date": "2026-07-06", "episode_number": 181, "season_number": 1 },
  "last_episode_to_air": { "air_date": "2026-06-29", "episode_number": 180, "season_number": 1 },
  "last_air_date": "2026-06-29",
  "overview": "..."
}
```

### 验证 TMDB API Key
- **请求地址**: `GET /api/tmdb/verify`
- **返回参数**: `{"valid": true}` 或 `{"valid": false, "error": "..."}`

### 获取监控列表
- **请求地址**: `GET /api/monitor/list`
- **返回参数**:
```json
{
  "series": [{
    "tmdb_id": 95557,
    "title": "凡人修仙传",
    "poster_url": "...",
    "current_status": "Returning Series",
    "notified_ended": false,
    "next_episode": { "air_date": "2026-07-06", "episode_number": 181 },
    "last_episode": { "air_date": "2026-06-29", "episode_number": 180 },
    "total_episodes": 200,
    "type": "动画",
    "vote_average": 8.5
  }]
}
```

### 添加监控剧集
- **请求地址**: `POST /api/monitor/add`
- **请求体**: `{"tmdb_id": 95557, "title": "凡人修仙传", "year": "2020", "poster_url": "..."}`
- **返回参数**: `{"success": true, "notification_sent": false}`
- **说明**: 立即返回，异步查询 TMDB 详情并发送通知

### 删除监控剧集
- **请求地址**: `DELETE /api/monitor/{tmdb_id}`
- **返回参数**: `{"success": true}`

### 获取运行状态
- **请求地址**: `GET /api/monitor/status`
- **返回参数**:
```json
{
  "last_check_time": "2026-06-30T01:00:00",
  "next_check_time": "2026-06-30T01:30:00",
  "monitored_count": 5,
  "last_notification_time": "2026-06-30T00:30:00",
  "is_running": true
}
```

### 获取检查日志
- **请求地址**: `GET /api/monitor/logs?limit=50`
- **返回参数**:
```json
[
  { "time": "2026-06-30T01:00:00", "status": "ok", "message": "检查完成 · 5 部剧"}
]
```

---

## 模块：配置管理

### 获取配置
- **请求地址**: `GET /api/config`
- **返回参数**:
```json
{
  "tmdb_api_key": "...",
  "tg_bot_token": "...",
  "tg_chat_id": "...",
  "proxy_url": "http://192.168.1.100:7890",
  "update_template": "📺 ...",
  "end_template": "🎬 ...",
  "check_interval_minutes": 30
}
```

### 保存配置
- **请求地址**: `PUT /api/config`
- **请求体**: 同 GET 返回结构，字段值为 `"__skip__"` 时跳过更新
- **返回参数**: `{"success": true}`
- **说明**: 如果 `check_interval_minutes` 变化，自动重启定时任务

### 测试 TG 通知
- **请求地址**: `POST /api/config/test`
- **返回参数**: `{"success": true}` 或 `{"success": false, "error": "..."}`

### 测试代理连通性
- **请求地址**: `POST /api/config/test-proxy`
- **返回参数**: `{"success": true, "message": "代理连接成功"}` 或 `{"success": false, "error": "..."}`
- **说明**: 用配置的代理访问 google.com 检测连通性

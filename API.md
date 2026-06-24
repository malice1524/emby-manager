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
  "sessions": {
    "active": 19,
    "streams": [{ "username": "Malice", "client": "Emby Web", "device": "Chrome",
                  "now_playing": "影片名", "play_state": "playing",
                  "item_id": "64351", "progress": 45.2, "has_playing": true,
                  "image_url": "/api/dashboard/images/64351?w=200" }]
  },
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

- **返回参数**: `{"items": [{"id": "64351", "name": "影片名", "type": "Movie", "year": 2023, "overview": "...", "rating": 8.5, "image_url": "/api/dashboard/images/64351?w=400"}]}`

### 获取仪表盘统计（活动日志）
- **请求地址**: `GET /api/dashboard/stats`
- **返回参数**: `{"activity": [{"name": "活动名", "short_overview": "...", "date": "2026-06-23T...", "severity": "Info"}], "system": {...}}`

### 获取媒体详情（含 TMDB 信息）
- **请求地址**: `GET /api/dashboard/item/{item_id}`
- **返回参数**:
```json
{
  "id": "64351", "name": "云秀行", "overview": "...", "type": "Series",
  "year": 2026, "rating": 8.0,
  "genres": ["剧情", "喜剧"],
  "tmdb_id": "239901", "imdb_id": "tt29489359",
  "tmdb_url": "https://www.themoviedb.org/tv/239901",
  "imdb_url": "https://www.imdb.com/title/tt29489359",
  "cast": [{"name": "李一桐", "role": "Fan Yun", "type": "Actor", "person_id": "31954", "avatar_url": "/api/dashboard/images/31954?w=100"}],
  "image_url": "/api/dashboard/images/64351?w=400"
}
```

### 删除媒体
- **请求地址**: `DELETE /api/dashboard/item/{item_id}`
- **请求参数**: 无
- **返回参数**: `{"status": "ok"}`
- **权限要求**: 需要配置 `EMBY_ADMIN_PW` 环境变量

### 图片代理
- **请求地址**: `GET /api/dashboard/images/{item_id}`
- **请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| w | int | 否 | 400 | 图片宽度（50-1200） |
| type | string | 否 | item | 图片类型：item/user |

- **返回**: 图片二进制数据

---

## 模块：用户管理

### 获取用户列表
- **请求地址**: `GET /api/users`
- **返回参数**:
```json
{
  "users": [{
    "id": "fb1f0470...", "name": "Malice",
    "avatar_url": "/api/dashboard/images/fb1f0470...?w=80&type=user",
    "has_password": true, "is_admin": true, "is_disabled": false,
    "last_login": "2026-06-22T...", "last_active": "2026-06-23T...",
    "created": "2026-06-08T..."
  }]
}
```

### 创建用户
- **请求地址**: `POST /api/users`
- **请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | query | 是 | 用户名 |
| password | query | 否 | 密码 |

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
    "id": "129", "name": "动画电影", "type": "movies",
    "locations": ["/media/电影/动画电影"],
    "counts": { "movies": 5832, "series": 206, "episodes": 5817, "total": 11855 }
  }]
}
```

### 获取媒体库内容
- **请求地址**: `GET /api/libraries/{item_id}/items`
- **请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 30 | 返回数量（1-100） |
| page | int | 否 | 0 | 页码 |
| search | string | 否 | "" | 搜索关键词 |
| types | string | 否 | "" | 媒体类型：movies/tvshows |

- **返回参数**: `{"items": [{"id": "41019", "name": "冰雪奇缘", "type": "Movie", "year": 2013, "runtime_min": 102, "has_image": true}], "total": 76}`

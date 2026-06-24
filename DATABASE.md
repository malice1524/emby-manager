# DATABASE.md

## 数据库类型

Emby Manager **不维护独立数据库**。所有数据通过 Emby REST API 实时获取，以 JSON 格式传输，不在服务器端持久化存储。

## 数据来源

| 数据类型 | 来源 | 获取方式 |
|---------|------|---------|
| 用户信息 | Emby API (`/Users`, `/Users/{id}`) | HTTP GET |
| 媒体统计 | Emby API (`/Items/Counts`) | HTTP GET |
| 会话信息 | Emby API (`/Sessions`) | HTTP GET |
| 媒体项目 | Emby API (`/Items`) | HTTP GET |
| 系统信息 | Emby API (`/System/Info`) | HTTP GET |
| 媒体库列表 | Emby API (`/Users/{id}/Views`) | HTTP GET |
| 活动日志 | Emby API (`/System/ActivityLog/Entries`) | HTTP GET |
| 用户头像 | Emby API (`/Users/{id}/Images/Primary`) | HTTP GET (代理) |
| 媒体图片 | Emby API (`/Items/{id}/Images/Primary`) | HTTP GET (代理) |
| 演员图片 | Emby API (`/Items/{id}/Images/Primary`) | HTTP GET (代理) |

## 数据缓存

| 缓存类型 | 策略 | 说明 |
|---------|------|------|
| 图片缓存 | Cache-Control: public, max-age=86400 | CDN/浏览器缓存 24 小时 |
| 会话数据 | 15 秒轮询 | 前端每 15 秒刷新在线状态 |
| 仪表盘数据 | 页面加载时获取 | 不持久缓存 |

## 数据流

```
前端 (Vue 3)
    │
    ├── GET /api/dashboard/overview
    │   └── Emby API: Items/Counts, Sessions, Users/Public, VirtualFolders, System/Info
    │
    ├── GET /api/dashboard/recent
    │   └── Emby API: Items (按 DateCreated 排序)
    │
    ├── GET /api/dashboard/stats
    │   └── Emby API: System/ActivityLog/Entries, System/Info
    │
    ├── GET /api/dashboard/item/{id}
    │   └── Emby API: Users/{uid}/Items/{id} (含 ProviderIds, People)
    │
    ├── DELETE /api/dashboard/item/{id}
    │   └── Emby API: DELETE Items/{id} (需管理员用户令牌)
    │
    ├── GET /api/users
    │   └── Emby API: Users/Public, Users/{id}
    │
    ├── POST /api/users
    │   └── Emby API: POST Users/New + POST Users/{id}/Password
    │
    ├── DELETE /api/users/{id}
    │   └── Emby API: DELETE Users/{id}
    │
    ├── PUT /api/users/{id}/password
    │   └── Emby API: POST Users/{id}/Password
    │
    ├── PUT /api/users/{id}/policy
    │   └── Emby API: GET Users/{id} + POST Users/{id}/Policy
    │
    ├── GET /api/libraries
    │   └── Emby API: Users/{uid}/Views (获取排序) + Items/Counts
    │
    ├── GET /api/libraries/{id}/items
    │   └── Emby API: Items (带 ParentId 过滤)
    │
    ├── GET /api/dashboard/images/{id}
    │   └── Emby API: Items/{id}/Images/Primary (代理)
    │
    └── GET /api/health
        └── 返回 {"status": "ok"}
```

## 数据关系

```
Emby 服务器
    ├── 媒体库 (Items/Counts, VirtualFolders)
    │   ├── 电影 (Movie)
    │   ├── 剧集 (Series)
    │   │   ├── 季 (Season)
    │   │   │   └── 集 (Episode)
    │   └── 其他类型
    ├── 用户 (Users)
    │   ├── 基本信息
    │   ├── 策略/权限 (Policy)
    │   └── 头像 (Images/Primary)
    ├── 会话 (Sessions)
    │   ├── 播放状态
    │   ├── 客户端信息
    │   └── 当前播放项
    └── 系统信息 (System/Info)
```

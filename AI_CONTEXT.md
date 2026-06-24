# AI_CONTEXT.md — Emby Manager 项目上下文

## 项目整体架构

Emby Manager 是一个 Emby 媒体服务器 Web 管理面板，采用 **单容器前后端一体架构**。

```
用户浏览器 → FastAPI (uvicorn) → Emby API
                ↓
            静态文件 (Vue 3 SPA)
```

- **后端**: Python FastAPI，异步 httpx 调用 Emby REST API
- **前端**: Vue 3 + Element Plus，单 HTML 文件 SPA
- **部署**: 单 Docker 容器，GitHub Actions 自动构建推送到 Docker Hub
- **存储**: 无数据库，所有数据实时从 Emby API 获取

## 核心业务逻辑

### 认证
- 使用 Emby API Key (X-Emby-Token 头) 认证
- 删除操作需要额外管理员密码 (EMBY_ADMIN_PW) 获取用户令牌
- 图片代理使用 API Key 认证

### 路由
- 前端 SPA 处理所有页面路由 (`/#/`, `/#/users`, `/#/libraries`)
- 后端 API 全部在 `/api/` 路径下
- 所有其他路径返回 `index.html`（SPA 入口）

### 已实现功能
1. **仪表盘**: 概览数据、最近添加、活动日志、正在播放、图片代理、删除媒体
2. **用户管理**: CRUD、密码管理、策略管理、头像代理
3. **媒体库**: 列表、自动排序（Users/Views 顺序）、海报墙、瀑布流加载、全局搜索、详情弹窗

## 后端 API 总结

| 模块 | 端点 | 方法 | 用途 |
|------|------|------|------|
| 仪表盘 | `/api/dashboard/overview` | GET | 概览数据 |
| 仪表盘 | `/api/dashboard/recent` | GET | 最近添加 |
| 仪表盘 | `/api/dashboard/stats` | GET | 活动日志 |
| 仪表盘 | `/api/dashboard/item/{id}` | GET | 媒体详情 |
| 仪表盘 | `/api/dashboard/item/{id}` | DELETE | 删除媒体 |
| 仪表盘 | `/api/dashboard/images/{id}` | GET | 图片代理 |
| 用户 | `/api/users` | GET | 用户列表 |
| 用户 | `/api/users` | POST | 创建用户 |
| 用户 | `/api/users/{id}` | DELETE | 删除用户 |
| 用户 | `/api/users/{id}/password` | PUT | 修改密码 |
| 用户 | `/api/users/{id}/policy` | PUT | 修改策略 |
| 媒体库 | `/api/libraries` | GET | 媒体库列表 |
| 媒体库 | `/api/libraries/{id}/items` | GET | 媒体库内容 |
| 系统 | `/api/health` | GET | 健康检查 |

所有端点返回 JSON，`Content-Type: application/json`。

## 前端关键数据结构

### Dashboard 组件
```javascript
data: {
  data: {media, server, users, sessions},
  recent: [{id, name, type, year, overview, rating, image_url}],
  activity: [{name, short_overview, date, severity}],
  libraries: [{id, name, type, locations, counts}],
  showDetail, detailItem, expanded,
  activeLibrary, libraryName, _excludeIds
}
// computed: activePlaying, idleCount
// 轮询: refreshStats() 每15秒
```

### Users 组件
```javascript
data: {users: [{id, name, avatar_url, has_password, is_admin, is_disabled, last_login, last_active, created}]}
```

### Libraries 组件
```javascript
data: {libraries, libSearch, searchResults, curLib, items, total, page, loadingMore}
// 搜索: libSearch → onGlobalSearch() → fetchJSON('/dashboard/recent?search=...')
```

## 关键配置

### 环境变量
```python
EMBY_URL = os.getenv("EMBY_URL", "http://localhost:8096")
EMBY_API_KEY = os.getenv("EMBY_API_KEY", "")
HEADERS = {"X-Emby-Token": EMBY_API_KEY}
EMBY_ADMIN_USER = os.getenv("EMBY_ADMIN_USER", "")
EMBY_ADMIN_PW = os.getenv("EMBY_ADMIN_PW", "")
```

### Docker 构建
```dockerfile
FROM python:3.12-alpine
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app/ ./app/
COPY frontend/index.html ./static/
COPY frontend/lib/ ./static/lib/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 开发规范

### 文件路径
- 后端代码: `backend/app/`（**重要**: 非根目录 `app/`）
- 前端 SPA: `frontend/index.html`（单文件应用）
- 前端依赖: `frontend/lib/`

### 代码风格
- Python: FastAPI 异步路由，类型注解，httpx AsyncClient
- JavaScript: Vue 3 Options API，Element Plus 组件，ES5 兼容语法
- CSS: 自定义变量系统，毛玻璃效果，8pt 网格间距

## 后续开发注意事项
1. 修改 `libraries.py` 确认在 `backend/app/routers/` 下
2. 前端所有逻辑在 `frontend/index.html` 的 `<script>` 中
3. 添加新路由在 `backend/app/main.py` 注册
4. 推送前必须询问用户确认
5. 小版本更新跟随用户定义的版本号
6. GitHub Actions 自动构建后需用户手动部署到 NAS

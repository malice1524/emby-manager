# AI_CONTEXT.md — Emby Manager 项目上下文

## 项目整体架构

Emby Manager 是一个 Emby 媒体服务器 Web 管理面板 + 剧集完结监控系统，采用 **单容器前后端一体架构**。

```
用户浏览器 → FastAPI (uvicorn) → Emby API / TMDB API / Telegram API
                ↓
            静态文件 (Vue 3 SPA) + JSON 文件存储
```

- **后端**: Python FastAPI，异步 httpx 调用外部 API
- **前端**: Vue 3 + Element Plus，单 HTML SPA
- **存储**: 无数据库，配置/监控数据存 JSON 文件（Docker volume）
- **定时任务**: APScheduler 每 N 分钟检测剧集状态
- **部署**: 单 Docker 容器，GitHub Actions 推送 Docker Hub

## 核心业务逻辑

### 认证
- Emby API Key (`X-Emby-Token` 头) 认证
- 删除操作需管理员密码 (`EMBY_ADMIN_PW`)

### 配置系统
- 配置优先读 JSON 文件 → 环境变量兜底
- 所有配置可在 Web 界面 ⚙️ 设置中修改，即时生效
- 配置文件：`config.json` / `monitored_series.json` / `monitor_log.json`

### 完结监控流程
```
1. 用户通过 TMDB 搜索添加剧集到监控列表
2. APScheduler 定时触发 check_series()
3. 遍历监控列表，调 TMDB API 获取最新状态
4. 检测更新（last_episode_air_date 变化）→ TG 通知
5. 检测完结（status: Returning Series → Ended）→ TG 通知
6. 更新 JSON，记录检查日志
```

### 通知模板
- 默认模板支持 `{series_name}`、`{episode_info}`、`{air_date}` 等变量
- 模板校验：保存时检测未知变量，提示但不阻止
- 通知发送：优先 `sendPhoto`（带海报），失败降级为 `sendMessage`
- 简介截断：完结通知简介仅显示前 4 行

## 后端 API 总结

| 模块 | 端点 | 方法 | 用途 |
|------|------|------|------|
| 仪表盘 | `/api/dashboard/*` | GET/DELETE | 概览、最近添加、详情、删除、图片代理 |
| 用户 | `/api/users*` | GET/POST/DELETE/PUT | 用户 CRUD、密码、策略 |
| 媒体库 | `/api/libraries*` | GET | 列表、数量统计、子项查询 |
| TMDB | `/api/tmdb/*` | GET | 搜索、详情、验证 Key |
| 监控 | `/api/monitor/*` | GET/POST/DELETE | 列表、添加、删除、状态、日志 |
| 配置 | `/api/config*` | GET/PUT/POST | 读取、保存、测试 TG、测试代理 |
| 系统 | `/api/health` | GET | 健康检查 |

共 **24 个 API 端点**（含子路径）。

## 前端关键数据结构

### Monitor 组件
```javascript
data: {
  searchQuery, searchResults: [], searching, searchError,
  monitoredList: [], loadingList, refreshing,
  showSettings: false,
  filterStatus: 'all',  // all / continuing / ended
  monitorStatus: null,
  logs: [],
  activeCollapse: []
}
computed: {
  filteredList() // 按 filterStatus 筛选
}
methods: {
  doSearch(), addSeries(), deleteSeries(),
  loadList(), refreshList(), loadStatus(), loadLogs(),
  fmtTime2(), daysUntil()
}
```

### SettingsDialog 组件
```javascript
data: {
  form: { tmdb_api_key, tg_bot_token, tg_chat_id, proxy_url, update_template, end_template, check_interval_minutes },
  verifying, tmdbVerifyResult,
  testing, tgTestResult,
  proxyTesting, proxyTestResult,
  saving, saveWarn,
  showUpdateVars, showEndVars,
  isMobile
}
methods: {
  loadConfig(), verifyTmdb(), testTg(), testProxy(),
  save(), resetDefaults(), validateTemplate()
}
```

## 关键配置

### config.py
```python
MONITOR_DATA_DIR = os.getenv("MONITOR_DATA_DIR", "/data")
CONFIG_PATH = os.path.join(MONITOR_DATA_DIR, "config.json")
MONITORED_SERIES_PATH = os.path.join(MONITOR_DATA_DIR, "monitored_series.json")

def load_tg_config():
    # 优先读 JSON，没有则用环境变量兜底

def get_http_client():
    # 返回带代理的 httpx.AsyncClient（如配置了代理）
```

## 开发规范

### 文件路径
- **后端代码**: `backend/app/`（根目录 `app/` 是旧副本，修改两端需同步）
- **前端 SPA**: `frontend/index.html`（单文件，约82KB）
- **前端依赖**: `frontend/lib/`

### 代码风格
- Python: FastAPI 异步路由，类型注解，httpx AsyncClient
- JavaScript: Vue 3 Options API，Element Plus 组件，ES5 兼容语法
- CSS: 自定义变量系统，暗色毛玻璃主题，8pt 网格

### 推送前必须询问用户确认
### 版本号规则
每次推送代码时，版本号加 0.01（如 1.10 → 1.11）。到 0.09 后进位到 0.10（如 1.09 → 1.10）。版本号写在 VERSION 和 static/VERSION，两个文件同步。

## 后续开发注意事项
1. 新路由在 `backend/app/main.py` 注册 `app.include_router()`
2. 修改 `libraries.py` 需同步 `backend/app/routers/` 和 `app/routers/`
3. Dockerfile 使用 `backend/` 下的代码，`frontend/` 下的静态文件
4. 环境变量作为兜底，优先从 JSON 文件读取
5. 新静态文件（JS/CSS）放 `frontend/lib/` 并复制到 `backend/static/lib/`
6. TG 通知调用走 `get_http_client()` 自动支持代理

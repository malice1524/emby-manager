# Emby Manager 项目文档

## 项目简介

### 项目名称
Emby Manager

### 项目目标
为 Emby 媒体服务器提供现代化的 Web 管理面板，支持跨网络访问、用户管理、媒体库浏览、剧集完结监控等管理功能，替代 Emby 原生管理界面的不便之处。

### 核心功能
- 📊 **仪表盘** — 服务器状态、媒体统计、活跃会话实时监控
- 👥 **用户管理** — 创建/删除用户、修改密码、启用/禁用账户
- 📂 **媒体库** — 所有媒体库浏览、海报墙展示、按类型显示数量统计
- 🖼️ **海报浏览** — 瀑布流加载、海报缩放、点击查看详情
- 🌐 **跨网络访问** — 图片代理功能，解决内外网跨域问题
- 🔍 **全局搜索** — 跨所有媒体库搜索媒体内容
- 🔔 **完结监控** — 剧集状态检测、TMDB 数据查询、Telegram 通知推送
- ⚙️ **自定义配置** — Web界面配置 TMDB Key、TG Bot、代理地址、通知模板

## 技术栈

### 后端框架
| 技术 | 版本 | 用途 |
|------|------|------|
| Python FastAPI | 3.12+ | Web API 框架 |
| httpx | latest | 异步 HTTP 客户端（调用 Emby/TMDB/Telegram API） |
| apscheduler | 3.10+ | 定时任务调度 |
| uvicorn | latest | ASGI 服务器 |

### 前端框架
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue.js | 3.5.38 | 前端 SPA 框架 |
| Vue Router | 4.6.4 | 前端路由 |
| Element Plus | latest | UI 组件库 |
| HTML/CSS | — | 自定义样式（暗色毛玻璃主题） |

### 存储
- **配置存储**: JSON 文件（`/data/config.json`、`/data/monitored_series.json`、`/data/monitor_log.json`）
- **持久化**: Docker volume 挂载

### Docker 部署
| 文件 | 说明 |
|------|------|
| Dockerfile | 单容器构建文件（Python + 静态文件） |
| docker-compose.yml | NAS 部署配置模板 |
| GitHub Actions | CI/CD 自动构建并推送到 Docker Hub |

## 项目目录结构

```
emby-manager/
├── .github/workflows/           # GitHub Actions 工作流
│   └── deploy.yml               # 自动构建 Docker 镜像并推送到 Docker Hub
├── backend/                     # Python FastAPI 后端（主代码）
│   ├── app/                     # 应用主目录
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 入口、路由注册、SPA 静态文件服务
│   │   ├── config.py            # 配置：环境变量 + JSON 文件读取（优先级：JSON > 环境变量）
│   │   ├── tmdb_client.py       # TMDB API 封装（搜索剧集、获取详情、验证 API Key）
│   │   ├── tg_notifier.py       # Telegram 通知发送（更新提醒、完结提醒、自定义模板）
│   │   ├── series_monitor.py    # 剧集监控核心（定时检测、状态对比、通知触发、日志记录）
│   │   └── routers/             # 路由模块
│   │       ├── dashboard.py     # 仪表盘 API（概览、最近添加、图片代理、删除媒体）
│   │       ├── users.py         # 用户管理 API（CRUD、密码、策略）
│   │       ├── libraries.py     # 媒体库 API（列表、数量统计、子项查询）
│   │       └── monitor.py       # 完结监控 API（TMDB搜索/详情/验证、监控CRUD、配置读写/测试、状态/日志）
│   ├── requirements.txt         # Python 依赖
│   └── static/                  # 前端静态文件（构建后复制至此）
│       ├── index.html           # Vue SPA 入口
│       ├── favicon.png
│       ├── VERSION
│       └── lib/                 # 前端依赖库（Vue、Element Plus 等）
├── frontend/                    # 前端源码
│   ├── index.html               # 完整 SPA（Vue 3 + Element Plus，约82KB）
│   ├── nginx.conf               # Nginx 配置（前端独立部署时使用）
│   └── lib/                     # 前端依赖库
├── docker-compose.hub.yml       # Docker Hub 部署模板
├── docker-compose.yml           # 本地 Docker Compose 配置
├── Dockerfile                   # 单容器 Docker 构建文件
├── VERSION                      # 版本号
├── favicon.png
├── README.md
├── PROJECT.md
├── API.md
├── DATABASE.md
└── AI_CONTEXT.md
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    用户浏览器 (手机/桌面)                         │
│                   Vue 3 SPA + Element Plus                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Docker 容器 (单一容器)                            │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │              uvicorn (FastAPI ASGI Server)                    ││
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐   ││
│  │  │  SPA 服务    │  │  API 路由    │  │ 定时任务           │   ││
│  │  │ (静态文件)   │  │ (REST API)  │  │ (APScheduler)     │   ││
│  │  └─────────────┘  └──────┬───────┘  └───────────────────┘   ││
│  └──────────────────────────┼──────────────────────────────────┘│
└─────────────────────────────┼──────────────────────────────────┘
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌────────────────┐ ┌──────────┐ ┌──────────────┐
    │ Emby Media      │ │ TMDB API │ │ Telegram API │
    │ Server          │ │ (剧集    │ │ (通知推送)   │
    │ (内网/公网)      │ │  数据)   │ │              │
    └────────────────┘ └──────────┘ └──────────────┘
```

### 架构说明
1. **单容器部署** — 后端 API + 前端 SPA + 定时任务都在一个 Docker 容器中
2. **无独立数据库** — 所有数据实时从 Emby/TMDB API 获取；配置和监控列表存 JSON 文件
3. **图片代理** — 前端图片请求走后端代理，解决内外网跨域问题
4. **认证方式** — 使用 Emby API Key 认证，删除操作需额外管理员密码
5. **定时检测** — APScheduler 每 N 分钟检测剧集状态变化，触发 TG 通知

## 已实现功能

### ✅ 仪表盘
- [x] Hero 区域：服务器信息、媒体统计（电影/剧集/单集数）
- [x] 最近添加海报墙 + 媒体库筛选
- [x] 默认显示指定媒体库 + 排除特定媒体库
- [x] 最近活动日志
- [x] 正在播放：当前播放用户、进度条、海报缩略图
- [x] 15 秒自动刷新在线状态
- [x] 详情弹窗：TMDB/IMDb 链接、演员列表、简介
- [x] 删除媒体按钮

### ✅ 用户管理
- [x] 查看用户列表（头像、名称、角色、状态）
- [x] 新建/删除用户
- [x] 修改密码（带确认密码验证）
- [x] 启用/禁用用户

### ✅ 媒体库管理
- [x] 媒体库列表（卡片展示）
- [x] 按类型显示数量统计
- [x] 海报墙 + 瀑布流加载
- [x] 媒体搜索（实时搜索关键词）
- [x] 详情弹窗（TMDB/IMDb 链接、演员列表）

### ✅ 完结监控
- [x] TMDB 搜索剧集
- [x] TMDB API Key 验证
- [x] 监控列表管理（添加/删除）
- [x] 剧集状态检测（连载中/已完结/已取消）
- [x] 定时自动检测（APScheduler，间隔可配置）
- [x] TG 更新提醒（新增一集时通知）
- [x] TG 完结提醒（状态变为已完结时通知）
- [x] 自定义通知模板（更新/完结分别可配置）
- [x] 检查日志记录

### ✅ 配置管理
- [x] Web 界面配置 TMDB API Key
- [x] Web 界面配置 TG Bot Token / Chat ID
- [x] Web 界面配置代理地址
- [x] Web 界面配置通知模板
- [x] Web 界面配置检测间隔
- [x] TMDB Key 验证按钮
- [x] TG 测试发送按钮
- [x] 代理连通性测试

### ✅ UI/UX
- [x] 暗色毛玻璃主题
- [x] 响应式布局（手机/平板/桌面）
- [x] 移动端 Safari 安全区域适配
- [x] 海报卡片 hover 动效
- [x] 弹窗/抽屉适配

### ✅ 部署
- [x] Docker 单容器部署
- [x] GitHub Actions 自动构建推送到 Docker Hub
- [x] 环境变量 + JSON 文件双配置

## 待开发功能

- [ ] 多语言支持（i18n）
- [ ] 批量操作（批量删除、移动）
- [ ] 播放记录统计图表
- [ ] 系统通知/告警
- [ ] 媒体库刷新/扫描触发
- [ ] OAuth 认证支持

## 配置说明

### 环境变量

| 变量名 | 必填 | 说明 | 默认值 |
|--------|------|------|--------|
| EMBY_URL | 是 | Emby 服务器地址 | http://localhost:8096 |
| EMBY_API_KEY | 是 | Emby API Key | — |
| EMBY_ADMIN_USER | 否 | Emby 管理员用户名（删除功能需要） | "Malice" |
| EMBY_ADMIN_PW | 否 | Emby 管理员密码（删除功能需要） | "" |
| TMDB_API_KEY | 否 | TMDB API Key（JSON 文件兜底） | "" |
| TG_BOT_TOKEN | 否 | Telegram Bot Token（JSON 文件兜底） | "" |
| TG_CHAT_ID | 否 | TG 接收者 ID（JSON 文件兜底） | "" |
| MONITOR_DATA_DIR | 否 | 配置/监控列表存储目录 | "/data" |

### 配置读取优先级
配置读取顺序：**JSON 文件 > 环境变量**（JSON 文件优先，没有时兜底到环境变量）

### JSON 文件说明

| 文件 | 路径 | 用途 |
|------|------|------|
| config.json | `/data/config.json` | TMDB Key / TG Token/ChatID / 代理 / 通知模板 / 检测间隔 |
| monitored_series.json | `/data/monitored_series.json` | 监控剧集列表 + 检测状态 |
| monitor_log.json | `/data/monitor_log.json` | 最近 100 条检查日志 |

## Docker 部署说明

### docker-compose 结构

```yaml
version: "3.8"

services:
  emby-manager:
    image: 1524566636/emby-manager:latest
    container_name: emby-manager
    environment:
      - EMBY_URL=http://192.168.1.7:8096    # 你的 Emby 地址
      - EMBY_API_KEY=你的API_Key              # Emby API Key
      - MONITOR_DATA_DIR=/data               # 配置文件目录
    ports:
      - "8117:8000"
    volumes:
      - ./monitor_data:/data                 # 持久化配置 + 监控数据
    restart: unless-stopped
```

### 部署步骤

```bash
# 1. 拉取最新镜像
docker pull 1524566636/emby-manager:latest

# 2. 启动
docker-compose up -d

# 3. 访问 http://你的NAS地址:8117

# 4. 打开 🔔完结监控 → ⚙️设置 → 配置 TMDB Key / TG Bot / 代理
```

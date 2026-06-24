# Emby Manager 项目文档

## 项目简介

### 项目名称
Emby Manager

### 项目目标
为 Emby 媒体服务器提供现代化的 Web 管理面板，支持跨网络访问、用户管理、媒体库浏览等核心管理功能，代替 Emby 原生管理界面的不便之处。

### 核心功能
- 📊 **仪表盘** — 服务器状态、媒体统计、活跃会话实时监控
- 👥 **用户管理** — 创建/删除用户、修改密码、启用/禁用账户
- 📂 **媒体库** — 所有媒体库浏览、海报墙展示、按类型显示数量统计
- 🖼️ **海报浏览** — 瀑布流加载、海报缩放、点击查看详情
- 🌐 **跨网络访问** — 图片代理功能，解决内外网跨域问题
- 🔍 **全局搜索** — 跨所有媒体库搜索媒体内容

## 技术栈

### 后端框架
| 技术 | 版本 | 用途 |
|------|------|------|
| Python FastAPI | 3.12+ | Web API 框架 |
| httpx | latest | 异步 HTTP 客户端（调用 Emby API） |
| uvicorn | latest | ASGI 服务器 |

### 前端框架
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue.js | 3.5.38 | 前端 SPA 框架 |
| Vue Router | 4.6.4 | 前端路由 |
| Element Plus | latest | UI 组件库 |
| HTML/CSS | — | 自定义样式（暗色毛玻璃主题） |

### 数据库
无独立数据库。依赖 Emby 服务器的数据库。

### 缓存
无独立缓存。CDN 级图片缓存（通过 Cache-Control: max-age=86400 头）。

### Docker 部署
| 文件 | 说明 |
|------|------|
| Dockerfile | 单容器构建文件（Python + 静态文件） |
| docker-compose.yml | NAS 部署配置模板 |
| GitHub Actions | CI/CD 自动构建并推送到 Docker Hub |

## 项目目录结构

```
emby-manager/
├── .github/workflows/       # GitHub Actions 工作流
│   └── deploy.yml           # 自动构建 Docker 镜像并推送到 Docker Hub
├── backend/                 # Python FastAPI 后端（主代码）
│   ├── app/                 # 应用主目录
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI 入口、路由注册、静态文件服务
│   │   ├── config.py        # 环境变量配置（Emby URL、API Key、管理员凭据）
│   │   └── routers/         # 路由模块
│   │       ├── dashboard.py # 仪表盘 API（概览、最近添加、图片代理、删除媒体）
│   │       ├── users.py     # 用户管理 API（CRUD、密码、策略）
│   │       └── libraries.py # 媒体库 API（列表、真实数量统计、子项查询）
│   ├── requirements.txt     # Python 依赖
│   └── static/              # 前端静态文件（构建后复制至此）
│       ├── index.html       # Vue SPA 入口
│       ├── favicon.png      # 网站图标
│       ├── VERSION          # 版本号文件
│       └── lib/             # 前端依赖库（Vue、Element Plus 等）
├── app/                     # 后端代码副本（必须与 backend/app/ 同步修改）
│   └── routers/
│       └── libraries.py
├── frontend/                # 前端源码
│   ├── index.html           # 完整 SPA（Vue 3 + Element Plus）
│   ├── nginx.conf           # Nginx 配置（前端独立部署时使用）
│   └── lib/                 # 前端依赖库
├── docker-compose.hub.yml   # Docker Hub 部署模板
├── docker-compose.yml       # 本地 Docker Compose 配置
├── Dockerfile               # 单容器 Docker 构建文件
├── VERSION                  # 版本号
├── favicon.png              # 项目图标
└── README.md                # 项目介绍
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户浏览器 (手机/桌面)                     │
│                   Vue 3 SPA + Element Plus                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Docker 容器 (单一容器)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           uvicorn (FastAPI ASGI Server)               │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │   │
│  │  │  SPA 服务    │  │  API 路由    │  │ 图片代理    │ │   │
│  │  │ (静态文件)   │  │ (REST API)  │  │ (httpx)    │ │   │
│  │  └─────────────┘  └──────┬───────┘  └──────┬──────┘ │   │
│  └──────────────────────────┼────────────────┼──────────┘   │
└─────────────────────────────┼────────────────┼──────────────┘
                              │ HTTP           │ HTTP
                              ▼                ▼
                    ┌──────────────────────────────────┐
                    │       Emby Media Server           │
                    │   (内网: 192.168.1.7:8096)        │
                    │   公网: 47.109.19.131:8116)       │
                    └──────────────────────────────────┘
```

### 架构说明
1. **单容器部署** — 后端 API + 前端 SPA 静态文件都在一个 Docker 容器中
2. **反向代理** — 前端所有 `/api/*` 请求由 Vue 自带 API base 转发到后端
3. **无数据库** — 所有数据实时从 Emby API 获取，不持久化存储
4. **图片代理** — 前端图片请求走后端代理，解决内外网跨域问题
5. **认证方式** — 使用 Emby API Key 认证，删除操作需额外管理员密码

## 已实现功能

### ✅ 仪表盘
- [x] Hero 区域：服务器信息、媒体统计（电影/剧集/单集数）
- [x] 最近添加海报墙：显示最新添加的媒体海报
- [x] 媒体库筛选：按媒体库过滤最近添加
- [x] 默认显示指定媒体库（当前为 欧美电影）
- [x] 排除特定媒体库显示
- [x] 最近活动日志
- [x] 正在播放：显示当前播放用户、进度条、海报缩略图
- [x] 在线人数统计
- [x] 详情弹窗：TMDB/IMDb 链接、演员列表、简介
- [x] 删除媒体按钮
- [x] 15 秒自动刷新在线状态

### ✅ 用户管理
- [x] 查看用户列表（头像、名称、角色、状态）
- [x] 新建用户（支持设置密码）
- [x] 删除用户
- [x] 修改密码（带确认密码验证）
- [x] 启用/禁用用户
- [x] 显示注册时间、最后上线时间

### ✅ 媒体库管理
- [x] 媒体库列表（卡片展示）
- [x] 按类型显示数量（电影类显示电影数、剧集类显示剧集数、混合类显示总数）
- [x] 搜索所有媒体库
- [x] 媒体库排序跟随 Emby 用户视图顺序
- [x] 海报墙展示媒体库内容
- [x] 瀑布流加载（滚动到底部自动加载更多）
- [x] 媒体搜索（实时搜索关键词）
- [x] 详情弹窗（TMDB/IMDb 链接、演员列表）
- [x] 详情弹窗删除按钮

### ✅ UI/UX
- [x] 暗色毛玻璃主题
- [x] 响应式布局（手机/平板/桌面）
- [x] 侧边栏版本号显示
- [x] Favicon 图标
- [x] 路由页面切换自动滚动到顶部
- [x] 100dvh 适配浏览器底部导航栏
- [x] 海报卡片 hover 缩放动效
- [x] 移动端海报 3 列布局
- [x] 移动端弹窗顶部避开 topbar（:top 动态绑定）
- [x] 弹窗禁止拖动（:draggable="false" + CSS 固定居中）
- [x] 弹窗底部安全区域适配（safe-area-inset-bottom）
- [x] 弹窗滚动区域使用 100dvh 防止底部被遮挡

### ✅ 图片
- [x] Emby 图片跨域代理
- [x] 用户头像代理
- [x] 演员头像代理
- [x] 图片加载失败占位符

### ✅ 部署
- [x] Docker 单容器部署
- [x] GitHub Actions 自动构建推送到 Docker Hub
- [x] 环境变量配置

## 待开发功能

- [ ] Web 界面在线配置（Emby 地址、API Key、密码等）
- [ ] 多语言支持（i18n）
- [ ] 自定义排序选项
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

### 配置文件说明
项目无独立配置文件。所有配置通过环境变量传入 Docker 容器。

## Docker 部署说明

### docker-compose 结构

```yaml
version: "3.8"

services:
  emby-manager:
    image: 1524566636/emby-manager:latest
    container_name: emby-manager
    environment:
      - EMBY_URL=http://192.168.1.7:8096    # 你的 Emby 服务器地址
      - EMBY_API_KEY=你的API_Key              # Emby API Key
      - EMBY_ADMIN_USER=Malice               # 管理员用户名（可选）
      - EMBY_ADMIN_PW=你的密码               # 管理员密码（可选）
    ports:
      - "8117:8000"                          # 映射到宿主 8117 端口
    restart: unless-stopped
```

### 部署步骤

```bash
# 1. 拉取最新镜像
docker pull 1524566636/emby-manager:latest

# 2. 删除旧容器
docker rm -f emby-manager

# 3. 启动新容器
docker run -d --name emby-manager -p 8117:8000 \
  -e EMBY_URL=http://192.168.1.7:8096 \
  -e EMBY_API_KEY=你的API_Key \
  -e EMBY_ADMIN_USER=Malice \
  -e EMBY_ADMIN_PW=你的密码 \
  --restart unless-stopped \
  1524566636/emby-manager:latest

# 4. 访问
# http://你的NAS地址:8117
```

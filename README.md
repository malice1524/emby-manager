# Emby Manager

Emby 服务器管理面板 —— 浏览媒体库、管理用户账号的 Docker 项目。

## 功能

- 📊 **仪表盘** - 服务器状态、媒体统计、活跃会话
- 👥 **用户管理** - 新建/删除用户、修改密码、启用/禁用
- 📂 **媒体库** - 浏览所有媒体库及其内容
- 📱 **响应式** - 手机/平板/桌面全适配

## 快速部署（从 Docker Hub）

### 1. 创建 docker-compose.yml

```yaml
version: "3.8"
services:
  emby-manager:
    image: 1524566636/emby-manager:latest
    container_name: emby-manager
    environment:
      - EMBY_URL=http://你的Emby地址:8096
      - EMBY_API_KEY=你的Emby_API_Key
    ports:
      - "8117:8000"
    restart: unless-stopped
```

### 2. 启动

```bash
docker-compose up -d
```

访问 `http://你的NAS:8117`

## 构建镜像（自己打包）

```bash
# 构建
docker build -t 你的用户名/emby-manager:latest .

# 推送
docker login
docker push 你的用户名/emby-manager:latest
```

## 项目结构

```
emby-manager/
├── Dockerfile              # 统一构建文件
├── docker-compose.hub.yml  # Docker Hub 部署模板
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py         # FastAPI + 静态文件服务
│       ├── config.py       # 环境变量配置
│       ├── emby_client.py  # Emby API 封装
│       └── routers/
│           ├── dashboard.py
│           ├── users.py
│           └── libraries.py
└── frontend/
    └── index.html          # Vue 3 + Element Plus SPA
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python FastAPI + httpx |
| 前端 | Vue 3 + Element Plus (CDN) |
| 部署 | Docker 单容器 |

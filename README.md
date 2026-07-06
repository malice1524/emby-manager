# Emby Manager

Emby 媒体服务器 Web 管理面板，提供仪表盘、用户管理、媒体库浏览、完结监控、NFO 生成等常用 NAS/Emby 管理能力。

## 功能特性

- 📊 **仪表盘** — 服务器状态、媒体统计、活跃会话、最近添加内容
- 👥 **用户管理** — 新建/删除用户、修改密码、启用/禁用
- 📂 **媒体库** — 海报墙浏览、搜索、分页跳转、TMDB 信息查看
- 📝 **NFO 生成** — 自定义文件名 + TMDB ID 生成演员 `.nfo` 与封面压缩包
- 🖼️ **图片代理** — 通过后端代理访问 Emby/TMDB 图片，减少跨网络加载失败
- 🔍 **全局搜索** — 跨媒体库搜索内容
- 🔔 **完结监控** — 剧集状态检测、更新提醒、完结提醒、Telegram 通知；更新通知可包含单集标题、简介、评分、片长、剧照与北京时间播出时间
- ⚙️ **Web 配置** — TMDB、Telegram、代理、Cron 检查规则均可在页面配置
- 📱 **响应式界面** — 手机、平板、桌面端适配，暗色毛玻璃风格 UI

## 安装部署

### Docker Compose 部署

创建 `docker-compose.yml`：

```yaml
version: "3.8"

services:
  emby-manager:
    image: 1524566636/emby-manager:latest
    container_name: emby-manager
    environment:
      - EMBY_URL=http://你的Emby地址:8096
      - EMBY_API_KEY=你的Emby_API_Key
      # 删除用户功能需要管理员账号密码；不使用删除功能可不填
      - EMBY_ADMIN_USER=你的Emby管理员用户名
      - EMBY_ADMIN_PW=你的Emby管理员密码
      - MONITOR_DATA_DIR=/data
    ports:
      - "8117:8000"
    volumes:
      - ./monitor_data:/data
    restart: unless-stopped
```

启动：

```bash
docker-compose up -d
```

访问：

```text
http://你的NAS地址:8117
```

DockerHub 镜像：

```text
1524566636/emby-manager:latest
```

`main` 分支更新后会自动构建 latest 镜像。

## 环境变量说明

| 变量 | 必填 | 说明 |
|------|------|------|
| `EMBY_URL` | ✅ | Emby 服务器地址，需包含 `http://` 或 `https://` |
| `EMBY_API_KEY` | ✅ | Emby 后台生成的 API Key |
| `EMBY_ADMIN_USER` | ❌ | Emby 管理员用户名，删除用户功能需要 |
| `EMBY_ADMIN_PW` | ❌ | Emby 管理员密码，删除用户功能需要 |
| `TMDB_API_KEY` | ❌ | TMDB API Key；Web 界面可配置，此项作为兜底 |
| `TG_BOT_TOKEN` | ❌ | Telegram Bot Token；Web 界面可配置，此项作为兜底 |
| `TG_CHAT_ID` | ❌ | Telegram 接收 ID；Web 界面可配置，此项作为兜底 |
| `MONITOR_DATA_DIR` | ❌ | 配置/监控数据目录，默认 `/data` |

## 获取 Emby API Key

1. 打开 Emby Web 界面
2. 进入：控制台 → 高级 → API 密钥
3. 点击「新建 API 密钥」
4. 填入名称并确认
5. 复制生成的 API Key 到 `EMBY_API_KEY`

## Web 界面配置

完结监控相关配置均可在 Web 界面完成：

- TMDB API Key
- Telegram Bot Token / Chat ID
- 代理地址与连通性测试
- Cron 检查规则，例如 `*/30 * * * *`

部署后打开：

```text
🔔 完结监控 → ⚙️ 设置
```

填写配置后即可开始使用。

## NFO 生成功能

入口：

```text
📝 NFO 生成
```

使用方式：

1. 输入自定义文件名
2. 输入 TMDB ID
3. 可选上传自定义封面
4. 生成并下载 zip 压缩包

压缩包内容：

```text
自定义文件名.nfo
自定义文件名.jpg/png/webp
```

NFO 示例：

```xml
<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<actor>
  <name>从 TMDB 抓取</name>
  <tmdbid>输入的 TMDB ID</tmdbid>
  <thumb>自定义文件名.jpg</thumb>
</actor>
```

如果未上传封面，会默认使用 TMDB 头像。

## 常见问题

**Q: 完结监控页面不显示或搜索失败？**
A: 检查 TMDB API Key 是否正确，容器网络是否能访问 TMDB；如使用代理，请在设置中配置代理并测试连通性。

**Q: Telegram 通知发送失败？**
A: 检查 TG Bot Token 和 Chat ID 是否正确，可在设置页面使用测试发送功能。更新通知中的具体播出时间优先来自 TVmaze（免 API Key，按 TMDB 的 tvdb/imdb 外部 ID 匹配并转北京时间）；查不到时会自动降级为 TMDB 播出日期，不影响基础通知。

**Q: 图片加载不出来？**
A: 确认 `EMBY_URL` 配置正确。项目已内置后端图片代理，通常不需要浏览器直接访问 Emby/TMDB 图片源。

**Q: 删除用户失败，提示 API Key 不能删除？**
A: 删除用户需要管理员登录凭据，请在 Docker Compose 中配置 `EMBY_ADMIN_USER` 和 `EMBY_ADMIN_PW` 后重启容器。

**Q: 更新镜像后页面样式没有变化？**
A: 项目已对 SPA 入口添加 `Cache-Control: no-cache, no-store, must-revalidate`。如仍有缓存，可强制刷新浏览器或清理站点缓存。

**Q: 媒体库弹窗分页看不到或弹窗能上下拖动？**
A: 请更新到最新镜像。当前版本已固定媒体库弹窗位置，分页固定可见，海报区域在弹窗内部滚动。

## 本地开发

```bash
cd backend
pip install -r requirements.txt
export EMBY_URL=http://你的Emby地址:8096
export EMBY_API_KEY=你的API_Key
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

浏览器打开：

```text
http://localhost:8000
```

前端主要文件：

```text
frontend/index.html
static/index.html
```

修改前端后需保持 `frontend/index.html` 与 `static/index.html` 同步。

## 更新日志

### v1.17 当前

- 📂 媒体库弹窗位置固定
  - 桌面/iPad 端上下留白一致
  - 弹窗外层不再上下滚动/拖动
  - 搜索框与分页固定可见
  - 海报列表在弹窗内部滚动
- 📄 媒体库分页增强
  - 支持总数展示、页码、上一页/下一页、跳页
- 🎨 媒体库卡片优化
  - 卡片显示电影/剧集数量
  - 副文案统一为「点击查看全部」
- 🐛 删除接口失败提示优化
  - 明确提示管理员账号密码配置要求

### v1.16

- 📂 媒体库弹窗缩小高度
- 修复分页被弹窗高度挤出的问题
- 保持弹窗外壳固定，只让海报区域滚动

### v1.15

- 🔔 完结监控搜索结果简介两行省略
- 修复简介过长导致页面横向撑开/缩放的问题
- 优化完结监控刷新按钮图标与 loading 状态
- 仪表盘最近添加默认分类调整为「欧美电影」
- SPA 入口增加 no-cache 响应头，降低浏览器缓存导致 UI 不一致的问题

### v1.14 及更早

- 📝 新增 NFO 生成功能
- 🔔 新增剧集完结监控模块
- ⚙️ 新增 Web 配置系统
- 🎨 UI 全面优化：暗色主题、毛玻璃卡片、移动端适配
- 📂 媒体库排序跟随 Emby 用户视图顺序
- 🖼️ 新增图片代理能力

# Emby Manager

Emby 媒体服务器 Web 管理面板

## 功能特性

- 📊 **仪表盘** — 服务器状态、媒体统计、活跃会话
- 👥 **用户管理** — 新建/删除用户、修改密码、启用/禁用
- 📂 **媒体库** — 海报墙浏览、搜索、TMDB 信息查看
- 🖼️ **图片代理** — 跨网络图片访问
- 🔍 **全局搜索** — 跨媒体库搜索
- 🔔 **完结监控** — 剧集状态检测 + Telegram 通知
- 📱 **响应式** — 手机/平板/桌面全适配

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

访问 `http://你的NAS地址:8117`

部署后打开 🔔完结监控 → ⚙️ 设置，配置 TMDB API Key、TG Bot Token/ChatID、代理地址即可开始使用。

## 环境变量说明

| 变量 | 必填 | 说明 |
|------|------|------|
| EMBY_URL | ✅ | Emby 服务器地址（含 http://） |
| EMBY_API_KEY | ✅ | Emby 后台生成的 API Key |
| EMBY_ADMIN_USER | ❌ | 管理员用户名（删除功能需要） |
| EMBY_ADMIN_PW | ❌ | 管理员密码（删除功能需要） |
| TMDB_API_KEY | ❌ | TMDB API Key（Web界面可配置，此为兜底） |
| TG_BOT_TOKEN | ❌ | TG Bot Token（Web界面可配置，此为兜底） |
| TG_CHAT_ID | ❌ | TG 接收ID（Web界面可配置，此为兜底） |
| MONITOR_DATA_DIR | ❌ | 配置文件目录（默认 /data） |

## 获取 Emby API Key

1. 打开 Emby Web 界面 → 控制台 → 高级 → API 密钥
2. 点击「新建 API 密钥」，填入名称，确定
3. 复制生成的密钥

## Web 界面配置

完结监控的所有配置（TMDB Key、TG Token、代理地址、通知模板、检测间隔）都可以在 Web 界面 ⚙️ 设置中填写，**无需修改环境变量**。

## 常见问题

**Q: 完结监控页面不显示？**
A: 检查 Docker 日志，确认 TMDB API Key 配置正确且有网络连接。

**Q: 设置抽屉背景白色？**
A: 请确保使用最新版本镜像，或清除浏览器缓存后重新加载。

**Q: TG 通知发送失败？**
A: 检查 TG Bot Token 和 Chat ID 是否正确，或在设置中测试发送。

**Q: 图片加载不出来？**
A: 该问题已通过后端图片代理解决，确保 EMBY_URL 配置正确。

## 本地开发部署

```bash
cd backend
pip install -r requirements.txt
export EMBY_URL=http://你的Emby地址:8096
export EMBY_API_KEY=你的API_Key
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

然后浏览器打开 http://localhost:8000

## 更新日志

### v1.12 (当前)
- 🔔 剧集完结监控模块
  - TMDB 搜索/详情/验证 API
  - 监控列表管理（添加/删除/状态展示）
  - APScheduler 定时检测（间隔可配置）
  - TG 更新提醒 + 完结提醒（带海报图片）
  - 自定义通知模板（更新/完结分别配置）
- ⚙️ Web 界面配置系统
  - TMDB API Key、TG Bot Token/ChatID
  - 代理地址 + 连通性测试
  - 自定义通知模板
  - 检测间隔配置
- 🎨 UI/UX
  - 完结监控页面（搜索/列表/筛选/状态/日志）
  - 设置抽屉组件（替代弹窗，避免遮挡）
  - 暗色主题全面适配
  - 移动端 Safari 安全区域适配
- 🐛 Bug 修复
  - 配置读取回显问题
  - 模板无法清空问题
  - 按钮白底问题
  - 弹窗/抽屉遮挡问题
  - 添加剧集延迟优化（异步处理）

### v1.11
- UI 全面优化：色彩系统升级、毛玻璃卡片精修
- Safari 手机端海报 3 列修复
- 媒体库排序跟随 Emby 用户视图顺序
- 瀑布流加载 + 弹窗固定修复

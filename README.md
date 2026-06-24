# Emby Manager

Emby 媒体服务器 Web 管理面板

## 功能特性

- 📊 **仪表盘** — 服务器状态、媒体统计、活跃会话
- 👥 **用户管理** — 新建/删除用户、修改密码、启用/禁用
- 📂 **媒体库** — 海报墙浏览、搜索、TMDB 信息查看
- 🖼️ **图片代理** — 跨网络图片访问，解决内外网跨域
- 🔍 **全局搜索** — 跨媒体库搜索媒体内容
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
      - EMBY_ADMIN_USER=Malice        # 可选，删除功能需要
      - EMBY_ADMIN_PW=你的密码         # 可选，删除功能需要
    ports:
      - "8117:8000"
    restart: unless-stopped
```

启动：

```bash
docker-compose up -d
```

访问 `http://你的NAS:8117`

### Docker 直接部署

```bash
docker run -d --name emby-manager -p 8117:8000 \
  -e EMBY_URL=http://192.168.1.7:8096 \
  -e EMBY_API_KEY=你的Emby_API_Key \
  -e EMBY_ADMIN_USER=Malice \
  -e EMBY_ADMIN_PW=你的密码 \
  --restart unless-stopped \
  1524566636/emby-manager:latest
```

## 环境变量说明

| 变量 | 必填 | 说明 |
|------|------|------|
| EMBY_URL | ✅ | Emby 服务器地址（含 http://） |
| EMBY_API_KEY | ✅ | Emby 后台生成的 API Key |
| EMBY_ADMIN_USER | ❌ | 管理员用户名（删除功能需要） |
| EMBY_ADMIN_PW | ❌ | 管理员密码（删除功能需要） |

## 获取 Emby API Key

1. 打开 Emby Web 界面 → 控制台 → 高级 → API 密钥
2. 点击「新建 API 密钥」
3. 填入名称（如 "Emby Manager"），点击确定
4. 复制生成的密钥

## 常见问题

**Q: 页面显示空白/侧边栏可见但内容不显示？**
A: 检查 EMBY_API_KEY 和 EMBY_URL 是否正确，用新版镜像重建容器。

**Q: 删除按钮无效？**
A: 需要设置 EMBY_ADMIN_USER 和 EMBY_ADMIN_PW 环境变量。

**Q: 图片加载不出来？**
A: 该问题已通过后端图片代理解决，确保 EMBY_URL 配置正确。

**Q: 更新后需要重建容器吗？**
A: 是的，`docker pull` 后需要 `docker rm -f` + `docker run`。

## 本地开发部署

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt

# 2. 设置环境变量
export EMBY_URL=http://你的Emby地址:8096
export EMBY_API_KEY=你的API_Key

# 3. 启动后端
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 浏览器打开 http://localhost:8000
```

## 更新日志

### v1.11 (当前)
- UI 全面优化：色彩系统升级、毛玻璃卡片精修、侧边栏新样式
- Safari 手机端海报 3 列修复
- 媒体库排序跟随 Emby 用户视图顺序
- 媒体库全局搜索功能
- 瀑布流加载 + 弹窗固定修复

### v1.10
- 版本号同步

### v1.09
- 媒体库全局搜索
- 瀑布流加载
- 弹窗固定修复

### v1.08
- 移除排序参数，跟随 Emby 默认排序

### v1.07
- 弹窗定位修复
- 移动端 3 列
- 默认排序

### v1.06
- Favicon 图标
- 默认动画电影
- 100dvh 适配

### v1.05
- 删除按钮修复（管理员密码认证）
- 排除媒体库

### v1.04
- 海报 5 列
- 路由滚动置顶
- 删除按钮修复
- 弹窗偏移

### v1.03
- 排除媒体库
- 弹窗遮挡修复

### v1.02
- 侧边栏版本号
- encode 修复
- 弹窗遮挡修复

### v1.01
- 初始版本
- 仪表盘：画廊风格仪表盘
- 用户管理：CRUD
- 媒体库：海报墙
- GitHub Actions 自动构建

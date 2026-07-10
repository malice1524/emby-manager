# MeTube 下载上传仪表盘设计规格

## 目标

在 Emby Manager 中新增「下载上传」页面，并在侧边栏「仪表盘」下面加入入口，用于监控 MeTube 下载队列与 115 上传进度。

## 用户确认的范围

- 不放在首页内容区，新增独立页面「下载上传」。
- 侧边栏位置：仪表盘下面。
- 页面采用完整监控界面：当前 115 上传进度大卡、MeTube 下载概览、115 上传状态概览、失败项列表。
- 失败项必须列出来，错误信息需脱敏，不能暴露 user_key、token、cookie、password 等敏感值。
- 不实现下载/上传控制操作；本次只读监控。

## 后端设计

新增接口：

```text
GET /api/dashboard/metube
```

数据来源：

```text
/vol1/1000/docker/metube/uploader/upload-progress.json
/vol1/1000/docker/metube/uploader/upload-state.json
http://127.0.0.1:8081/history
```

返回结构：

```json
{
  "available": true,
  "progress": {
    "filename": "xxx.mp4",
    "status": "uploading",
    "uploaded_bytes": 123,
    "total_bytes": 456,
    "percent": 26.97,
    "updated_at": "2026-07-10 21:57:22",
    "error": ""
  },
  "metube": {
    "finished": 46,
    "downloading": 2,
    "pending": 128,
    "preparing": 0,
    "failed": 0,
    "total": 176
  },
  "uploader": {
    "total": 68,
    "statuses": {
      "deleted_local_after_confirm": 28,
      "waiting_remote_confirm": 16,
      "unstable": 8,
      "upload_failed": 1
    }
  },
  "failed": [
    {
      "filename": "xxx.mp4",
      "size": 512593843,
      "size_text": "488.85 MB",
      "updated_at": "2026-07-10 21:37:28",
      "error_type": "MultipartUploadAbort",
      "error": "MultipartUploadAbort: {... 'user_key': '[redacted]' ...}"
    }
  ]
}
```

当数据源不可用时返回 `available:false` 和错误摘要，首页其他功能不能受影响。

## 前端设计

新增 Vue 组件 `DownloadUpload`，路由：

```text
/download-upload
```

侧边栏新增：

```text
<a href="#/download-upload"><span class="nav-icon">⬆️</span> 下载上传</a>
```

页面布局：

```text
下载上传
MeTube 下载队列与 115 上传进度监控

┌───────────────────────────────┬───────────────────┐
│ 当前上传大卡                   │ 下载/上传统计      │
│ 百分比 + 阶段时间线            │ 队列数字/异常数量  │
└───────────────────────────────┴───────────────────┘

┌───────────────────────────────────────────────────┐
│ 上传失败列表                                      │
└───────────────────────────────────────────────────┘
```

移动端布局：单列，大进度卡在上，统计和失败列表在下。

刷新策略：页面 mounted 时加载一次，每 5 秒刷新一次，离开页面清理定时器。

## 样式要求

- 沿用当前 Emby Manager 深色玻璃风格。
- 上传进度使用大号百分比 + 渐变进度条。
- 失败数量和失败列表使用红色语义色。
- 长文件名允许换行或中间截断，不撑破移动端布局。

## 测试要求

- 后端测试覆盖：接口读取进度、统计状态、失败错误脱敏、MeTube 不可用降级。
- 前端测试覆盖：侧边栏入口、路由存在、页面包含进度条和失败列表文案。
- 同步修改 `frontend/index.html` 和 `static/index.html`。
- 不 push，除非用户明确说“推送”。

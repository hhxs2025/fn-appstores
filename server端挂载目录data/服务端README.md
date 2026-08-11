# FN软仓 服务端

## 简介

FN软仓 服务端是 FN软仓 的后端服务，提供应用列表 API 和 `.fpk` 文件下载。开发者可以自托管此服务端，成为 FN软仓客户端的一个“软件源”。

**v2.2.0 新增功能**：支持通过 `notice.json` 向所有客户端推送公告，公告内容支持 Markdown 渲染。

**镜像拉取**：
```bash
docker pull ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.2.0
```


## 版本功能对比

| 功能 | v2.1.0 | v2.2.0 |
|------|:---:|:---:|
| **应用列表 API** | ✅ `/api/apps` | ✅ `/api/apps` |
| **FPK 文件下载** | ✅ `/apps/<filename>` | ✅ `/apps/<filename>` |
| **应用图标服务** | ✅ `/icons/<filename>` | ✅ `/icons/<filename>` |
| **应用截图服务** | ✅ `/previews/<app_id>/<filename>` | ✅ `/previews/<app_id>/<filename>` |
| **健康检查** | ✅ `/health` | ✅ `/health` |
| **公告板接口** | ❌ 不支持 | ✅ `/api/notice` |
| **公告内容格式** | — | ✅ Markdown 渲染 |
| **数据目录** | `data/` | `data/`（新增 `notice.json`） |
| **部署方式** | Docker / Docker Compose | Docker / Docker Compose |


## 环境要求

- Docker 20.10+
- Docker Compose 2.0+（可选）
- 公网域名或 FRP 穿透（如需对外提供服务）


## 快速开始

### 1. 拉取镜像

```bash
docker pull ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.2.0
```

### 2. 准备数据目录

```bash
mkdir -p data/{apps,icons,previews}
```

将 `fn-appstores.json` 放入 `data/` 目录，将 `.fpk` 安装包放入 `data/apps/`，图标放入 `data/icons/`，截图放入 `data/previews/{app_id}/`。

如需发布公告，在 `data/` 目录下创建 `notice.json`。

### 3. 启动容器

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p 5660:5660 \
  -v $(pwd)/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.2.0
```

## 目录结构

```
fn-appstores-server/
├── data/                       # 应用数据（挂载目录）
│   ├── fn-appstores.json       # 应用清单（必须）
│   ├── notice.json             # 公告内容（可选，v2.2.0新增）
│   ├── apps/                   # .fpk 安装包
│   │   ├── myapp-1.0.0.fpk
│   │   └── ...
│   ├── icons/                  # 应用图标
│   │   ├── myapp.PNG
│   │   └── ...
│   └── previews/               # 应用截图
│       └── {app_id}/
│           ├── 1.PNG
│           └── 2.PNG
├── app.py                      # 服务端程序
└── vendor/                     # Python 依赖
```


## 配置文件

### `fn-appstores.json` 格式

```json
[
  {
    "id": "myapp",
    "name": "我的应用",
    "version": "1.0.0",
    "desc": "应用描述信息",
    "author": "作者名",
    "tags": "分类标签",
    "repo": "https://gitee.com/xxx/xxx"
  }
]
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 应用唯一标识，需与文件名对应 |
| `name` | ✅ | 应用显示名称 |
| `version` | ✅ | 版本号，用于生成 `{id}-{version}.fpk` |
| `desc` | ❌ | 应用描述 |
| `author` | ❌ | 作者 |
| `tags` | ❌ | 分类标签（逗号分隔） |
| `repo` | ❌ | 源码仓库地址 |

> **注意**：`fn-appstores.json` 中列出的每个应用，`data/apps/` 目录下必须有对应的 `{id}-{version}.fpk` 文件，否则该应用不会被加载。


### `notice.json` 格式（v2.2.0 新增）

`notice.json` 是 v2.2.0 新增的公告配置文件，放置在 `data/` 目录下。客户端会在“关于”页面展示公告内容。

```json
{
  "enabled": true,
  "title": "📢FN软仓2.2.0正式版发布",
  "summary": "新增公告板功能，支持多源管理",
  "content": "### 🎉FN软仓2.2.0 正式版发布\n\n#### 新增功能\n- **公告板**：新增公告推送功能便于服务端推送公告信息\n- **多源管理**：用户可自助添加/删除服务端源\n\n- **鸣谢以下内置源应用提供者**\n- 豪子:文件收集器；snltty:在线fpk打包;\n\n-**欢迎更多开发者加入FN软仓生态，参与多源建设或提供应用支援！**",
  "updated_at": "2026-08-08"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `enabled` | ✅ | 是否启用公告，`true` 或 `false` |
| `title` | ❌ | 公告标题（客户端横幅显示） |
| `summary` | ❌ | 公告摘要（客户端横幅显示） |
| `content` | ✅ | 公告正文，支持 Markdown 格式 |
| `updated_at` | ❌ | 更新时间，建议格式 `YYYY-MM-DD` |

> **提示**：修改 `notice.json` 后，如未生效请重启容器。


## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/apps` | GET | 获取应用列表，支持 `?force=true` 强制刷新 |
| `/api/notice` | GET | 获取公告内容（v2.2.0新增） |
| `/apps/<filename>` | GET | 下载 `.fpk` 文件 |
| `/icons/<filename>` | GET | 获取应用图标 |
| `/previews/<app_id>/<filename>` | GET | 获取应用截图 |
| `/health` | GET | 健康检查 |


## 更新应用数据或公告

添加/修改应用或公告只需：

1. 更新 `data/fn-appstores.json` 或 `data/notice.json`
2. 放入对应的 `.fpk` 和图标（如有新增）
3. 重启容器

## 客户端配置

用户安装 FN软仓客户端 v2.2.0+ 后，可通过“源管理”添加你的服务端地址：

1. 打开 FN软仓 → 点击底部「源管理」Tab
2. 点击「添加源」，输入：
   - **源名称**：自定义（如“我的应用源”）
   - **源地址**：`http://你的服务器IP:5660`
3. 点击「测试」验证连通性，确认后点击「添加」

添加成功后，应用列表会自动合并展示该源的所有应用，同时“关于”页面会展示你发布的公告。

> **注意**：服务端设备需配置公网 IP 或内网穿透（如 FRP）并开放 5660 端口。


## 常见问题

### Q：服务端启动后 `/api/apps` 返回空数据？

1. 检查 `data/fn-appstores.json` 是否存在且格式正确
2. 检查 `data/apps/` 目录下是否有对应的 `.fpk` 文件
3. 查看容器日志：`docker logs fn-appstores-server`

### Q：公告不显示？

1. 检查 `data/notice.json` 是否存在且格式正确
2. 确认 `enabled` 字段为 `true`
3. 确认 `content` 字段不为空
4. 检查客户端是否 v2.2.0 或以上版本
5. 查看容器日志：`docker logs fn-appstores-server`

### Q：端口 5660 被占用怎么办？

修改启动命令中的端口映射，如改为 `-p 5661:5660`，客户端添加源时使用对应端口即可。

### Q：如何更新应用数据或公告？

1. 更新 `data/fn-appstores.json` 或 `data/notice.json`
2. 添加/替换 `data/apps/` 中的 `.fpk` 文件
3. 重启容器：`docker restart fn-appstores-server`


## 版本信息

- **当前版本**：2.2.0
- **作者**：晦华先生
- **反馈**：2303537063@qq.com
- **开源地址**：[https://gitee.com/hhxs2025/fn-appstores](https://gitee.com/hhxs2025/fn-appstores)


## 版本记录

### v2.2.0（当前版本）
- 新增公告板接口 `/api/notice`
- 支持 `data/notice.json` 配置公告内容
- 公告内容支持 Markdown 格式渲染
- 启动时自动检测 `notice.json` 是否存在
- 文档完善，增加公告配置说明
- 镜像仓库迁移至腾讯云容器镜像服务（CCR）

### v2.1.0
- 基础应用列表 API
- FPK 文件下载服务
- 应用图标和截图服务
- 健康检查接口
# FN软仓服务端 自托管搭建教程

> 适用于三方源搭建者（树状聚合架构下的节点）


## 📌 适用人群

本教程面向希望自建 FN软仓服务端（软件源）的开发者。搭建完成后，你可以将自己的应用发布到自建源中，并提交给 FN软仓官方审核，审核通过后所有用户都能浏览和安装你收录的应用。

**如果你只是普通用户，不需要搭建服务端，直接使用 FN软仓客户端即可。**


## 🎯 搭建前的准备

| 项目 | 说明 |
|------|------|
| **飞牛 fnOS 系统** | 或其他支持 Docker 的 Linux 系统 |
| **Docker** | 版本 20.10+ |
| **公网访问** | 公网 IP 或内网穿透（如 FRP），用于对外提供服务 |
| **应用素材** | `.fpk` 安装包、图标（PNG 格式）等 |


## 📁 数据目录结构

```
data/
├── fn-appstores.json          # 应用清单（必须）
├── apps/                      # .fpk 安装包
│   ├── myapp-1.0.0.fpk
│   └── ...
├── icons/                     # 应用图标（PNG 格式）
│   ├── myapp.PNG
│   └── ...
└── previews/                  # 应用截图（可选）
    ├── myapp/
    │   ├── 1.PNG
    │   └── 2.PNG
    └── ...
```


## 📄 应用清单格式

在 `data/` 目录下创建 `fn-appstores.json` 文件。

### 飞牛本地托管模式（推荐）

FPK 文件直接放在 `data/apps/` 目录中，**JSON 中无需填写 `download_url` 和 `icon` 字段**，服务端会自动扫描并生成。

```json
[
  {
    "id": "myapp",
    "name": "我的应用",
    "version": "1.0.0",
    "desc": "应用描述信息",
    "author": "作者名",
    "tags": "工具,效率",
    "updated_at": "2026-08-30"
  }
]
```

> **💡 必填字段**：`id`、`name`、`version`，其他字段可选。

**服务端自动生成规则**：

| JSON 字段 | 自动生成的地址 |
|-----------|---------------|
| `download_url` | `{BASE_URL}/apps/{id}-{version}.fpk` |
| `icon` | `{BASE_URL}/icons/{id}.PNG` |
| `screenshots` | `{BASE_URL}/previews/{id}/1.PNG` 等 |

**本地文件必须匹配**：

| JSON 中的 `id` 和 `version` | 对应的本地文件 |
|----------------------------|---------------|
| `"id": "myapp"` + `"version": "1.0.0"` | `data/apps/myapp-1.0.0.fpk` |
| `"id": "myapp"` | `data/icons/myapp.PNG` |
| `"id": "myapp"` | `data/previews/myapp/1.PNG` |


### Gitee 托管模式（进阶）

如需将 FPK 托管在 Gitee 等平台，则需填写 `download_url` 和 `icon` 字段指向直链地址：

```json
[
  {
    "id": "myapp",
    "name": "我的应用",
    "version": "1.0.0",
    "desc": "应用描述信息",
    "author": "作者名",
    "tags": "工具,效率",
    "updated_at": "2026-08-30",
    "download_url": "https://gitee.com/你的用户名/仓库名/raw/master/apps/myapp-1.0.0.fpk",
    "icon": "https://gitee.com/你的用户名/仓库名/raw/master/icons/myapp.PNG"
  }
]
```

> **两种模式的区别**：
> - **飞牛本地托管**：FPK 存放在飞牛本地，下载速度快，配置简单，JSON 更简洁
> - **Gitee 托管**：FPK 存放在 Gitee，服务端只提供统计入口，适合没有公网 IP 的场景


### 🛠️ 使用工具快速生成（推荐）

手动编写 JSON 容易出错，建议使用以下工具辅助：

- **FN软仓应用上架助手.exe**：配置好服务端地址后，拖入 FPK 文件即可一键完成所有上架操作（自动生成 JSON、重命名文件、整理目录结构），无需手动编写任何配置。
- **fpk信息提取器.exe**：拖入 FPK 文件，自动提取应用信息并生成上架所需的 JSON 内容，同时按规范格式重命名 FPK 和图标文件。

使用上述工具可大幅减少手动配置的工作量，尤其适合批量上架多个应用的场景。工具获取途径——QQ群:2154077576


## 🚀 搭建步骤

### 步骤一：拉取镜像

```bash
docker pull ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:latest
```

> 如需指定版本，可将 `latest` 替换为具体版本号，如 `2.5.3`。


### 步骤二：准备数据目录

**方式一：飞牛本地托管（推荐）**

在飞牛 NAS 中创建 `data/` 目录，放入以下内容：

```
/path/to/data/
├── fn-appstores.json          # 应用清单
├── apps/
│   └── myapp-1.0.0.fpk        # FPK 安装包
└── icons/
    └── myapp.PNG              # 应用图标
```

> 使用上架助手可自动生成 `fn-appstores.json` 并整理好目录结构。


**方式二：Gitee 托管**

1. 在 Gitee 创建仓库（如 `fn-appstores`）
2. 将 `data/` 目录推送到仓库
3. 在 `fn-appstores.json` 中填写 Gitee 直链地址

```bash
git clone https://gitee.com/你的用户名/fn-appstores.git
cd fn-appstores
# 放入 data/ 目录
git add .
git commit -m "首次提交"
git push
```


### 步骤三：配置内网穿透（如需公网访问）

如果你的服务端需要被外网访问（大多数情况），需要进行内网穿透配置。

**推荐使用 frpc 容器**（比客户端更稳定）：

| 配置项 | 说明 |
|--------|------|
| 本地端口 | `5660`（与服务端容器端口一致） |
| 远程端口 | 自定义（如 `5660`），需在 `BASE_URL` 中保持一致 |

配置完成后，获取公网访问地址：
```
http://你的公网IP或域名:远程端口
```


### 步骤四：启动容器

**⚠️ 关键配置**：必须设置 `BASE_URL` 为你的公网访问地址，否则图标、截图、下载地址将无法正确生成。

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p 5660:5660 \
  -e TZ=Asia/Shanghai \
  -e BASE_URL="http://你的公网IP或域名:远程端口" \
  -e ADMIN_PASSWORD="你的管理密码" \
  -v /path/to/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:latest
```

**参数说明**：

| 参数 | 说明 |
|------|------|
| `-d` | 后台运行 |
| `--name` | 容器名称 |
| `--restart unless-stopped` | 自动重启 |
| `-p 5660:5660` | 端口映射（宿主机:容器） |
| `-e BASE_URL` | **必填**：你的公网访问地址 |
| `-e ADMIN_PASSWORD` | 管理后台密码（默认 admin123） |
| `-v /path/to/data:/app/data` | 挂载数据目录 |


### 步骤五：验证服务

```bash
# 本地测试
curl http://127.0.0.1:5660/api/apps

# 公网测试
curl http://你的公网IP或域名:5660/api/apps
```

正常返回 JSON 格式的应用列表即表示部署成功。


### 步骤六：访问管理后台

```
http://你的服务器IP:5660/admin
```

使用 `ADMIN_PASSWORD` 设置的密码登录。管理后台提供公告管理、三方源管理、数据查看、应用编辑等功能。


## ⚠️ 重要提示：不要聚合其他源

**请勿在 `data/upstream.json` 中配置三方源进行多层聚合！**

### 为什么？

```
┌─────────────┐
│   你的服务端  │  ← 如果你又聚合了其他源，形成多层聚合
└──────┬───────┘
       │
┌──────▼───────┐
│  官方聚合源   │  ← 官方已经聚合了你
└──────────────┘
```

- 你搭建服务端的目的是作为“树枝”被官方源聚合
- 如果你再去聚合其他源，会形成 **多层聚合链**
- 多层聚合会导致 **应用重复、版本混乱、响应变慢**

### 正确做法

1. **只发布自己的应用**，不配置 `upstream.json`
2. 将你的 `BASE_URL` 提交给 FN软仓官方审核
3. 审核通过后，你的应用会自动出现在官方源中


## 🧪 可选：提交你的源给官方审核

如果你希望自己的应用出现在 FN软仓官方源中，可将你的 `BASE_URL` 提交给管理员审核。

**提交方式**：
- QQ 群：2154077576（联系管理员）
- 上架表单：https://f.wps.cn/ksform/w/write/L7KeYAD1


## 📚 参考文档

| 内容 | 说明 |
|------|------|
| 应用清单完整字段说明 | 见服务端说明书“应用清单格式”章节 |
| 管理后台功能说明 | 见服务端说明书“管理后台”章节 |
| API 接口清单 | 见服务端说明书“API 接口”章节 |
| 树状聚合架构原理 | 见服务端说明书“树状聚合架构”章节 |


## 💬 技术交流

- 用户交流群：QQ 1039270739
- 代码仓库：https://gitee.com/hhxs2025/fn-appstores
- 问题反馈：https://gitee.com/hhxs2025/fn-appstores/issues

---

> **文档更新日期**：2026-08-30
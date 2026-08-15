# FN软仓服务端 自托管搭建指南

## 一、概述

FN软仓服务端是一个基于 Docker 的轻量级应用商店后端服务，提供应用列表 API 和 `.fpk` 文件下载。开发者可以自托管此服务端，成为 FN软仓客户端的一个“软件源”。

其他用户通过 FN软仓客户端（v2.2.0+）添加你的服务端地址后，即可浏览和安装你收录的应用，并在“关于”页面查看你发布的公告。


### 版本特性概览

| 版本 | 核心功能 |
| :--- | :--- |
| **v2.1.0** | 基础服务：应用列表 API、FPK 下载、图标/截图服务、健康检查 |
| **v2.2.0** | 新增公告板（`notice.json`），支持 Markdown 渲染 |
| **v2.3.0** | 新增应用下载统计（SQLite 持久化）、统计接口、强制刷新接口、自动提取 app_id |
| **v2.3.1** | 新增 `BASE_URL` 环境变量支持，解决跨设备/中继访问时图标和截图 404 的问题 |
| **v2.4.0** | 新增树状聚合架构，支持 `upstream.json` 三方源白名单聚合，官方源可作为统一入口分发三方源应用 |


## 二、环境要求

- 飞牛 fnOS 系统（或任意支持 Docker 的 Linux 系统）
- Docker 20.10+
- 公网 IP 或内网穿透（如需对外提供服务）


## 三、文件说明

| 文件 | 说明 |
|------|------|
| `fn-appstores-server-{version}.tar` | Docker 镜像包（或从镜像仓库拉取） |
| `data/` 文件夹（需自行准备） | 挂载到容器内的数据目录，存放应用清单、安装包、公告、统计数据等 |


## 四、快速开始

### 1. 导入镜像

**方式一：从镜像仓库拉取（推荐）**

```bash
docker pull ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.4.0
```

**方式二：从 tar 文件导入**

```bash
docker load -i fn-appstores-server-2.4.0.tar
```

验证镜像是否存在：

```bash
docker images | grep fn-appstores-server
```

### 2. 准备数据目录

创建数据目录：

```bash
mkdir -p /vol1/1000/docker/fn-appstores-server/data/{apps,icons,previews}
```

将 `fn-appstores.json` 放入 `data/` 目录，将 `.fpk` 安装包放入 `data/apps/`，图标放入 `data/icons/`，截图放入 `data/previews/{app_id}/`。

### 3. 启动容器

**基础启动命令：**

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p 5660:5660 \
  -v /vol1/1000/docker/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.4.0
```

**推荐启动命令（设置 BASE_URL）：**

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p 5660:5660 \
  -e BASE_URL="http://你的公网域名或IP:5660" \
  -v /vol1/1000/docker/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.4.0
```

**参数说明**：

| 参数 | 说明 |
|------|------|
| `-d` | 后台运行 |
| `--name` | 容器名称 |
| `--restart unless-stopped` | 自动重启 |
| `-p 5660:5660` | 端口映射（宿主机:容器） |
| `-e BASE_URL="..."` | 强制指定资源访问地址（图标/截图/FPK 下载） |
| `-v ...:/app/data` | 挂载数据目录 |

### 4. 验证服务

```bash
curl http://127.0.0.1:5660/api/apps
```

正常返回 JSON 格式的应用列表即表示部署成功。


## 五、BASE_URL 环境变量（v2.3.1 新增）

### 5.1 为什么需要 BASE_URL？

服务端生成图标、截图、FPK 下载地址时，默认使用 `request.host`（即客户端访问服务端时使用的地址）。这会导致以下问题：

| 场景 | request.host | 生成的资源地址 | 结果 |
|------|-------------|---------------|------|
| 客户端与服务端在同一设备 | `192.168.1.100:5660` | `http://192.168.1.100:5660/icons/xxx.PNG` | ✅ 正常 |
| 客户端在另一台设备访问 | `192.168.1.101:5660` | `http://192.168.1.101:5660/icons/xxx.PNG` | ❌ 404（资源在 192.168.1.100） |
| 通过中继/公网域名访问 | `xxx.fnos.net` | `http://xxx.fnos.net/icons/xxx.PNG` | ❌ 404（中继不代理 /icons/） |

**`BASE_URL` 的作用**：强制指定资源地址，不再依赖 `request.host`，解决跨设备、中继、域名反代等场景下的资源加载问题。

### 5.2 如何使用 BASE_URL

启动容器时添加 `-e BASE_URL` 参数：

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p 5660:5660 \
  -e BASE_URL="http://你的公网域名或IP:5660" \
  -v /vol1/1000/docker/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.4.0
```

### 5.3 BASE_URL 应该填什么？

| 使用场景 | BASE_URL 推荐值 | 示例 |
|---------|----------------|------|
| 仅局域网内使用 | 服务端所在设备的内网 IP | `http://192.168.1.100:5660` |
| 公网访问（有域名） | 公网域名 | `http://app.your-domain.com:5660` |
| 公网访问（无域名） | 公网 IP | `http://123.45.67.89:5660` |
| 通过 FRP/内网穿透访问 | FRP 节点的公网域名或 IP | `http://frp-node.com:5660` |

### 5.4 BASE_URL 优先级

服务端 `get_base_url()` 的优先级顺序：

1. **环境变量 `BASE_URL`**（最高优先级，推荐使用）
2. 当前请求的 `request.host`（回退）
3. 默认地址 `http://rc.hhxs2026.top:5660`（最终兜底）

### 5.5 如何确认 BASE_URL 生效

查看容器启动日志：

```bash
docker logs fn-appstores-server | grep BASE_URL
```

如果设置成功，会看到：

```
🔗 使用 BASE_URL 环境变量: http://your-domain.com:5660
```

如果未设置，会看到：

```
ℹ️ 未设置 BASE_URL 环境变量，将根据请求来源动态生成
```


## 六、树状聚合架构（v2.4.0 新增）

### 6.1 什么是树状聚合架构？

v2.4.0 引入了树状聚合能力，官方源可作为“根节点”，聚合多个审核通过的三方源，统一对外提供服务。

```
                    ┌─────────────┐
                    │   用户客户端   │
                    │ （只连官方源）  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   官方源（根）  │
                    │ rc.hhxs2026  │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
     ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
     │ 三方源 A   │   │ 三方源 B   │   │ 三方源 C   │
     │ (树枝)     │   │ (树枝)     │   │ (树枝)     │
     └───────────┘   └───────────┘   └───────────┘
```

**效果**：
- 用户只需添加官方源，即可看到所有审核通过的三方源应用
- 三方源开发者无需自行推广，通过审核即可触达所有用户
- 每个应用卡片会显示实际来源（如“张三的应用源”）

### 6.2 upstream.json 配置文件

在 `data/` 目录下创建 `upstream.json` 文件，配置需要聚合的三方源白名单：

```json
{
  "sources": [
    {
      "id": "source_zhangsan",
      "name": "张三的应用源",
      "url": "http://zhangsan.example.com:5660",
      "enabled": true,
      "added_at": "2026-08-15",
      "description": "个人开发的应用集合"
    },
    {
      "id": "source_lisi",
      "name": "李四的镜像源",
      "url": "http://lisi.example.com:5660",
      "enabled": true,
      "added_at": "2026-08-14",
      "description": "常用工具镜像"
    }
  ]
}
```

**字段说明**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 三方源唯一标识 |
| `name` | ✅ | 显示名称（会显示在应用卡片的来源标签中） |
| `url` | ✅ | 三方源服务端地址（需包含端口） |
| `enabled` | ❌ | 是否启用，默认 `true` |
| `added_at` | ❌ | 添加时间，便于追溯 |
| `description` | ❌ | 备注说明 |

### 6.3 工作流程

| 角色 | 操作 |
|------|------|
| **三方源开发者** | 搭建服务端，自测通过，提交源地址给官方 |
| **官方审核** | 验证内容、安全性、稳定性 |
| **官方维护** | 审核通过后在 `upstream.json` 中添加源地址 |
| **官方服务端** | 启动时自动拉取所有白名单三方源的应用 |
| **普通用户** | 打开软仓即可看到所有应用，无需自行添加源 |

### 6.4 合并且去重

服务端会自动合并本地应用和所有三方源应用，按 `id` 去重，保留版本较高的应用。当三方源版本 >= 本地版本时，三方源应用优先显示，并保留其来源标签。


## 七、服务端数据目录结构

```
data/
├── fn-appstores.json          # 应用清单（必须）
├── notice.json                # 公告内容（可选，v2.2.0+）
├── upstream.json              # 三方源白名单（可选，v2.4.0+）
├── stats.db                   # 下载统计数据库（v2.3.0+，自动生成）
├── apps/                      # .fpk 安装包（必须）
│   ├── myapp-1.0.0.fpk
│   └── ...
├── icons/                     # 应用图标（可选）
│   ├── myapp.PNG
│   └── ...
└── previews/                  # 应用截图（可选）
    ├── myapp/
    │   ├── 1.PNG
    │   └── 2.PNG
    └── ...
```

### 文件命名规则

| 资源类型 | 命名规则 | 示例 |
| :--- | :--- | :--- |
| 应用包 | `{id}-{version}.fpk` | `cloud-collection-1.2.0.fpk` |
| 应用图标 | `{id}.PNG`（大小写敏感） | `cloud-collection.PNG` |
| 应用截图 | `{数字}.PNG` | `previews/cloud-collection/1.PNG` |

> **注意**：`fn-appstores.json` 中列出的每个应用，`data/apps/` 目录下必须有对应的 `{id}-{version}.fpk` 文件，否则该应用不会被加载。


## 八、应用清单格式（fn-appstores.json）

`fn-appstores.json` 是服务端的核心配置文件，格式如下：

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

**字段说明**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 应用唯一标识，需与文件名对应，可包含 `-`（如 `cloud-collection`） |
| `name` | ✅ | 应用显示名称 |
| `version` | ✅ | 版本号，用于生成 `{id}-{version}.fpk`（支持 `1.0`、`1.0.0`、`v1.0`、`v1.0.0`） |
| `desc` | ❌ | 应用描述 |
| `author` | ❌ | 作者 |
| `tags` | ❌ | 分类标签（逗号分隔） |
| `repo` | ❌ | 源码仓库地址 |


## 九、公告配置（notice.json）

`notice.json` 是 v2.2.0 新增的公告配置文件，放置在 `data/` 目录下。客户端会在“关于”页面展示公告内容。

### 文件格式

```json
{
  "enabled": true,
  "title": "📢 公告标题",
  "summary": "公告摘要内容（显示在横幅中）",
  "content": "## 🎉 公告内容\n\n支持 **Markdown** 格式渲染。\n\n- 列表项1\n- 列表项2\n\n欢迎使用 FN软仓！",
  "updated_at": "2026-08-09"
}
```

**字段说明**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `enabled` | ✅ | 是否启用公告，`true` 或 `false` |
| `title` | ❌ | 公告标题 |
| `summary` | ❌ | 公告摘要（用于横幅提醒） |
| `content` | ✅ | 公告正文，支持 Markdown 格式 |
| `updated_at` | ❌ | 更新时间，建议格式 `YYYY-MM-DD` |

### 更新公告

修改 `data/notice.json` 后，重启容器即可生效：

```bash
docker restart fn-appstores-server
```


## 十、API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/apps` | GET | 获取应用列表（含聚合的三方源应用），支持 `?force=true` 强制刷新 |
| `/api/refresh` | POST | 强制刷新应用列表缓存（v2.3.0+） |
| `/api/notice` | GET | 获取公告内容（v2.2.0+） |
| `/api/stats/<app_id>` | GET | 获取单个应用下载统计（v2.3.0+） |
| `/apps/<filename>` | GET | 下载 `.fpk` 文件（自动记录下载次数，v2.3.0+） |
| `/icons/<filename>` | GET | 获取应用图标 |
| `/previews/<app_id>/<filename>` | GET | 获取应用截图 |
| `/health` | GET | 健康检查 |


## 十一、客户端配置（供用户使用）

用户安装 FN软仓客户端 v2.2.0 后，可通过以下步骤添加你的自托管源：

1. 打开 FN软仓 → 点击底部“源管理”Tab
2. 点击“添加源”，输入：
   - **源名称**：自定义（如“我的应用源”）
   - **源地址**：`http://你的服务器IP:5660`（需与 `BASE_URL` 保持一致）
3. 点击“测试”验证连通性，确认后点击“添加”

添加成功后，应用列表会自动合并展示该源的所有应用，同时“关于”页面会展示你发布的公告。

> **注意**：服务端设备需配置公网 IP 或内网穿透（如 FRP）并开放 5660 端口。

如果官方源启用了树状聚合（v2.4.0），用户**无需添加任何三方源**，打开官方源即可看到所有审核通过的三方源应用。


## 十二、内置源地址说明

v2.2.3 起，官方内置源地址为：

| 源地址类型 | 地址 | 说明 |
| :--- | :--- | :--- |
| **官方源地址** | `http://rc.hhxs2026.top:5660` | 主用 |
| **官方源备用地址** | `http://rc1.hhxs2026.top:5660` | 备用（v2.2.3 起作为备用，旧版可能只有一个源） |
| **应用源地址查询** | `https://gitee.com/hhxs2025/fn-appstores/raw/master/源.md` | 官方源列表查询 |

> **注意**：自托管用户不受影响，可自行添加任意源地址。


## 十三、常见问题

### Q：服务端启动后 `/api/apps` 返回空数据？

1. 检查 `data/fn-appstores.json` 是否存在且格式正确
2. 检查 `data/apps/` 目录下是否有对应的 `.fpk` 文件
3. 查看容器日志：`docker logs fn-appstores-server`

### Q：图标或截图不显示？

1. **检查 `BASE_URL` 是否正确设置**（v2.3.1+）：
   ```bash
   docker logs fn-appstores-server | grep BASE_URL
   ```
2. 确认 `data/icons/` 目录下的图标文件名与 `fn-appstores.json` 中的 `id` 一致（大小写敏感）
3. 确认 `data/previews/{app_id}/` 目录下有截图文件
4. 在浏览器中直接访问图标地址，确认是否返回 404

### Q：公告不显示？

1. 检查 `data/notice.json` 是否存在且格式正确
2. 确认 `enabled` 字段为 `true`
3. 确认 `content` 字段不为空
4. 检查客户端是否 v2.2.0 或以上版本
5. 查看容器日志：`docker logs fn-appstores-server`

### Q：端口 5660 被占用怎么办？

修改启动命令中的端口映射，如改为 `-p 5661:5660`，客户端添加源时使用对应端口即可。同时 `BASE_URL` 也要同步修改。

### Q：如何更新应用数据或公告？

1. 更新 `data/fn-appstores.json` 或 `data/notice.json`
2. 添加/替换 `data/apps/` 中的 `.fpk` 文件
3. 重启容器：`docker restart fn-appstores-server`

### Q：下载统计不显示或为 0？

1. 确认客户端已升级到 v2.3.0 或以上版本
2. 在客户端点击“刷新”按钮强制更新缓存
3. 检查服务端容器日志：`docker logs fn-appstores-server | grep "下载计数"`

### Q：跨设备访问时图标显示 404（v2.3.0 及以下版本）？

升级到 v2.3.1 并设置 `BASE_URL` 环境变量即可解决。

### Q：三方源应用没有出现在列表中（v2.4.0）？

1. 检查 `data/upstream.json` 是否存在且格式正确
2. 确认三方源地址可访问：`curl http://三方源地址/api/apps`
3. 查看容器日志：`docker logs fn-appstores-server | grep "上游"`，确认拉取成功
4. 强制刷新缓存：`curl -X POST http://官方源地址/api/refresh`

### Q：三方源应用的来源标签显示不正确？

v2.4.0 服务端强制使用 `upstream.json` 中配置的 `name` 字段作为来源标签，三方源自身无法伪造。检查 `upstream.json` 中的 `name` 字段是否正确。


## 十四、版本更新记录

### v2.4.0（当前版本）

**新增功能**：
- ✅ **树状聚合架构**：支持通过 `upstream.json` 配置三方源白名单，官方源自动拉取并聚合三方源应用
- ✅ **统一入口**：用户只需添加官方源即可看到所有审核通过的三方源应用
- ✅ **来源标签强制覆盖**：三方源应用显示 `upstream.json` 中配置的名称，防止来源伪造
- ✅ **智能合并去重**：按 `id` 去重，保留版本较高的应用；三方源版本 >= 本地版本时优先使用三方源
- ✅ **启动日志增强**：显示已配置的上游三方源列表

**改进**：
- 🔧 缓存机制优化，支持三方源数据缓存
- 🔧 合并逻辑完善，确保三方源来源标签正确显示


### v2.3.1

**新增功能**：
- ✅ **`BASE_URL` 环境变量**：强制指定资源访问地址，解决跨设备、中继、域名反代等场景下图标和截图 404 的问题
- ✅ **优先级机制**：`BASE_URL` > `request.host` > 默认地址

**改进**：
- 🔧 启动日志增强：显示当前使用的 `base_url` 配置，便于排查问题
- 🔧 默认回退地址修正为 `http://rc.hhxs2026.top:5660`


### v2.3.0

**新增功能**：
- ✅ **应用下载统计**：安装应用时自动累加下载次数，前端卡片显示
- ✅ **SQLite 持久化**：下载统计数据存储在 `data/stats.db`
- ✅ **统计接口**：`/api/stats/<app_id>` 查询单个应用下载数
- ✅ **强制刷新接口**：`/api/refresh` POST 接口，清除缓存并返回最新数据
- ✅ **智能 app_id 提取**：支持带多个连字符的应用 ID（如 `cloud-collection`）
- ✅ **版本号兼容**：支持 `1.0`、`1.0.0`、`v1.0`、`v1.0.0` 等多种格式

**改进**：
- 🔧 优化缓存机制
- 🔧 完善日志输出，便于排查问题


### v2.2.0

**新增功能**：
- ✅ **公告板**：支持通过 `data/notice.json` 向客户端推送公告
- ✅ **Markdown 渲染**：公告内容支持 Markdown 格式

**改进**：
- 🔧 镜像仓库迁移至腾讯云容器镜像服务（CCR）


### v2.1.0

**基础功能**：
- ✅ 应用列表 API（`/api/apps`）
- ✅ FPK 文件下载服务（`/apps/<filename>`）
- ✅ 应用图标服务（`/icons/<filename>`）
- ✅ 应用截图服务（`/previews/<app_id>/<filename>`）
- ✅ 健康检查接口（`/health`）
- ✅ 24 小时内存缓存
- ✅ Docker 容器化部署


## 十五、升级指南

### 从 v2.3.1 升级到 v2.4.0

1. **备份现有数据**：
   ```bash
   cp -r /vol1/1000/docker/fn-appstores-server/data /vol1/1000/docker/fn-appstores-server/data.bak
   ```

2. **拉取新镜像**：
   ```bash
   docker pull ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.4.0
   ```

3. **停止并删除旧容器**：
   ```bash
   docker stop fn-appstores-server
   docker rm fn-appstores-server
   ```

4. **使用新版镜像启动容器**：
   ```bash
   docker run -d \
     --name fn-appstores-server \
     --restart unless-stopped \
     -p 5660:5660 \
     -e BASE_URL="http://你的公网域名或IP:5660" \
     -v /vol1/1000/docker/fn-appstores-server/data:/app/data \
     ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.4.0
   ```

5. **（可选）配置三方源聚合**：
   在 `data/` 目录下创建 `upstream.json`，添加需要聚合的三方源白名单（参考第六章）。


> **注意**：首次启动 v2.4.0 会自动创建 `data/stats.db` 数据库文件（如果不存在）。从旧版本升级，现有统计数据不受影响。


## 十六、版本信息

- **当前版本**：2.4.0
- **作者**：晦华先生
- **反馈**：2303537063@qq.com
- **开源地址**：[https://gitee.com/hhxs2025/fn-appstores](https://gitee.com/hhxs2025/fn-appstores)
- **镜像仓库**：`ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.4.0`

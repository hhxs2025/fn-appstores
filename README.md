# FN软仓服务端 自托管搭建指南

> 适用于 v2.5.1 版本 · 面向三方源搭建者


## 一、简介

FN软仓服务端是一个基于 Docker 的轻量级应用商店后端服务，提供应用列表 API 和 `.fpk` 文件下载。开发者可以自托管此服务端，成为 FN软仓客户端的一个"软件源"。

其他用户通过 FN软仓客户端添加你的服务端地址后，即可浏览和安装你收录的应用，并在首页查看你发布的公告。


## 二、核心功能

- ✅ **应用托管**：支持飞牛本地托管、Gitee 仓库存储、Gitee Releases 三种托管方式
- ✅ **下载统计**：自动记录每个应用的下载次数，支持排行榜查看
- ✅ **树状聚合**：通过 `upstream.json` 聚合多个三方源，作为统一入口分发应用
- ✅ **公告管理**：支持轮播图 + 公告记录，可通过管理后台在线编辑
- ✅ **权限分离**：不同角色拥有不同管理权限（公告编辑 / 完整管理）
- ✅ **管理后台**：公告管理、三方源管理、数据查看、使用说明，一站式管理
- ✅ **客户端自更新**：通过 `client-version.json` 为客户端提供版本更新提示


## 三、搭建步骤

### 1. 环境要求

- 飞牛 fnOS 系统（或任意支持 Docker 的 Linux 系统）
- Docker 20.10+
- 公网 IP 或内网穿透（如需对外提供服务）

### 2. 导入镜像

```bash
docker pull ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.5.1
```

### 3. 准备数据目录

创建数据目录：

```bash
mkdir -p /vol1/1000/docker/fn-appstores-server/data/{apps,icons,previews}
```

将 `fn-appstores.json` 放入 `data/` 目录，将 `.fpk` 安装包放入 `data/apps/`，图标放入 `data/icons/`，截图放入 `data/previews/{app_id}/`。

### 4. 启动容器

**⚠️ 重要提醒**：由于服务端会强制重写所有 `download_url` 为 `{BASE_URL}/apps/{filename}`，**自托管源搭建者必须设置 `BASE_URL` 环境变量**，否则所有下载地址将指向官方兜底域名，导致 404。

**基础启动命令：**

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p 5660:5660 \
  -e TZ=Asia/Shanghai \
  -e BASE_URL="http://你的公网域名或IP:5660" \
  -v /vol1/1000/docker/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.5.1
```

**参数说明**：

| 参数 | 说明 |
|------|------|
| `-d` | 后台运行 |
| `--name` | 容器名称 |
| `--restart unless-stopped` | 自动重启 |
| `-p 5660:5660` | 端口映射（宿主机:容器） |
| `-e TZ=Asia/Shanghai` | 时区设置 |
| `-e BASE_URL="..."` | **必填**：强制指定资源访问地址 |
| `-v ...:/app/data` | 挂载数据目录 |

### 5. 设置管理密码

管理后台默认密码为 `admin123`，**首次登录后请立即修改**。

```bash
-e LOGIN_PASSWORD="你的新密码"
```

> 完整命令中，`-e LOGIN_PASSWORD` 应添加在 `-e BASE_URL` 之后、`-v` 之前。

### 6. 验证服务

```bash
curl http://127.0.0.1:5660/api/apps
```

正常返回 JSON 格式的应用列表即表示部署成功。

### 7. 访问管理后台

```
http://你的服务器IP:5660/admin
```


## 四、BASE_URL 环境变量

### 4.1 为什么需要 BASE_URL？

服务端生成图标、截图、FPK 下载地址时，默认使用 `request.host`（即客户端访问服务端时使用的地址）。这会导致以下问题：

| 场景 | request.host | 生成的资源地址 | 结果 |
|------|-------------|---------------|------|
| 客户端与服务端在同一设备 | `192.168.1.100:5660` | `http://192.168.1.100:5660/icons/xxx.PNG` | ✅ 正常 |
| 客户端在另一台设备访问 | `192.168.1.101:5660` | `http://192.168.1.101:5660/icons/xxx.PNG` | ❌ 404（资源在 192.168.1.100） |
| 通过中继/公网域名访问 | `xxx.fnos.net` | `http://xxx.fnos.net/icons/xxx.PNG` | ❌ 404（中继不代理 /icons/） |

**`BASE_URL` 的作用**：强制指定资源地址，不再依赖 `request.host`，解决跨设备、中继、域名反代等场景下的资源加载问题。

### 4.2 如何设置 BASE_URL

启动容器时添加 `-e BASE_URL` 参数：

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p 5660:5660 \
  -e BASE_URL="http://你的公网域名或IP:5660" \
  -v /vol1/1000/docker/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.5.1
```

### 4.3 BASE_URL 应该填什么？

| 使用场景 | BASE_URL 推荐值 | 示例 |
|---------|----------------|------|
| 仅局域网内使用 | 服务端所在设备的内网 IP | `http://192.168.1.100:5660` |
| 公网访问（有域名） | 公网域名 | `http://app.your-domain.com:5660` |
| 公网访问（无域名） | 公网 IP | `http://123.45.67.89:5660` |
| 通过 FRP/内网穿透访问 | FRP 节点的公网域名或 IP | `http://frp-node.com:5660` |

### 4.4 如何确认 BASE_URL 生效

查看容器启动日志：

```bash
docker logs fn-appstores-server | grep BASE_URL
```

如果设置成功，会看到：

```
🔗 使用 BASE_URL 环境变量: http://your-domain.com:5660
```


## 五、管理后台角色说明

v2.5.1 版本支持权限分离，不同登录身份拥有不同的管理能力：

| 身份 | 可访问功能 | 说明 |
|------|----------|------|
| **管理员** | 公告管理、三方源管理、数据查看、使用说明 | 拥有完整管理权限 |
| **公告编辑者** | 公告管理（仅编辑）、使用说明 | 仅可编辑公告内容 |

### 5.1 公告管理

| 功能 | 说明 |
|------|------|
| **启用公告** | 顶部开关控制公告全局启用/禁用 |
| **轮播图** | 点击「+ 添加」输入图片 URL，可拖拽调整顺序，点击「✕」删除 |
| **公告记录** | 点击「+ 添加公告」创建新公告，支持 `<b>`、`<a>` 等 HTML 标签 |
| **保存公告** | 修改后点击「保存公告」立即生效，无需重启容器 |

### 5.2 三方源管理

| 功能 | 说明 |
|------|------|
| **添加三方源** | 填写 ID（唯一标识）、名称（显示用）、地址（对方服务端 URL） |
| **测试连通性** | 点击「测试」验证对方 `/api/apps` 是否可访问 |
| **启用/禁用** | 临时开关，无需删除即可控制是否聚合 |
| **删除** | 永久移除该三方源 |

### 5.3 数据查看

| 功能 | 说明 |
|------|------|
| **应用清单** | 查看 `fn-appstores.json` 原始内容 |
| **运行时合并列表** | 展示实际返回给客户端的完整应用列表 |
| **下载统计** | 按下载量降序排列，总下载量一目了然 |


## 六、应用清单格式（fn-appstores.json）

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
    "repo": "https://gitee.com/xxx/xxx",
    "updated_at": "2026-08-26",
    "download_url": "https://gitee.com/xxx/xxx/raw/master/apps/myapp-1.0.0.fpk",
    "icon": "https://gitee.com/xxx/xxx/raw/master/icons/myapp.PNG"
  }
]
```

**字段说明**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 应用唯一标识 |
| `name` | ✅ | 应用显示名称 |
| `version` | ✅ | 版本号 |
| `desc` | ❌ | 应用描述 |
| `author` | ❌ | 作者 |
| `tags` | ❌ | 分类标签 |
| `repo` | ❌ | 源码仓库地址 |
| `updated_at` | ❌ | 最后更新时间（格式 `YYYY-MM-DD`） |
| `download_url` | ❌ | 原始下载地址 |
| `icon` | ❌ | 图标地址 |

**v2.5.1 重要行为**：
- 服务端会读取 `download_url` 并暂存到内存
- 返回给客户端的 `download_url` 被强制重写为 `{BASE_URL}/apps/{filename}`
- 实现"统一下载入口 → 统计 → 302 重定向"闭环


## 七、文件命名规则

| 资源类型 | 命名规则 | 示例 |
| :--- | :--- | :--- |
| 应用包 | `{id}-{version}.fpk` | `cloud-collection-1.2.0.fpk` |
| 应用图标 | `{id}.PNG`（大小写敏感） | `cloud-collection.PNG` |
| 应用截图 | `{数字}.PNG` | `previews/cloud-collection/1.PNG` |


## 八、版本更新记录

### v2.5.1（当前版本）

**新增功能**：
- ✅ **强制下载地址重写 + 302 重定向统计**：解决 Gitee 托管 FPK 应用无法统计下载量的问题
- ✅ **管理后台「刷新应用缓存」按钮**：一键调用 `/api/refresh`，无需 SSH
- ✅ **管理后台「使用说明」Tab**：内置完整操作指引
- ✅ **管理后台「数据查看」Tab**：新增 `fn-appstores.json` 查看、运行时合并列表、下载统计排行
- ✅ **客户端自更新接口**：`/api/client-version`，读取 `data/client-version.json`
- ✅ **三方源管理 API 完善**：完整的 CRUD + 状态检测 + 测试连通性
- ✅ **权限分离**：支持管理员与公告编辑者两种身份

**改进**：
- 🔧 管理后台三方源列表显示在线/离线/已禁用状态
- 🔧 添加/删除/切换三方源后自动刷新缓存


### v2.5.0

**新增功能**：
- ✅ **管理后台**：新增 `/admin` 管理界面，支持在线编辑公告
- ✅ **三方源管理 Tab**：管理后台新增三方源在线管理
- ✅ **公告格式升级**：`notice.json` 支持 `carousel`（轮播图）和 `records`（公告记录）
- ✅ **最近更新接口**：新增 `/api/recent`
- ✅ **应用 `updated_at` 字段**：服务端自动维护最后更新时间


### v2.4.1

**改进**：
- 🔧 移除 `request.host` 回退逻辑，BASE_URL 优先级简化为：环境变量 > 双兜底域名
- 🔧 新增双兜底域名：主备域名自动切换
- 🔧 三方源拉取增强：超时从 10s 延长至 15s，失败自动重试 2 次（指数退避）


### v2.4.0

**新增功能**：
- ✅ **树状聚合架构**：通过 `upstream.json` 配置三方源白名单
- ✅ **统一入口**：用户只需添加官方源即可看到所有审核通过的三方源应用
- ✅ **来源标签强制覆盖**：防止来源伪造
- ✅ **智能合并去重**：按 `id` 去重，保留版本较高的应用


## 九、常见问题

### Q：服务端启动后 `/api/apps` 返回空数据？

1. 检查 `data/fn-appstores.json` 是否存在且格式正确
2. 检查 `data/apps/` 目录下是否有对应的 `.fpk` 文件
3. 查看容器日志：`docker logs fn-appstores-server`

### Q：图标或截图不显示？

1. 检查 `BASE_URL` 是否正确设置
2. 确认 `data/icons/` 目录下的图标文件名与 `fn-appstores.json` 中的 `id` 一致（大小写敏感）
3. 确认 `data/previews/{app_id}/` 目录下有截图文件

### Q：管理后台无法访问？

1. 确认镜像版本为 v2.5.0 或更高
2. 确认 `static/admin.html` 文件存在
3. 查看容器日志：`docker logs fn-appstores-server | grep admin`

### Q：如何更新应用数据或公告？

**应用数据：**
1. 更新 `data/fn-appstores.json`
2. 添加/替换 `data/apps/` 中的 `.fpk` 文件
3. 点击管理后台右上角「刷新应用缓存」（或调用 `/api/refresh`），无需重启容器

**公告（推荐方式）：**
1. 访问 `/admin` 管理后台
2. 在线编辑轮播图和公告记录
3. 点击保存即生效，无需重启容器

### Q：三方源应用没有出现在列表中？

1. 检查 `data/upstream.json` 是否存在且格式正确
2. 确认三方源地址可访问：`curl http://三方源地址/api/apps`
3. 点击管理后台「刷新应用缓存」或 `curl -X POST http://你的服务端地址/api/refresh`

### Q：如何在线管理三方源？

访问 `/admin` 管理后台，切换到「三方源管理」Tab，即可在线添加、测试、启用/禁用、删除三方源。


## 十、技术交流

- 用户交流群：QQ 群 1039270739
- 代码仓库：https://gitee.com/hhxs2025/fn-appstores
- 问题反馈：https://gitee.com/hhxs2025/fn-appstores/issues

---

> **文档版本**：v2.5.1
> **对应服务端版本**：v2.5.1
> **更新日期**：2026-08-30
![首页](previews/xuanchuantu.png =800x500)
# FN软仓服务端搭建指南

> 版本 v2.8.2（Go 版）
<a href='https://gitee.com/hhxs2025/fn-appstores'><img src='https://gitee.com/hhxs2025/fn-appstores/widgets/widget_2.svg' alt='Fork me on Gitee'></img></a>


## 一、项目简介

FN软仓服务端是一个基于 Docker 的轻量级应用商店后端服务，使用 **Go 语言** 编写，提供应用列表 API 和 `.fpk` 文件下载能力。开发者可以自托管此服务端，成为 FN软仓客户端的一个"软件源"。其他用户通过客户端添加你的源地址后，即可浏览和安装你收录的应用，并在首页查看公告。

**v2.8.2 核心特性**：

- 🌐 **IPv4 / IPv6 双栈监听**：服务端同时接受 v4 和 v6 请求，聚合源地址可以是 v6 域名
- 🏗️ **应用架构支持**：同一应用区分 x86 / ARM / 通用，客户端按本机架构自动过滤
- ✏️ **同 ID 双架构精确编辑**：后台「应用编辑」按 `id@platform` 复合键匹配，同 ID 双架构各自独立编辑，不再互相影响
- ⭐ **应用评分**：客户端可评分，卡片显示评分徽章，后台应用编辑也能看到
- 🔗 **外链托管兼容**：FPK 可托管在 Git类平台 / OSS 等外部存储，服务端 302 跳转
- 📊 **数据查看**：本地清单 / 按源查看 / 下载统计三面板 + 架构分类统计卡片
- 📣 **自动公告**：应用上架/更新/下架时，自动追加到客户端首页公告，**永不丢失**
- 🩺 **三方源健康检查调整**：只标记在线/离线状态，**不再自动禁用**（避免网络抖动误伤）
- 🚀 **镜像 ~15MB，内存 ~10MB**：Go 版轻量优势


## 二、部署方式总览

服务端支持 **2 种运行环境 × 3 种应用托管方式**，可以自由组合。

### 2.1 运行环境

| 环境 | 说明 | 适合场景 |
|------|------|---------|
| **飞牛 NAS 部署** | 服务端跑在飞牛设备上（需 Docker 支持） | 个人开发者，应用资源在自己 NAS 上 |
| **云服务器部署** | 服务端跑在云主机上（阿里云 / 腾讯云 / 甲骨文等） | 需要固定公网 IP、带宽较大、长期稳定运行 |

两种环境跑的是**同一个 Docker 镜像**，只是网络配置略有差异（见下）。

### 2.2 部署维度说明

服务端部署涉及两个**独立选择**，可以任意组合。

- **列头（服务端位置）**：服务端程序跑在哪，即 `fn-appstores.json` 所在的机器
- **行头（资源托管位置）**：FPK 文件放在哪，即每个应用 `download_url` 字段指向的位置
---
两件事不耦合，任意组合都成立。


| 资源托管位置<br>（fpk/icon所在）  | 飞牛 NAS 服务端<br>（fn-appstores.json所在）| 云服务器服务端<br>（fn-appstores.json所在） |
|:----:|:---:|:---:|
| **服务端本地目录**<br>（跟json同机） | ✅ FPK 存飞牛磁盘<br>服务端直接返回本地文件 | ✅FPK存云盘<br>服务端直接返回本地文件 |
| **Git类仓库**<br>（Gitee/Gitea/GitHub） | ✅ FPK放Git类仓库<br>飞牛只存json+图标 | ✅FPK放Git类仓库<br>云盘只存json+图标,省流量 |
| **对象存储**<br>（阿里云OSS/腾讯云COS） | ✅ FPK放OSS<br>飞牛带宽小,走OSS CDN | ✅FPK放OSS<br>云盘带宽小,走OSS CDN |  


**读法**：横着看 = 同一个服务端位置下，FPK 可以放哪；竖着看 = 同一个 FPK 托管方式下，服务端可以跑在哪。

**列头决定"服务端跑在哪"**：

- **飞牛 NAS 服务端**：`fn-appstores.json` 在飞牛的 `/vol1/1000/fn-appstores-server/data/` 下
- **云服务器服务端**：`fn-appstores.json` 在云服务器的 `/www/fn-appstores-server/data/` 下

**行头决定"FPK 放哪"**：

- **服务端本地目录**：FPK 和服务端在同一台机器，服务端直接返回文件，无 302
- **Git 类仓库**：FPK 在 Gitee / Gitea / GitHub，服务端本地没有时 **302 跳转**
- **对象存储**：FPK 在 OSS / COS，服务端本地没有时 **302 跳转**

**任意组合都成立**：

| 组合 | 典型场景 |
|------|---------|
| 飞牛服务端 + 服务端本地 | 全自托管，FPK 也在飞牛上，客户端从飞牛下载 |
| 飞牛服务端 + Git 仓库 | 飞牛磁盘小或带宽小，FPK 放 Gitee 减轻压力 |
| 飞牛服务端 + 对象存储 | 飞牛带宽小，FPK 走 OSS CDN |
| 云服务器服务端 + 服务端本地 | 最常见的"正式源"玩法，云盘直连公网 |
| 云服务器服务端 + Git 仓库 | 云盘带宽小，FPK 走 Gitee |
| 云服务器服务端 + 对象存储 | 云盘带宽小，FPK 走 OSS CDN |


## 三、核心功能

### 客户端 API

- **应用列表**：`/api/apps`，支持三方源聚合、24 小时缓存、`?force=true` 强制刷新、评分字段合并
- **最近更新**：`/api/recent`，按 `sort_order` + `updated_at` 排序
- **公告**：`/api/notice`，支持轮播图和 HTML 公告记录
- **客户端自更新**：`/api/client-version`
- **应用下载统计**：`/api/stats/<app_id>`
- **应用评分**：`/api/rating/<app_id>`

### 文件服务

- **FPK 下载**：`/apps/<filename>`，自动统计下载次数，本地文件直接返回，支持断点续传；本地无文件时 302 到外链
- **图标**：`/icons/<filename>`
- **截图**：`/previews/<app_id>/<filename>`
- **健康检查**：`/health`

### 管理后台（`/admin`）

- **📢 公告管理**：轮播图 + 公告记录，支持 HTML 富文本、`order` 排序
- **🔗 三方源管理**：添加/删除/启用/禁用上游源，测试连通性；列表带 **30 秒内存缓存 + 并行状态探测**
- **📊 数据查看**：折叠面板（本地清单 + 按源查看 + 下载统计）+ 架构分类统计卡片
- **✏️ 应用编辑**：在线新增/编辑/删除应用，支持 `platform`（架构）字段、评分徽章、批量按钮组；**同 ID 双架构按 `id@platform` 精确匹配**（v2.8.2 修复）；标签 chip 多选
- **📤 应用上传**：拖拽 FPK 上传，自动解析 manifest、识别类型、提取图标、更新 JSON；含「上传历史」面板
- **🔔 QQ 群推送**：监听 JSON 变化，自动推送变动汇总消息
- **📣 自动公告**：应用上架/更新/下架时自动追加到客户端公告
- **🔄 刷新缓存**：一键调用 `/api/refresh`

### 架构特性

- **树状聚合**：`upstream.json` 配置三方源，官方源作为根节点聚合
- **并行拉取三方源**：Go goroutine 并发，速度提升 3~5 倍
- **JSON 变化监听**：无论通过后台、外部工具还是手工修改 JSON，都能被检测到
- **自动公告兜底**：应用变动时同步写入 `notice.json`，即使 QQ 推送失效，用户也能从客户端首页看到
- **健康检查不自动禁用**：三方源离线只标记状态
- **版本比较容错**：兼容任何格式的版本号
- **SQLite WAL 模式**：写入不阻塞读取
- **IPv4 / IPv6 双栈监听**：默认 `[::]:5660`


## 四、部署步骤

### 4.1 环境准备

**两种环境都需要的**：

- Docker 已安装（飞牛自带 Docker，云服务器自行安装）
- 一个公网可访问的地址（域名或 IP）
- 数据目录（存放 `fn-appstores.json` / `icons/` / `apps/` 等）

**飞牛 NAS**：

- 已开启 SSH 或能用终端执行命令
- 有可用的存储空间（`/vol1/` 等）

**云服务器**：

- 安全组放行端口（TCP）
- 防火墙放行端口（如 `firewalld` / `ufw`）
- 域名可选（有域名更好，证书方便）

---

### 4.2 拉取镜像

```bash
docker pull ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.8.2
```

---

### 4.3 准备数据目录

**飞牛 NAS**：

```bash
# 选一个存储空间下的位置
mkdir -p /vol1/1000/fn-appstores-server/data/{apps,icons,previews}
```

**云服务器**：

```bash
mkdir -p /www/fn-appstores-server/data/{apps,icons,previews}
```

**放入必需文件**（`data/` 目录下）：

| 文件 | 必需 | 说明 |
|------|:----:|------|
| `fn-appstores.json` | ✅ | 应用清单（初始可为 `[]`） |
| `notice.json` | ❌ | 公告配置（服务端自动创建） |
| `upstream.json` | ❌ | 三方源白名单（服务端自动创建） |
| `client-version.json` | ❌ | 客户端自更新信息 |

---

### 4.4 启动服务端

**环境变量说明**：

| 变量 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `BASE_URL` | **必填** | 内置兜底域名 | 服务端公网访问地址（**含端口**，不含末尾斜杠） |
| `ADMIN_PASSWORD` | 否 | `admin123` | 管理员密码（全部权限） |
| `NOTICE_PASSWORD` | 否 | `notice123` | 公告员密码（仅公告编辑权限） |
| `TZ` | 否 | UTC | 时区，建议 `Asia/Shanghai` |

> **⚠️ `BASE_URL` 必须包含端口号**：例如 `http://nas.example.com:port`。只写到域名会漏掉端口，导致服务端自动拼接的图标、截图、下载地址不可达。

---

#### 4.4.1 飞牛 NAS 部署

**如果飞牛 NAS 直连公网**（有公网 IP，或已配好 DDNS）：

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p "[::]:port:5660" \
  -e TZ=Asia/Shanghai \
  -e BASE_URL="http://你的域名:5660" \
  -e ADMIN_PASSWORD="你的管理密码" \
  -e NOTICE_PASSWORD="公告员专用密码" \
  -v /vol1/1000/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.8.2
```

**如果飞牛 NAS 在 NAT 后面**（家宽没公网 IP，靠 frp 穿透）：

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  --network host \
  -e TZ=Asia/Shanghai \
  -e BASE_URL="http://你的frp域名:frp端口" \
  -e ADMIN_PASSWORD="你的管理密码" \
  -e NOTICE_PASSWORD="公告员专用密码" \
  -v /vol1/1000/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.8.2
```

> **为什么用 `--network host`**：frp 穿透场景下，Docker bridge 网络的 NAT 规则经常被系统/面板改坏，导致容器内访问不到三方源。`--network host` 让容器直接用宿主机网络栈，避免这类问题。

**验证**：

```bash
curl http://127.0.0.1:5660/health
```

---

#### 4.4.2 云服务器部署

**推荐直接公网监听**（安全组放行port）：

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p "[::]:port:5660" \
  -e TZ=Asia/Shanghai \
  -e BASE_URL="http://你的域名或公网IP:port" \
  -e ADMIN_PASSWORD="你的管理密码" \
  -e NOTICE_PASSWORD="公告员专用密码" \
  -v /www/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.8.2
```

**如果使用宝塔面板 / 1Panel 等管理 Docker**：

- **只用于查看状态**，不要用面板的「重建」「重新创建」按钮，会覆盖网络配置
- 修改配置请用命令行 `docker stop` / `docker rm` / `docker run`
- 如果遇到容器内访问不到三方源（宿主机能访问、容器不能），改用 `--network host`：

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  --network host \
  -e TZ=Asia/Shanghai \
  -e BASE_URL="http://你的域名或公网IP:port" \
  -e ADMIN_PASSWORD="你的管理密码" \
  -e NOTICE_PASSWORD="公告员专用密码" \
  -v /www/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.8.2
```

**验证**：

```bash
curl http://127.0.0.1:port/health
curl http://你的公网IP:port/health
```

---

### 4.5 IPv6 双栈监听（可选）

服务端默认监听 `[::]:port`，Linux 下同时接受 IPv4 和 IPv6。要让 v6 请求真正生效，需满足：

**1. Docker 启用 IPv6**：编辑 `/etc/docker/daemon.json`：

```json
{
  "ipv6": true,
  "fixed-cidr-v6": "fd00::/80"
}
```

重启 Docker：`sudo systemctl restart docker`

**2. 端口映射写双栈格式**：`-p "[::]:port:5660"`（不是 `-p "port:5660"`）

**3. 宿主机有 v6 出口**：`curl -6 http://[240e:xxx::1]` 能通

**验证**：

```bash
curl -4 http://127.0.0.1:port/health   # IPv4
curl -6 "http://[::1]:port/health"     # IPv6
```

两个都返回 JSON 即双栈成功。

---

### 4.6 访问管理后台

浏览器打开：

```
http://你的地址:port/admin
```

登录密码为 `ADMIN_PASSWORD`（管理员）或 `NOTICE_PASSWORD`（公告员）。

---

## 五、添加应用

三种托管方式，按需选择。

### 5.1 自托管（FPK 保存在服务端）

**流程**：

1. 管理后台「应用上传」Tab 拖拽或选择 `.fpk` 文件（支持多选）
2. 服务端自动解析 manifest，提取应用 ID、名称、版本、描述、作者、`platform`
3. 服务端解压 `app.tgz` 自动识别应用类型（`server/` → 原生，`docker/docker-compose.yaml` → Docker）
4. FPK 保存到 `data/apps/{id}-{version}.fpk`，图标保存到 `data/icons/{id}.PNG`
5. JSON 自动更新，10 秒内 watcher 检测到变化：
   - **自动追加一条客户端公告**（`notice.json`）
   - **触发 QQ 群推送**（如已配置）

**特点**：

- FPK 完全由服务端掌控，无外部依赖
- 支持断点续传（`http.ServeContent` 自动处理 Range 请求）
- 下载统计在本地触发，不受外部服务影响

---

### 5.2 Git类平台托管

**流程**：

1. 把 FPK + 图标上传到 Gitee 仓库（Release 或 raw 直链）
2. 打开管理后台「应用编辑」Tab → 点「＋ 新增应用」
3. 填写表单：
   - `download_url` = Gitee Release 或 raw 直链
   - `icon` = 图标直链
   - 其他字段按需填写
4. 点「确认添加」，服务端写入 JSON 并刷新缓存
5. 客户端请求时，服务端本地找不到文件 → **302 跳转**到 Gitee

**特点**：

- 免费、公开
- **注意 Gitee CDN 冷启动**：首次访问可能拿到错误页，客户端已加 gzip 校验 + 3 次重试，能自动跨过这个窗口
- Gitee 对单文件有大小和流量限制

---

### 5.3 OSS 托管（阿里云 OSS / 腾讯云 COS 等）

**流程**：

1. 把 FPK + 图标上传到 OSS 桶（公开读）
2. 打开管理后台「应用编辑」Tab → 点「＋ 新增应用」
3. 填写表单：
   - `download_url` = OSS 外链
   - `icon` = OSS 图标直链
   - 其他字段按需填写
4. 点「确认添加」，服务端写入 JSON 并刷新缓存
5. 客户端请求时，服务端本地找不到文件 → **302 跳转**到 OSS

**特点**：

- 大文件传输稳定
- 支持 CDN 加速
- 有带宽/流量成本

---

### 5.4 手工编辑 JSON（任何托管方式通用）

直接在 `data/fn-appstores.json` 里添加条目：

```json
[
  {
    "id": "myapp",
    "name": "我的应用",
    "version": "1.0.0",
    "desc": "应用描述",
    "author": "作者",
    "tags": "工具,效率",
    "repo": "https://gitee.com/xxx/xxx",
    "updated_at": "2026-09-11",
    "download_url": "",
    "icon": "",
    "screenshots": [],
    "type": "原生",
    "platform": "x86",
    "sort_order": 0
  }
]
```

**字段说明**：

| 字段 | 必填 | 说明 |
|------|:----:|------|
| `id` | ✅ | 应用唯一标识 |
| `name` | ✅ | 显示名称 |
| `version` | ✅ | 版本号（支持任意格式） |
| `desc` | ❌ | 描述（支持 HTML） |
| `author` | ❌ | 作者 |
| `tags` | ❌ | 分类标签（英文逗号隔开，最多 2 个） |
| `repo` | ❌ | 源码仓库地址 |
| `updated_at` | ❌ | 最后更新时间（`YYYY-MM-DD`） |
| `download_url` | ❌ | 下载地址（**自托管留空**；外链托管填直链） |
| `icon` | ❌ | 图标地址（自托管留空则自动扫描 `data/icons/`） |
| `screenshots` | ❌ | 截图地址数组（自托管留空则自动扫描 `data/previews/`） |
| `type` | ❌ | 应用类型（`docker` / `原生`） |
| `platform` | ❌ | 应用架构（`x86` / `arm` / `all` / 空；空 = 按 x86 处理） |
| `sort_order` | ❌ | 首页置顶权重（数字越大越靠前） |

**`platform` 字段取值**：

| 值 | x86 设备 | ARM 设备 |
|----|---------|---------|
| `"x86"` | ✅ 显示 | ❌ 隐藏 |
| `"arm"` | ❌ 隐藏 | ✅ 显示 |
| `"all"` | ✅ 显示 | ✅ 显示 |
| `""` 空 | ✅ 显示 | ❌ 隐藏 |

**改完 JSON 后**：JSON watcher 会在 10 秒内自动检测变化，清空内存缓存。也可以在管理后台点「刷新应用缓存」立即生效。


## 六、功能详解

### 6.1 同 ID 双架构编辑（v2.8.2 修复）

**背景**：同一应用（如 `myapp`）同时存在 x86 和 ARM 两个 FPK 时，`fn-appstores.json` 里会有两条记录：

```json
[
  { "id": "myapp", "version": "1.0.0", "platform": "x86", ... },
  { "id": "myapp", "version": "1.0.0", "platform": "arm", ... }
]
```

**v2.8.1 及之前的问题**：管理后台「应用编辑」Tab 里，点其中一条的「编辑」按钮，**两条会同时进入编辑模式**；保存时又因为没带 `platform` 参数，容易改错记录。

**v2.8.2 修复**：

- 前端 `editingAppKey` 用 `id + '@' + platform` 复合键，只有键值匹配的那一条进入编辑模式
- 保存按钮传 `app.id` 和 `app.platform`，后端按 `?platform=xxx` 精确匹配
- Go 后端本来就用 `id + normalizePlatformKey(platform)` 精确匹配，无需改动

**若仍看到两条同时进入编辑**：浏览器缓存了旧的 `admin.html` / `apps.html`，强刷一次即可（Ctrl+Shift+R）。

---

### 6.2 自动公告（v2.8.1）

应用变动时自动同步到客户端公告，用户打开客户端首页就能看到最新动态，无需额外配置。

**触发条件**：

| 操作 | 是否生成公告 |
|------|:----------:|
| **新增应用** | ✅ 生成「🆕 上架」 |
| **删除应用** | ✅ 生成「🗑️ 下架」 |
| **版本号变化** | ✅ 生成「🔄 更新」 |
| 改名称 / 描述 / 标签 / 作者 / 图标 / 架构 | ❌ 不生成 |
| 只改 JSON 格式 | ❌ 不生成 |

**合并规则**：10 秒内的多次变动合并成一条公告。

**保留策略**：

- **自动公告**：保留最近 **20 条**
- **手动公告**：永久保留

**查看**：

- 客户端首页「📢 公告记录」栏自动显示
- 管理后台「公告管理」Tab 能看到全部
- 服务端直接查 `data/notice.json`，自动公告带 `"_auto": true` 标记

---

### 6.3 三方源管理

**v2.8.1 起，三方源健康检查不再自动禁用**，只标记在线/离线状态。

| 三方源状态 | 服务端动作 |
|-----------|-----------|
| 在线 | 清除失败计数，正常聚合应用 |
| **短暂离线** | 累加失败计数，继续检测 |
| **长期离线** | **不自动禁用**，只更新 `fail_count` 和 `last_check` |
| 离线后恢复 | 自动清零失败计数，重新聚合应用 |

**管理后台三方源列表**：

- 30 秒内存缓存 + 并行状态探测
- 「刷新」按钮绕过缓存
- 添加 / 删除 / 启用 / 禁用后缓存自动失效

**长期挂掉的源**：去后台「三方源管理」Tab 手动「禁用」或「删除」。

---

### 6.4 QQ 群推送（可选）

应用变动时推送到指定 QQ 群。

- 依赖 OneBot 协议（NapCat / Lagrange / go-cqhttp）
- 需要自己部署 QQ 机器人
- 与自动公告**独立运行**，互不影响

**配置入口**：管理后台「QQ群推送」Tab。


## 七、版本历史

### v2.8.2（当前版本）

**同 ID 双架构编辑修复**

- 🛠️ **同 ID 双架构精确编辑**：管理后台「应用编辑」Tab 里，同 ID 双架构（如 `myapp@x86` 和 `myapp@arm`）各自独立编辑
- 🔧 **`admin.html` 改动**：`editingAppKey` 状态键从 `id` 升级为 `id@platform`
- 🔧 **`apps.html` 改动**：编辑模式判断从 `editingAppId !== app.id` 改为 `editingAppKey !== (app.id + '@' + (app.platform || ''))`
- ✅ **Go 后端无需改动**

### v2.8.1

**双栈监听 + 数据查看改版 + 外链托管加固 + 自动公告 + 健康检查调整**

- 🌐 **IPv4 / IPv6 双栈监听**
- 📊 **数据查看改版**：按源查看应用面板
- 🛡️ **外链托管加固**：`download_url` 填 `{BASE_URL}/apps/xxx.fpk` 时不会误判为外链
- 📣 **自动公告**
- 🩺 **健康检查调整**：不再自动禁用
- ⚡ **三方源列表优化**：并行探测 + 30 秒缓存
- 📤 **上传历史**
- 🏷️ **标签 chip 交互**

### v2.8.0

**应用架构支持 + 应用评分启用 + 后台架构编辑 + 后台新增应用 + 同 ID 双架构精确匹配**

- 🏗️ **应用架构字段（`platform`）**
- 🔀 **去重键升级**：从 `id` 升级为 `id@platform`
- ⭐ **应用评分正式启用**
- ✏️ **后台可视化编辑架构**
- ⚡ **后台批量改架构**
- ➕ **后台新增应用**
- 🛠️ **同 ID 双架构精确匹配**
- 📊 **数据查看加架构分类统计**

### v2.7.0

**飞牛本地托管 + JSON 监听 + 批量推送 + 断点续传**

- 📤 飞牛本地托管上传
- 📥 断点续传（Range 请求 + 304 缓存）
- 👀 JSON 变化监听
- 📢 批量汇总推送
- 🧹 孤儿文件清理
- 🏷️ 应用类型自动识别
- 🛡️ 字段保留
- ⭐ 应用评分预留

### v2.6.0

**Go 语言重写版**

- 🚀 改用 Go 语言重写：镜像从 ~300MB 降到 ~15MB，内存从 ~50MB 降到 ~10MB
- 📤 新增 HTTP 上传 API
- 🏥 三方源健康检查
- 🛠️ 版本比较容错
- ✅ 100% 兼容 v2.5.4


## 八、开发者信息

- **开发者**：晦华先生
- **开源协议**：MIT
- **代码仓库**：[https://gitee.com/hhxs2025/fn-appstores](https://gitee.com/hhxs2025/fn-appstores)
- **问题反馈**：[https://gitee.com/hhxs2025/fn-appstores/issues](https://gitee.com/hhxs2025/fn-appstores/issues)
- **用户交流群**：QQ 2154077576
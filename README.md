# FN软仓 建源指南

> 自己搭一个 FN软仓源，把应用分享给朋友。
>
> 当前版本：**v2.8.1（Go 版）** · 更新日期：2026-09-15

---

## 一、准备

| 项目 | 说明 |
|------|------|
| 机器 | 飞牛 fnOS 或任何支持 Docker 的 Linux |
| Docker | 20.10+ |
| 公网访问 | 公网 IP 或内网穿透（FRP） |
| 素材 | `.fpk` 安装包 + PNG 图标（截图可选） |

镜像 ~15MB，运行时内存 ~10MB，飞牛随手就能跑。

---

## 二、起一个源

### 1. 建目录

```bash
mkdir -p /path/to/data/{apps,icons,previews}
```

### 2. 启动

```bash
docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p 5660:5660 \
  -e TZ=Asia/Shanghai \
  -e BASE_URL="http://你的公网IP或域名:5660" \
  -e ADMIN_PASSWORD="你的管理密码" \
  -e NOTICE_PASSWORD="你的公告员密码" \
  -v /path/to/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.8.1
```

| 变量 | 必填 | 默认 | 说明 |
|------|:----:|------|------|
| `BASE_URL` | ✅ 自托管必填 | 内置兜底域名 | 公网访问地址，不含末尾斜杠 |
| `ADMIN_PASSWORD` | 否 | `admin123` | 管理员密码 |
| `NOTICE_PASSWORD` | 否 | `notice123` | 公告员密码 |
| `TZ` | 否 | UTC | 时区 |

**`BASE_URL` 填错，图标、截图、下载地址全错。** 不含末尾 `/`。

> 需要 IPv6 双栈的话，端口改成 `-p "[::]:5660:5660"`，并在 Docker 里启用 IPv6。

### 3. 验证

```bash
curl http://你的地址:5660/health
curl http://你的地址:5660/api/apps
```

返回 JSON 即成功。

### 4. 进后台

```
http://你的地址:5660/admin
```

用 `ADMIN_PASSWORD` 登录。后台能管公告、管应用、传 FPK、看下载统计。

---

## 三、上架应用

**不用手写 JSON。** 两种托管方式都有一键工具。

### 飞牛本地托管（推荐）

进后台 →「应用上传」→ 拖 `.fpk` 进去（支持批量）。

服务端自动解析 manifest、识别类型、提取图标、写清单。10 秒内生效。

**你只需要准备好 `.fpk` 文件。**

### Gitee 托管

不想自己抗下载流量？把 FPK 放 Gitee。

进 QQ 群（**2154077576**）拿「**FN软仓应用上架助手pro-0.5.exe**」：填服务端地址后拖 FPK 进去，自动生成 JSON、重命名文件、整理目录，再帮你推到仓库。

> 客户端下载时，服务端本地找不到文件会自动 **302 跳转**到 Gitee。下载统计依然生效。
>
> ⚠️ 用 Gitee 托管时**不要改 `BASE_URL`**，它永远指服务端自己。

### 参考：清单字段

只有手动改 JSON 时才需要了解这些字段：

```json
[
  {
    "id": "myapp",
    "name": "我的应用",
    "version": "1.0.0",
    "desc": "应用描述",
    "author": "你的名字",
    "tags": "工具,效率",
    "repo": "https://gitee.com/xxx/xxx",
    "updated_at": "2026-09-15",
    "download_url": "",
    "icon": "",
    "screenshots": [],
    "type": "原生",
    "platform": "x86",
    "sort_order": 0
  }
]
```

| 字段 | 必填 | 说明 |
|------|:----:|------|
| `id` | ✅ | 唯一标识，英文/数字 |
| `name` | ✅ | 显示名称 |
| `version` | ✅ | 版本号，任意格式 |
| `desc` | ❌ | 描述，支持 HTML |
| `author` | ❌ | 作者，会显示在客户端「开发者星球」 |
| `tags` | ❌ | 分类标签，逗号隔开，最多 2 个 |
| `repo` | ❌ | 源码仓库 |
| `updated_at` | ❌ | 更新日期 `YYYY-MM-DD` |
| `download_url` | ❌ | 本地托管留空；外链托管填直链 |
| `icon` | ❌ | 留空则自动扫描 `data/icons/` |
| `screenshots` | ❌ | 留空则自动扫描 `data/previews/` |
| `type` | ❌ | `docker` / `原生`，上传时自动识别 |
| `platform` | ❌ | `x86` / `arm` / `all` / 空（空按 x86 处理） |
| `sort_order` | ❌ | 置顶权重，数字越大越靠前 |

**分类标签可选值**：影音、办公、下载、AI、设计、社交、网络、工具、生活、商务、教育、效率、开发、游戏。

**本地托管时** `download_url` / `icon` / `screenshots` 留空即可，服务端自动生成：

| 字段 | 自动生成 | 对应本地文件 |
|------|---------|-------------|
| `download_url` | `{BASE_URL}/apps/{id}-{version}.fpk` | `data/apps/myapp-1.0.0.fpk` |
| `icon` | `{BASE_URL}/icons/{id}.PNG` | `data/icons/myapp.PNG` |
| `screenshots` | `{BASE_URL}/previews/{id}/1.PNG` | `data/previews/myapp/1.PNG` |

---

## 四、自动公告（免配置）

v2.8.1 起，应用变动自动写入客户端首页公告。你什么都不用配。

**触发条件**：新增 / 删除 / **版本号变化**。改描述、标签、作者、图标、架构**不触发**。

**合并规则**：10 秒内的多次变动合并成一条公告，不刷屏。

**保留策略**：自动公告保留最近 20 条；手动公告（在「公告管理」里写的）永久保留。

自动公告和 QQ 群推送是**两条独立通道**。QQ 推送需要养号、有封号风险；自动公告零依赖，永不失效。

---

## 五、⚠️ 不要聚合其他源

**不要**在 `upstream.json` 里配其他源做多层聚合。

```
官方聚合源
    └── 你的服务端        ← 只到这里
            └── ❌ 别人的源  ← 不要再往下
```

多层聚合会导致**应用重复、版本混乱、响应变慢**。

**正确做法**：`upstream.json` 留空，只发布自己的应用，把 `BASE_URL` 提交给官方审核。

> v2.8.1 起健康检查**不再自动禁用**离线三方源，只标记状态，避免网络抖动误伤。

---

## 六、提交给官方审核

提交你的 `BASE_URL`（如 `http://your-domain:5660`）：

- QQ 群：**2154077576**
- 上架表单：https://f.wps.cn/ksform/w/write/L7KeYAD1

审核通过后官方源会聚合你，你的应用出现在所有用户的 FN软仓 里。

---

> **开发者**：晦华先生 · **协议**：MIT · **交流群**：QQ 2154077576

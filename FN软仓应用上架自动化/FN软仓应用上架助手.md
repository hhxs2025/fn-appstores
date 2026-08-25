# FN软仓应用上架助手 使用说明书

适用于 FN软仓服务端搭建者（自托管源 / 官方源管理员 / 三方源开发者）


## 一、简介

FN软仓应用上架助手是一个 Windows 桌面工具，用于将 FPK 应用包快速上架到 FN软仓服务端。

**解决的核心问题：**

| 传统方式 | 使用本工具 |
|---------|----------|
| 手动解压 FPK 查看 manifest | 自动解析 |
| 手动复制文件到 Gitee 仓库 | 自动复制 + Git 推送 |
| 手动复制文件到飞牛 data/apps/ | 自动复制（通过 SMB） |
| 手动编辑 fn-appstores.json | 自动更新 |
| 手动调用 /api/refresh | 自动刷新缓存 |
| 逐个处理多个 FPK | 批量处理 |


## 二、两种部署模式

工具支持两种部署模式，根据你的配置自动切换：

### 模式一：飞牛本地模式（纯自托管）

FPK 存放在飞牛本地 `data/apps/`，下载流量走飞牛家庭带宽。

**适用场景：**
- 家庭宽带上行够用
- 不想依赖 Gitee/GitHub
- 应用包体积较大（>50MB）
- 用户量小

**配置要求：**
- 飞牛 data 目录（必填）
- 飞牛服务端地址（必填）
- Gitee 配置（留空）

### 模式二：Gitee 分流模式（混合托管）

小文件走 Gitee CDN，大文件走飞牛本地。

**适用场景：**
- 家庭宽带有限
- 大部分应用包小于 10MB
- 希望降低飞牛带宽压力

**配置要求：**
- 飞牛 data 目录（必填）
- 飞牛服务端地址（必填）
- Gitee 仓库路径（必填）
- Gitee Raw 地址（必填）
- 本地阈值（建议 10）


## 三、环境要求

### 3.1 硬件/系统

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / Windows 11 |
| Python | Python 3.8+（或使用打包后的 exe） |
| 网络 | 能访问飞牛 NAS（内网或 VPN） |
| 飞牛 | FN软仓服务端已部署并运行 |

### 3.2 飞牛服务端要求

| 项目 | 要求 |
|------|------|
| 服务端版本 | v2.3.0 或更高（支持 /api/refresh） |
| 服务端运行状态 | 正常运行，端口可访问 |
| data 目录 | 可读写（通过 SMB 挂载） |

### 3.3 Gitee 模式额外要求

| 项目 | 要求 |
|------|------|
| Gitee 仓库 | 已创建且为公开仓库 |
| 本地仓库 | 已克隆到 Windows 本地 |
| Git | 已安装并配置好认证 |


## 四、安装与启动

1. 下载 `FN软仓应用上架助手.exe`
2. 双击运行（无需安装 Python）


## 五、配置说明

### 5.1 配置项详解

| 配置项 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| **飞牛 data 目录** | ✅ 必填 | 飞牛 FN软仓服务端的 data 挂载目录，通过 SMB 映射到 Windows | `\\192.168.3.20\docker\fn-appstores-server\data` |
| **飞牛服务端地址** | ✅ 必填 | 飞牛 FN软仓服务端的访问地址 | `http://192.168.3.20:5660` |
| **Gitee 仓库路径** | ⬜ 可选 | Gitee 仓库在 Windows 本地的路径（仅 Gitee 模式需要） | `D:\应用开发\gitee\fn-appstores` |
| **Gitee Raw 地址** | ⬜ 可选 | Gitee 仓库的 raw 访问地址（仅 Gitee 模式需要） | `https://gitee.com/用户名/仓库名/raw/master/server-data` |
| **本地阈值 (MB)** | ⬜ 可选 | 小于此值走 Gitee，大于等于走飞牛本地。填 0 或负数则全部走飞牛本地 | `10` |

### 5.2 如何获取飞牛 data 目录地址

在 Windows 文件管理器地址栏输入：
```
\\飞牛IP\docker\fn-appstores-server\data
```
例如：
```
\\192.168.3.xx\docker\fn-appstores-server\data
```

如果提示需要凭证，输入飞牛的登录账号和密码。

### 5.3 如何获取 Gitee Raw 地址

格式：
```
https://gitee.com/你的用户名/仓库名/raw/分支名/server-data
```

示例：
```
https://gitee.com/xxxx/fn-appstores/raw/master/server-data
```


## 六、使用流程

### 6.1 首次使用

1. **填写配置**
   - 必填：飞牛 data 目录、飞牛服务端地址
   - 可选：Gitee 仓库路径、Gitee Raw 地址、本地阈值

2. **点击「保存配置」**
   - 配置会自动保存，下次启动无需重填

### 6.2 上架应用

1. **添加 FPK 文件**
   - 点击「添加文件」选择单个或多个 FPK
   - 点击「添加文件夹」自动扫描文件夹内所有 FPK
   - 支持拖拽 FPK 文件到窗口

2. **点击「开始上架」**

3. **查看运行日志**
   - 日志区会显示每个文件的处理进度
   - 进度条显示整体完成情况

4. **完成验证**
   - 在 FN软仓客户端点击「刷新」
   - 新应用应出现在列表


## 七、云服务器用户特别说明

### 7.1 场景说明

如果你使用云服务器（如阿里云 ECS、腾讯云 CVM）部署 FN软仓服务端，而不是在飞牛 NAS 上运行，操作方式略有不同。

```
┌─────────────────────────────────────────────────────┐
│  你的场景：服务端在云服务器，工具在本地电脑运行      │
├─────────────────────────────────────────────────────┤
│  本地电脑 (Windows)                                │
│  ├── FN上架助手.exe                                │
│  ├── Gitee仓库 (D:\fn-appstores\)                 │
│  │   └── 通过SMB或SFTP挂载云服务器data目录        │
│  └── 运行上架助手 → 自动更新云服务器data           │
│                                                    │
│  云服务器                                          │
│  ├── FN软仓服务端 Docker容器                       │
│  ├── data/ 目录                                   │
│  │   ├── fn-appstores.json                        │
│  │   └── apps/                                   │
│  └── 服务端地址: http://公网IP:5660              │
└─────────────────────────────────────────────────────┘
```

### 7.2 云服务器 data 目录的访问方式

| 方式 | 说明 | 推荐度 |
|------|------|--------|
| **SMB 挂载** | 在云服务器上安装 Samba，将 data 目录共享出来，Windows 直接映射为网络驱动器 | ⭐⭐⭐⭐⭐ |
| **SFTP 映射** | 使用 SFTP 工具（如 WinSCP）将云服务器目录映射为本地盘 | ⭐⭐⭐ |


### 7.3 推荐方式：SMB 挂载

**在云服务器上配置 SMB 共享：**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install samba samba-common-bin
sudo smbpasswd -a 你的用户名

# 编辑 /etc/samba/smb.conf，添加：
[fn-data]
   path = /path/to/fn-appstores-server/data
   browseable = yes
   read only = no
   guest ok = no
   valid users = 你的用户名

sudo systemctl restart smbd
```

**在 Windows 上映射网络驱动器：**
- 地址：`\\云服务器IP\fn-data`
- 凭证：云服务器的 SMB 用户名和密码

### 7.4 云服务器场景配置示例

```
配置 (飞牛必填，Gitee可选)
├── 飞牛 data 目录: \\123.45.67.89\fn-data
├── 飞牛服务端地址: http://123.45.67.89:5660
├── Gitee 仓库路径: D:\应用开发\gitee\fn-appstores
├── Gitee Raw 地址: https://gitee.com/hhxs2025/fn-appstores/raw/master/server-data
└── 本地阈值 (MB): 10
```

### 7.5 注意事项

| 注意点 | 说明 |
|--------|------|
| **安全组/防火墙** | 云服务器需开放 5660 端口（FN软仓服务端）和 445 端口（SMB，建议限制来源 IP） |
| **SMB 安全** | 建议仅允许你的本地电脑 IP 访问 SMB，避免暴露到公网 |
| **云服务器带宽** | 如果走飞牛本地模式，FPK 下载流量会消耗云服务器出站带宽（需付费） |
| **SMB 性能** | SMB 挂载受网络延迟影响，批量处理大量文件时可能稍慢 |


## 八、目录结构说明

### 8.1 使用本工具后，你的 Gitee 仓库结构

```
fn-appstores/                         # Gitee 仓库根目录
└── server-data/
    ├── apps/                         # FPK 文件 (工具自动复制)
    │   ├── dockfn-0.1.0.fpk
    │   └── file-tools-0.1.53.fpk
    ├── icons/                        # 应用图标 (工具自动提取)
    │   ├── dockfn.PNG
    │   └── file-tools.PNG
    └── previews/                     # 应用截图 (手动维护)
```

### 8.2 飞牛服务端 data 目录结构

```
data/                                 # 飞牛服务端挂载目录
├── fn-appstores.json                 # 应用清单 (工具自动更新)
├── apps/                             # FPK 文件 (大文件走这里)
│   └── file-collector-2.4.0.fpk
├── icons/                            # 图标 (大文件走这里)
│   └── file-collector.PNG
├── previews/                         # 截图
├── notice.json                       # 公告
└── stats.db                          # 下载统计
```


## 九、常见问题

### Q1：飞牛 data 目录连不上？

1. 确认飞牛已开启 SMB 共享
2. 确认飞牛 IP 地址正确
3. 确认飞牛共享路径正确
4. 在 Windows 文件管理器尝试 `\\飞牛IP\docker\fn-appstores-server\data`

### Q2：Gitee 推送失败？

1. 确认 Git 已安装：`git --version`
2. 确认 Gitee 仓库路径正确
3. 确认已配置 Gitee 认证：
   ```bash
   cd D:\应用开发\gitee\fn-appstores
   git push
   ```
   手动推送一次确认认证通过

### Q3：发行版应用被自动跳过？

工具检测到 `server-data/icons-re/` 目录下已有同名图标，认为这是发行版应用（FPK 存放在其他开发者仓库），自动跳过，需手动处理。

### Q4：客户端看不到新上架的应用？

1. 确认服务端日志无错误
2. 在客户端「源管理」点击「刷新」
3. 检查 `fn-appstores.json` 是否已更新
4. 浏览器访问 `http://飞牛IP:5660/api/apps` 查看返回数据

### Q5：多个 FPK 批量处理会卡吗？

不会。工具使用独立工作线程处理，界面保持响应，进度条实时更新。

### Q6：能不能只配置飞牛，不配 Gitee？

可以。Gitee 配置全部留空，自动切换为「仅飞牛本地模式」，所有 FPK 存到飞牛 `data/apps/`。



<h1>FN软仓服务端重大升级--- 自托管搭建指南</h1>
<blockquote>
<p>v2.5.1 版本</p>
</blockquote>
<h2>一、概述</h2>
<p>FN软仓服务端是一个基于 Docker 的轻量级应用商店后端服务，提供应用列表 API 和 <code>.fpk</code> 文件下载。开发者可以自托管此服务端，成为 FN软仓客户端的一个"软件源"。</p>
<p>其他用户通过 FN软仓客户端添加你的服务端地址后，即可浏览和安装你收录的应用，并在首页查看你发布的公告。</p>
<h3>版本特性概览</h3>
<table>
<thead>
<tr>
<th align="left">版本</th>
<th align="left">核心功能</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left"><strong>v2.1.0</strong></td>
<td align="left">基础服务：应用列表 API、FPK 下载、图标/截图服务、健康检查</td>
</tr>
<tr>
<td align="left"><strong>v2.2.0</strong></td>
<td align="left">新增公告板（<code>notice.json</code>），支持 Markdown 渲染</td>
</tr>
<tr>
<td align="left"><strong>v2.3.0</strong></td>
<td align="left">新增应用下载统计（SQLite 持久化）、统计接口、强制刷新接口、自动提取 app_id</td>
</tr>
<tr>
<td align="left"><strong>v2.3.1</strong></td>
<td align="left">新增 <code>BASE_URL</code> 环境变量支持，解决跨设备/中继访问时图标和截图 404 的问题</td>
</tr>
<tr>
<td align="left"><strong>v2.4.0</strong></td>
<td align="left">新增树状聚合架构，支持 <code>upstream.json</code> 三方源白名单聚合，官方源可作为统一入口分发三方源应用</td>
</tr>
<tr>
<td align="left"><strong>v2.4.1</strong></td>
<td align="left">移除 <code>request.host</code> 回退；新增双兜底域名；三方源拉取增强（超时延长+重试机制）；BASE_URL未设置时打印醒目警告提示</td>
</tr>
<tr>
<td align="left"><strong>v2.5.0</strong></td>
<td align="left">新增公告管理后台（<code>/admin</code>）；公告格式升级（轮播图 + 公告记录）；新增最近更新接口（<code>/api/recent</code>）；应用清单新增 <code>updated_at</code> 字段；管理后台密码环境变量；新增三方源管理 Tab（在线增删改 <code>upstream.json</code>）</td>
</tr>
<tr>
<td align="left"><strong>v2.5.1</strong></td>
<td align="left"><strong>强制下载地址重写 + 302 重定向统计</strong>（解决 Gitee 托管应用无法统计下载量）；管理后台新增「刷新应用缓存」按钮；新增「使用说明」Tab；新增数据查看接口；新增客户端自更新接口；三方源管理 API 完善</td>
</tr>
</tbody>
</table>
<h2>二、环境要求</h2>
<ul>
<li>飞牛 fnOS 系统（或任意支持 Docker 的 Linux 系统）</li>
<li>Docker 20.10+</li>
<li>公网 IP 或内网穿透（如需对外提供服务）</li>
</ul>
<h2>三、文件说明</h2>
<table>
<thead>
<tr>
<th>文件</th>
<th>说明</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>fn-appstores-server-{version}.tar</code></td>
<td>Docker 镜像包（或从镜像仓库拉取）</td>
</tr>
<tr>
<td><code>data/</code> 文件夹（需自行准备）</td>
<td>挂载到容器内的数据目录，存放应用清单、安装包、公告、统计数据等</td>
</tr>
<tr>
<td><code>static/admin.html</code></td>
<td>管理后台页面文件（v2.5.0 新增，v2.5.1 更新），需放在容器 <code>/app/static/</code> 目录</td>
</tr>
</tbody>
</table>
<h2>四、快速开始</h2>
<h3>1. 导入镜像</h3>
<p><strong>方式一：从镜像仓库拉取（推荐）</strong></p>
<pre><code class="language-bash">docker pull ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.5.1
</code></pre>
<p><strong>方式二：从 tar 文件导入</strong></p>
<pre><code class="language-bash">docker load -i fn-appstores-server-2.5.1.tar
</code></pre>
<h3>2. 准备数据目录</h3>
<p>创建数据目录：</p>
<pre><code class="language-bash">mkdir -p /vol1/1000/docker/fn-appstores-server/data/{apps,icons,previews}
</code></pre>
<p>将 <code>fn-appstores.json</code> 放入 <code>data/</code> 目录，将 <code>.fpk</code> 安装包放入 <code>data/apps/</code>，图标放入 <code>data/icons/</code>，截图放入 <code>data/previews/{app_id}/</code>。【可加群借助快捷工具处理】</p>
<h3>3. 启动容器</h3>
<p><strong>⚠️ v2.5.1 重要提醒</strong>：由于服务端会强制重写所有 <code>download_url</code> 为 <code>{BASE_URL}/apps/{filename}</code>，<strong>自托管源搭建者必须设置 <code>BASE_URL</code> 环境变量</strong>，否则所有下载地址将指向官方兜底域名，导致 404。</p>
<p><strong>推荐启动命令（设置 BASE_URL 和管理后台密码）：</strong></p>
<pre><code class="language-bash">docker run -d \
  --name fn-appstores-server \
  --restart unless-stopped \
  -p 5660:5660 \
  -e TZ=Asia/Shanghai \
  -e BASE_URL="http://你的公网域名或IP:5660" \
  -e ADMIN_PASSWORD="你的密码" \
  -v /vol1/1000/docker/fn-appstores-server/data:/app/data \
  ccr.ccs.tencentyun.com/hhxs2025/fn-appstores-server:2.5.1
</code></pre>
<p><strong>参数说明</strong>：</p>
<table>
<thead>
<tr>
<th>参数</th>
<th>说明</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>-d</code></td>
<td>后台运行</td>
</tr>
<tr>
<td><code>--name</code></td>
<td>容器名称</td>
</tr>
<tr>
<td><code>--restart unless-stopped</code></td>
<td>自动重启</td>
</tr>
<tr>
<td><code>-p 5660:5660</code></td>
<td>端口映射（宿主机:容器）</td>
</tr>
<tr>
<td><code>-e TZ=Asia/Shanghai</code></td>
<td>时区设置</td>
</tr>
<tr>
<td><code>-e BASE_URL="..."</code></td>
<td><strong>必填</strong>：强制指定资源访问地址（图标/截图/FPK 下载），v2.5.1 尤其重要</td>
</tr>
<tr>
<td><code>-e ADMIN_PASSWORD="..."</code></td>
<td>管理后台登录密码（v2.5.0 新增，默认 <code>admin123</code>）</td>
</tr>
<tr>
<td><code>-v ...:/app/data</code></td>
<td>挂载数据目录</td>
</tr>
</tbody>
</table>

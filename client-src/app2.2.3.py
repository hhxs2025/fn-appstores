# ====================加载 vendor 依赖==============================
import sys
import os

# 判断运行环境
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# 加载 vendor
vendor_path = os.path.join(base_dir, 'vendor')
if os.path.exists(vendor_path):
    sys.path.insert(0, vendor_path)
else:
    print(f"⚠️ vendor 目录不存在: {vendor_path}")

# ======================第三方库导入=============================
import json
import subprocess
import tempfile
import requests
import threading
import logging
import time
import uuid
import re
import tarfile
import shutil
import sqlite3
import glob
from datetime import datetime
from collections import defaultdict
from flask import Flask, render_template, jsonify, request, Response, send_from_directory
from flask_cors import CORS
from flask_sock import Sock

flask_app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, 'templates')
)
CORS(flask_app)
sock = Sock(flask_app)

# ========== 配置 ==========
PORT = 5660
DATA_DIR = os.path.join(base_dir, 'data')

# ========== 缓存配置 ==========
CACHE_TTL = 86400  # 24小时
RATE_LIMIT_MAX = 5

# ================================================================
# ========== 源状态缓存配置（v2.2.2） ==========
# ================================================================
_source_status_cache = {}
_cache_time = 0
SOURCE_CACHE_TTL = 300  # 5分钟

# ================================================================
# ========== 默认软件源配置 ==========
# ================================================================

DEFAULT_SOURCES = [
    {
        "id": "official",
        "name": "FN软仓官方源",
        "url": "http://rc.hhxs2026.top:5660",
        "enabled": True,
        "added_at": datetime.now().isoformat()
    }
]

# ================================================================
# ========== 源管理（核心） ==========
# ================================================================

def get_sources_path():
    """获取 sources.json 文件路径"""
    return os.path.join(DATA_DIR, 'sources.json')

def load_sources():
    """加载源列表，首次启动自动创建默认源"""
    sources_path = get_sources_path()
    
    # 确保 data 目录存在
    os.makedirs(DATA_DIR, mode=0o755, exist_ok=True)
    
    if not os.path.exists(sources_path):
        print(f"📝 sources.json 不存在，创建默认源配置")
        with open(sources_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_SOURCES, f, ensure_ascii=False, indent=2)
        return DEFAULT_SOURCES.copy()
    
    try:
        with open(sources_path, 'r', encoding='utf-8') as f:
            sources = json.load(f)
        print(f"✅ 加载 {len(sources)} 个软件源")
        return sources
    except Exception as e:
        print(f"⚠️ 读取 sources.json 失败: {e}，使用默认配置")
        return DEFAULT_SOURCES.copy()

def save_sources(sources):
    """保存软件源列表到文件"""
    sources_path = get_sources_path()
    try:
        with open(sources_path, 'w', encoding='utf-8') as f:
            json.dump(sources, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ 保存 sources.json 失败: {e}")
        return False

def get_enabled_sources():
    """获取所有启用的软件源"""
    sources = load_sources()
    return [s for s in sources if s.get('enabled', True)]

def test_source_connectivity(url):
    """测试单个源地址是否可访问"""
    try:
        resp = requests.head(f'{url}/api/apps', timeout=5)
        if resp.status_code < 400:
            return True, "连接成功"
        return False, f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "连接超时"
    except requests.exceptions.ConnectionError:
        return False, "无法连接"
    except Exception as e:
        return False, str(e)

def fetch_apps_from_source(source):
    """从单个源拉取应用列表"""
    url = source.get('url')
    name = source.get('name', url)
    
    try:
        resp = requests.get(f'{url}/api/apps', timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                apps = data.get('data', [])
                # 为每个应用标记来源
                for app in apps:
                    app['_source_id'] = source.get('id')
                    app['_source_name'] = name
                    app['_source_url'] = url
                print(f"✅ 从 {name} 拉取 {len(apps)} 个应用")
                return apps
        return []
    except Exception as e:
        print(f"⚠️ 从 {name} 拉取失败: {e}")
        return []

def merge_apps_from_sources():
    """从所有启用的源拉取并合并应用列表"""
    sources = get_enabled_sources()
    if not sources:
        print("⚠️ 没有启用的软件源")
        return []
    
    all_apps = []
    app_map = {}  # 用于去重，key: app_id, value: (app, source_priority)
    
    for source in sources:
        apps = fetch_apps_from_source(source)
        for app in apps:
            app_id = app.get('id')
            if not app_id:
                continue
            
            # 如果应用已存在，比较版本，保留较新的
            if app_id in app_map:
                existing_app, existing_version = app_map[app_id]
                new_version = app.get('version', '0')
                if compare_versions(new_version, existing_version) > 0:
                    app_map[app_id] = (app, new_version)
            else:
                app_map[app_id] = (app, app.get('version', '0'))
    
    # 提取应用列表
    result = [app for app, _ in app_map.values()]
    print(f"✅ 合并后共 {len(result)} 个应用")
    return result

# ================================================================
# ========== 日志功能（脱敏） ==========
# ================================================================

def sanitize_log(text):
    if not isinstance(text, str):
        return text
    return re.sub(r'https?://[^\s]+', '[*****]', text)

def get_log_file():
    log_dir = os.environ.get('TRIM_PKGVAR', os.path.join(DATA_DIR, 'data'))
    return os.path.join(log_dir, 'app.log')

def log_operation(action, detail, user='system'):
    log_file = get_log_file()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    detail_safe = sanitize_log(detail)
    log_line = f"[{timestamp}] {user} - {action}: {detail_safe}"
    try:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, mode=0o755, exist_ok=True)
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) >= 500:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines[-400:])
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    except:
        pass

def get_sanitized_logs():
    log_file = get_log_file()
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        logs.append(sanitize_log(line))
        except:
            pass
    return logs

# ================================================================
# ========== 版本号相关 ==========
# ================================================================

def get_app_version():
    version = os.environ.get('TRIM_APPVER')
    if version:
        return version
    manifest_path = os.path.join(base_dir, '..', 'manifest')
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('version='):
                        return line.split('=', 1)[1].strip()
                    elif line.startswith('version:'):
                        return line.split(':', 1)[1].strip()
        except:
            pass
    return '2.2.2'

def compare_versions(v1, v2):
    if not v1 or not v2:
        return 0
    v1 = str(v1).replace('v', '').replace('V', '').strip()
    v2 = str(v2).replace('v', '').replace('V', '').strip()
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    for i in range(max(len(parts1), len(parts2))):
        a = parts1[i] if i < len(parts1) else 0
        b = parts2[i] if i < len(parts2) else 0
        if a > b:
            return 1
        if a < b:
            return -1
    return 0

# ================================================================
# ========== 获取应用列表（多源模式） ==========
# ================================================================

def get_all_apps(force_refresh=False):
    cache_key = 'all_apps_list'

    if not force_refresh:
        cached = getattr(flask_app, '_app_cache', None)
        if cached and cached.get('key') == cache_key:
            cache_time = cached.get('time', 0)
            if time.time() - cache_time < CACHE_TTL:
                print(f"✅ 使用缓存应用列表")
                return cached.get('value', [])

    # 从所有启用的源拉取合并
    apps = merge_apps_from_sources()

    if not apps:
        return []

    # 补全资源 URL（使用官方源作为默认 base_url）
    default_url = get_default_source_url()
    for app in apps:
        app_id = app.get('id')
        if not app_id:
            continue

        # 如果应用没有 download_url，补全
        if 'download_url' not in app or not app['download_url']:
            version = app.get('version', '')
            fpk_filename = f'{app_id}-{version}.fpk'
            # 使用应用来源的 url 或默认官方源
            source_url = app.get('_source_url', default_url)
            app['download_url'] = f"{source_url}/apps/{fpk_filename}"
        
        # 如果应用没有 icon，补全
        if 'icon' not in app or not app['icon']:
            source_url = app.get('_source_url', default_url)
            app['icon'] = f"{source_url}/icons/{app_id}.PNG"

    # 标记已安装状态
    installed_apps = get_installed_apps()
    installed_versions = get_installed_apps_with_versions()
    installed_versions_dict = {app['id']: app['version'] for app in installed_versions}
    for app in apps:
        app_id = app.get('id')
        app['installed'] = app_id in installed_apps
        if app_id in installed_versions_dict:
            app['installed_version'] = installed_versions_dict[app_id]
            app['has_update'] = compare_versions(
                app.get('version', ''),
                app.get('installed_version', '')
            ) > 0
        else:
            app['has_update'] = False

    flask_app._app_cache = {
        'key': cache_key,
        'value': apps,
        'time': time.time()
    }

    return apps

def get_default_source_url():
    """获取默认官方源地址"""
    sources = load_sources()
    for s in sources:
        if s.get('default', False) or s.get('id') == 'official':
            return s.get('url', 'http://rc.hhxs2026.top:5660')
    return 'http://rc.hhxs2026.top:5660'

def get_app_by_id(app_id):
    apps = get_all_apps()
    for app in apps:
        if app.get('id') == app_id:
            return app
    return None

# ================================================================
# ========== 已安装应用 ==========
# ================================================================

def get_installed_apps():
    installed = []
    try:
        for base in glob.glob('/vol*/@appcenter'):
            if os.path.exists(base):
                for item in os.listdir(base):
                    full_path = os.path.join(base, item)
                    if os.path.isdir(full_path) and not item.startswith('.'):
                        installed.append(item)
        system_app_dir = '/usr/local/apps/@appcenter/'
        if os.path.exists(system_app_dir):
            for item in os.listdir(system_app_dir):
                if os.path.isdir(os.path.join(system_app_dir, item)) and not item.startswith('.'):
                    if item not in installed:
                        installed.append(item)
    except Exception as e:
        print(f"读取目录失败: {e}")
    return installed

def get_installed_apps_with_versions():
    installed = []
    try:
        for base in glob.glob('/vol*/@appcenter'):
            if os.path.exists(base):
                for item in os.listdir(base):
                    full_path = os.path.join(base, item)
                    if os.path.isdir(full_path) and not item.startswith('.'):
                        manifest_candidates = [
                            os.path.join(full_path, 'manifest'),
                            os.path.join(full_path, 'target', 'manifest'),
                            f'/var/apps/{item}/manifest',
                        ]
                        version = ''
                        app_id = item
                        for cand in manifest_candidates:
                            if os.path.exists(cand):
                                try:
                                    with open(cand, 'r') as f:
                                        content = f.read()
                                        match = re.search(r'version\s*[=:]\s*(v?[\d.]+)', content, re.IGNORECASE)
                                        if match:
                                            version = match.group(1)
                                        match_id = re.search(r'appId\s*[=:]\s*(\S+)', content, re.IGNORECASE)
                                        if match_id:
                                            app_id = match_id.group(1).strip()
                                        elif re.search(r'appname\s*[=:]\s*(\S+)', content, re.IGNORECASE):
                                            appname_match = re.search(r'appname\s*[=:]\s*(\S+)', content, re.IGNORECASE)
                                            if appname_match:
                                                app_id = appname_match.group(1).strip()
                                        break
                                except:
                                    continue
                        installed.append({
                            'id': app_id,
                            'version': version,
                            'dir': item
                        })
        return installed
    except Exception as e:
        print(f"读取已安装应用失败: {e}")
        return []

# ================================================================
# ========== 限流器 ==========
# ================================================================

rate_limit_storage = defaultdict(list)

def check_rate_limit(client_key, action='refresh'):
    config = {
        'refresh': {'max': RATE_LIMIT_MAX, 'window': 60},
        'install': {'max': 5, 'window': 300},
    }.get(action, {'max': 10, 'window': 60})
    now = time.time()
    window = config['window']
    max_requests = config['max']
    rate_limit_storage[client_key] = [
        t for t in rate_limit_storage[client_key]
        if now - t < window
    ]
    if len(rate_limit_storage[client_key]) >= max_requests:
        oldest = rate_limit_storage[client_key][0]
        wait_time = int(window - (now - oldest)) + 1
        return False, wait_time
    rate_limit_storage[client_key].append(now)
    return True, 0

# ================================================================
# ========== 卸载执行 ==========
# ================================================================

def uninstall_app(app_id):
    try:
        cmd = ['/usr/local/bin/appcenter-cli', 'uninstall', app_id]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            log_operation('卸载', f'{app_id}')
            return {'success': True, 'message': '卸载成功'}
        return {'success': False, 'message': result.stderr}
    except Exception as e:
        return {'success': False, 'message': str(e)}

# ================================================================
# ========== 安装执行（带进度） ==========
# ================================================================

_wizard_sessions = {}

def extract_fpk(fpk_path):
    base_dir = os.path.dirname(fpk_path)
    extract_dir = os.path.join(base_dir, 'fpk_extract')
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    try:
        with tarfile.open(fpk_path, 'r:gz') as tar:
            tar.extractall(extract_dir)
        return extract_dir
    except Exception as e:
        print(f"解压 .fpk 失败: {e}")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        return None

def parse_wizard_config(extract_dir, wizard_type='install'):
    wizard_file = os.path.join(extract_dir, 'wizard', wizard_type)
    if not os.path.exists(wizard_file):
        return None
    try:
        with open(wizard_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return {'config': config, 'wizard_file': wizard_file}
    except Exception as e:
        print(f"解析 wizard/{wizard_type} 失败: {e}")
        return None

def cleanup_wizard_files(tmp_dir):
    try:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        return True
    except Exception as e:
        print(f"清理失败: {e}")
        return False

def refresh_app_status(app_id):
    try:
        subprocess.run(['/usr/local/bin/appcenter-cli', 'list', '--refresh'],
                       capture_output=True, timeout=10)
        time.sleep(2)
        subprocess.run(['/usr/local/bin/appcenter-cli', 'start', app_id],
                       capture_output=True, timeout=30)
        time.sleep(2)
        subprocess.run(['/usr/local/bin/appcenter-cli', 'list', '--refresh'],
                       capture_output=True, timeout=10)
        return True
    except Exception as e:
        print(f"刷新应用状态失败: {e}")
        return False

def install_app_with_progress(app_id, download_url, ws):
    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp(prefix=f'fnsoft_{app_id}_')
        fpk_path = os.path.join(tmp_dir, f'{app_id}.fpk')

        ws.send(json.dumps({
            'event': 'progress',
            'data': {
                'app_id': app_id,
                'status': 'downloading',
                'msg': '连接中...',
                'progress': 0,
                'stage': 'download'
            }
        }))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://gitee.com/"
        }

        resp = requests.get(download_url, headers=headers, stream=True, timeout=120, allow_redirects=True)
        if resp.status_code != 200:
            ws.send(json.dumps({
                'event': 'result',
                'data': {
                    'app_id': app_id,
                    'status': 'error',
                    'msg': f'下载失败: HTTP {resp.status_code}'
                }
            }))
            cleanup_wizard_files(tmp_dir)
            return

        total_size = int(resp.headers.get('content-length', 0))
        downloaded = 0
        start_time = time.time()
        last_update = 0

        with open(fpk_path, 'wb') as f:
            for chunk in resp.iter_content(8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    if now - last_update > 0.5:
                        last_update = now
                        if total_size > 0:
                            progress = min(100, int(downloaded / total_size * 100))
                        else:
                            progress = 0

                        elapsed = now - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        speed_str = f"{speed/1024:.1f} KB/s" if speed < 1024*1024 else f"{speed/1024/1024:.1f} MB/s"
                        downloaded_str = f"{downloaded/1024/1024:.1f} MB" if downloaded > 1024*1024 else f"{downloaded/1024:.1f} KB"
                        total_str = f"{total_size/1024/1024:.1f} MB" if total_size > 1024*1024 else f"{total_size/1024:.1f} KB"

                        ws.send(json.dumps({
                            'event': 'progress',
                            'data': {
                                'app_id': app_id,
                                'status': 'downloading',
                                'msg': f'下载中... {progress}% ({downloaded_str}/{total_str})',
                                'progress': progress,
                                'downloaded': downloaded,
                                'total': total_size,
                                'speed': speed,
                                'speed_str': speed_str,
                                'eta': 0,
                                'stage': 'download'
                            }
                        }))

        ws.send(json.dumps({
            'event': 'progress',
            'data': {
                'app_id': app_id,
                'status': 'extracting',
                'msg': '解压中...',
                'progress': 100,
                'stage': 'extract'
            }
        }))

        extract_dir = extract_fpk(fpk_path)
        if not extract_dir:
            ws.send(json.dumps({
                'event': 'result',
                'data': {
                    'app_id': app_id,
                    'status': 'error',
                    'msg': '解压失败'
                }
            }))
            cleanup_wizard_files(tmp_dir)
            return

        wizard_config = parse_wizard_config(extract_dir, 'install')
        has_install_wizard = wizard_config is not None and wizard_config.get('config')

        if has_install_wizard:
            session_id = f"{app_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            _wizard_sessions[session_id] = {
                'app_id': app_id,
                'fpk_path': fpk_path,
                'tmp_dir': tmp_dir,
                'extract_dir': extract_dir,
                'wizard_config': wizard_config,
                'wizard_type': 'install',
                'step': 'waiting_for_input'
            }
            ws.send(json.dumps({
                'event': 'wizard.show',
                'data': {
                    'app_id': app_id,
                    'session_id': session_id,
                    'type': 'install',
                    'steps': wizard_config['config'],
                    'title': '安装向导'
                }
            }))
            return

        ws.send(json.dumps({
            'event': 'progress',
            'data': {
                'app_id': app_id,
                'status': 'installing',
                'msg': '安装中...',
                'progress': 100,
                'stage': 'install'
            }
        }))

        uninstall_app(app_id)
        time.sleep(1)

        cmd = ['/usr/local/bin/appcenter-cli', 'install-fpk', '--volume', '1', fpk_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        cleanup_wizard_files(tmp_dir)

        if result.returncode == 0:
            refresh_app_status(app_id)
            ws.send(json.dumps({
                'event': 'result',
                'data': {
                    'app_id': app_id,
                    'status': 'success',
                    'msg': '安装成功'
                }
            }))
            log_operation('安装', f'{app_id}')
        else:
            ws.send(json.dumps({
                'event': 'result',
                'data': {
                    'app_id': app_id,
                    'status': 'error',
                    'msg': result.stderr or '安装失败'
                }
            }))

    except Exception as e:
        log_operation('安装失败', f'{app_id}: {str(e)}')
        ws.send(json.dumps({
            'event': 'result',
            'data': {
                'app_id': app_id,
                'status': 'error',
                'msg': str(e)
            }
        }))
        if tmp_dir:
            cleanup_wizard_files(tmp_dir)

@flask_app.route('/api/wizard/install', methods=['POST'])
def api_wizard_install():
    data = request.get_json()
    session_id = data.get('session_id')
    user_inputs = data.get('inputs', {})

    if not session_id or session_id not in _wizard_sessions:
        return jsonify({'success': False, 'message': '会话已过期，请重新安装'})

    session_data = _wizard_sessions[session_id]
    app_id = session_data['app_id']
    fpk_path = session_data['fpk_path']
    extract_dir = session_data['extract_dir']
    tmp_dir = session_data['tmp_dir']

    env_file = os.path.join(extract_dir, 'wizard.env')
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            for key, value in user_inputs.items():
                if not key.startswith('wizard_'):
                    key = f'wizard_{key}'
                f.write(f"{key}={value}\n")
    except Exception as e:
        cleanup_wizard_files(tmp_dir)
        del _wizard_sessions[session_id]
        return jsonify({'success': False, 'message': f'写入环境文件失败: {str(e)}'})

    uninstall_app(app_id)
    time.sleep(1)

    cmd = ['/usr/local/bin/appcenter-cli', 'install-fpk', '--volume', '1', fpk_path, '--env', env_file]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    cleanup_wizard_files(tmp_dir)
    del _wizard_sessions[session_id]

    if result.returncode == 0:
        refresh_app_status(app_id)
        log_operation('安装完成', f'{app_id} 带向导安装')
        return jsonify({'success': True, 'message': '安装成功'})
    else:
        log_operation('安装失败', f'{app_id}: {result.stderr}')
        return jsonify({'success': False, 'message': result.stderr})

@flask_app.route('/api/wizard/cancel', methods=['POST'])
def api_wizard_cancel():
    data = request.get_json()
    session_id = data.get('session_id')
    if session_id and session_id in _wizard_sessions:
        session_data = _wizard_sessions[session_id]
        cleanup_wizard_files(session_data['tmp_dir'])
        del _wizard_sessions[session_id]
        return jsonify({'success': True, 'message': '已取消'})
    return jsonify({'success': False, 'message': '会话不存在'})

# ================================================================
# ========== 软件源管理 API ==========
# ================================================================

@flask_app.route('/api/sources', methods=['GET'])
def api_get_sources():
    """获取软件源列表，支持缓存和按需刷新（v2.2.2）"""
    global _source_status_cache, _cache_time
    force = request.args.get('force', 'false').lower() == 'true'
    sources = load_sources()
    
    # 判断是否需要重新探测
    now = time.time()
    need_refresh = force or (now - _cache_time > SOURCE_CACHE_TTL) or not _source_status_cache
    
    if need_refresh:
        status_map = {}
        for source in sources:
            url = source.get('url')
            if url:
                ok, msg = test_source_connectivity(url)
                status_map[url] = {'status': 'online' if ok else 'offline', 'msg': msg}
        _source_status_cache = status_map
        _cache_time = now
    
    # ============================================================
    # 组装返回数据（改动处：被禁用的源显示为 "disabled"）
    # ============================================================
    for source in sources:
        url = source.get('url')
        # 如果源被禁用，直接标记为 disabled，跳过探测结果
        if not source.get('enabled', True):
            source['status'] = 'disabled'
            source['status_msg'] = '已禁用'
        elif url and url in _source_status_cache:
            source['status'] = _source_status_cache[url]['status']
            source['status_msg'] = _source_status_cache[url]['msg']
        else:
            source['status'] = 'unknown'
            source['status_msg'] = '未检测'
    
    return jsonify({"success": True, "data": sources})

@flask_app.route('/api/sources/add', methods=['POST'])
def api_add_source():
    """添加新软件源"""
    data = request.get_json()
    name = data.get('name', '').strip()
    url = data.get('url', '').strip()
    
    if not name or not url:
        return jsonify({"success": False, "message": "名称和地址不能为空"})
    
    # 验证 URL 格式
    if not url.startswith('http://') and not url.startswith('https://'):
        return jsonify({"success": False, "message": "地址必须以 http:// 或 https:// 开头"})
    
    # 去除末尾斜杠
    url = url.rstrip('/')
    
    # 检查是否已存在相同 URL
    sources = load_sources()
    for s in sources:
        if s.get('url') == url:
            return jsonify({"success": False, "message": "该地址已存在"})
    
    # 测试源可用性
    ok, msg = test_source_connectivity(url)
    if not ok:
        return jsonify({"success": False, "message": f"无法连接到该源: {msg}"})
    
    # 添加新源
    new_source = {
        "id": f"source_{int(time.time())}",
        "name": name,
        "url": url,
        "enabled": True,
        "added_at": datetime.now().isoformat()
    }
    sources.append(new_source)
    
    if not save_sources(sources):
        return jsonify({"success": False, "message": "保存配置失败"})
    
    log_operation('添加源', f'{name} ({url})')
    return jsonify({"success": True, "data": new_source, "message": "添加成功"})

@flask_app.route('/api/sources/remove', methods=['POST'])
def api_remove_source():
    """删除软件源"""
    data = request.get_json()
    source_id = data.get('id')
    
    if not source_id:
        return jsonify({"success": False, "message": "缺少源 ID"})
    
    sources = load_sources()
    
    # 检查是否是默认源（不允许删除官方源）
    for s in sources:
        if s.get('id') == source_id and s.get('id') in ['official', 'official_backup']:
            return jsonify({"success": False, "message": "不能删除官方源"})
    
    new_sources = [s for s in sources if s.get('id') != source_id]
    
    if len(new_sources) == len(sources):
        return jsonify({"success": False, "message": "源不存在"})
    
    if not save_sources(new_sources):
        return jsonify({"success": False, "message": "保存配置失败"})
    
    log_operation('删除源', f'{source_id}')
    return jsonify({"success": True, "message": "删除成功"})

@flask_app.route('/api/sources/toggle', methods=['POST'])
def api_toggle_source():
    """启用/禁用软件源"""
    data = request.get_json()
    source_id = data.get('id')
    enabled = data.get('enabled', True)
    
    if not source_id:
        return jsonify({"success": False, "message": "缺少源 ID"})
    
    sources = load_sources()
    found = False
    for s in sources:
        if s.get('id') == source_id:
            s['enabled'] = enabled
            found = True
            break
    
    if not found:
        return jsonify({"success": False, "message": "源不存在"})
    
    if not save_sources(sources):
        return jsonify({"success": False, "message": "保存配置失败"})
    
    status = '启用' if enabled else '禁用'
    log_operation('切换源状态', f'{source_id} -> {status}')
    return jsonify({"success": True, "message": f"已{status}"})

@flask_app.route('/api/sources/test', methods=['POST'])
def api_test_source():
    """测试源地址是否可访问"""
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({"success": False, "message": "地址不能为空"})
    
    ok, msg = test_source_connectivity(url)
    return jsonify({
        "success": ok,
        "message": msg,
        "url": url
    })

# ================================================================
# ========== 🆕 公告接口 ==========
# ================================================================

@flask_app.route('/api/notice')
def api_notice():
    """从 sources.json 中读取所有启用的源，依次尝试拉取公告"""
    sources = load_sources()
    enabled_sources = [s for s in sources if s.get('enabled', True)]
    
    for source in enabled_sources:
        url = source.get('url', '').rstrip('/')
        if not url:
            continue
        notice_url = f"{url}/api/notice"
        try:
            resp = requests.get(notice_url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('enabled'):
                    return jsonify(data)
        except:
            continue
    
    return jsonify({"enabled": False})

# ================================================================
# ========== 原有路由 ==========
# ================================================================

@flask_app.route('/')
def index():
    version = get_app_version()
    return render_template('index.html', version=version)

@flask_app.route('/api/apps')
def api_apps():
    client_key = request.remote_addr
    allowed, wait_time = check_rate_limit(client_key, 'refresh')
    if not allowed:
        return jsonify({
            'success': False,
            'message': f'刷新太频繁，请在 {wait_time} 秒后重试',
            'retry_after': wait_time
        }), 429

    force_refresh = request.args.get('force', 'false').lower() == 'true'

    try:
        apps = get_all_apps(force_refresh=force_refresh)
        return jsonify({"success": True, "data": apps})
    except Exception as e:
        print(f"获取应用列表失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@flask_app.route('/api/refresh', methods=['POST'])
def api_refresh():
    client_key = request.remote_addr
    allowed, wait_time = check_rate_limit(client_key, 'refresh')
    if not allowed:
        return jsonify({
            'success': False,
            'message': f'刷新太频繁，请在 {wait_time} 秒后重试',
            'retry_after': wait_time
        }), 429

    try:
        apps = get_all_apps(force_refresh=True)
        return jsonify({'success': True, 'message': f'刷新成功，共 {len(apps)} 个应用', 'data': apps})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@flask_app.route('/api/installed')
def api_installed():
    installed = get_installed_apps_with_versions()
    return jsonify({"success": True, "apps": installed})

@flask_app.route('/api/uninstall', methods=['POST'])
def api_uninstall():
    data = request.get_json()
    app_id = data.get('app_id')
    if not app_id:
        return jsonify({'success': False, 'message': '缺少 app_id'}), 400
    result = uninstall_app(app_id)
    return jsonify(result)

@flask_app.route('/api/app/<app_id>')
def api_app_detail(app_id):
    app = get_app_by_id(app_id)
    if app:
        return jsonify({"success": True, "data": app})
    return jsonify({"success": False, "message": "应用不存在"}), 404

@flask_app.route('/api/logs')
def api_logs():
    logs = get_sanitized_logs()
    return jsonify({"success": True, "data": logs[:500]})

@flask_app.route('/api/logs/export')
def api_logs_export():
    log_file = get_log_file()
    if not os.path.exists(log_file):
        return jsonify({'success': False, 'message': '日志文件不存在'}), 404
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        content_safe = sanitize_log(content)
        return Response(
            content_safe,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename=fnsoft_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@flask_app.route('/api/check-update')
def check_update():
    return jsonify({"success": True, "has_update": False, "version": get_app_version()})

# ===== WebSocket =====
@sock.route('/ws')
def websocket(ws):
    while True:
        data = ws.receive()
        if not data:
            break
        try:
            msg = json.loads(data)
            if msg.get('event') == 'install':
                app_id = msg['data'].get('app_id')
                download_url = msg['data'].get('download_url')
                threading.Thread(target=install_app_with_progress, args=(app_id, download_url, ws), daemon=True).start()
        except:
            pass

# ================================================================
# ========== 启动 ==========
# ================================================================

if __name__ == '__main__':
    print(f"✅ FN软仓 v{get_app_version()} 启动在端口 {PORT}")
    print(f"📡 多源模式：从所有启用的软件源拉取应用")
    print(f"📂 数据目录: {DATA_DIR}")

    sources = load_sources()
    enabled = [s for s in sources if s.get('enabled', True)]
    print(f"📡 已启用 {len(enabled)} 个软件源:")
    for s in enabled:
        print(f"   ● {s.get('name')}: {s.get('url')}")

    flask_app.run(host='0.0.0.0', port=PORT, debug=False)
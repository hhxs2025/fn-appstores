#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# FN软仓应用上架助手 v1.4
# 支持多组配置管理，一键切换

import os
import sys
import json
import shutil
import subprocess
import tarfile
import requests
from datetime import datetime
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# ============================================================
# 核心业务逻辑（与GUI无关，保持不变）
# ============================================================

class FPKPublisher:
    @staticmethod
    def parse_fpk(fpk_path):
        with tarfile.open(fpk_path, 'r:gz') as tar:
            manifest = None
            for member in tar.getmembers():
                if member.name.endswith('/manifest') or member.name == 'manifest':
                    f = tar.extractfile(member)
                    manifest = f.read().decode('utf-8', errors='ignore')
                    f.close()
                    break
            if not manifest:
                raise Exception("未找到 manifest 文件")
            info = {}
            for line in manifest.split('\n'):
                line = line.strip()
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    info[key.strip()] = val.strip()
                elif ':' in line:
                    key, val = line.split(':', 1)
                    info[key.strip()] = val.strip()
            return {
                'id': info.get('appname', ''),
                'name': info.get('display_name', info.get('appname', '')),
                'version': info.get('version', ''),
                'desc': info.get('desc', ''),
                'author': info.get('maintainer', info.get('distributor', '')),
                'repo': info.get('maintainer_url', info.get('distributor_url', ''))
            }

    @staticmethod
    def extract_icon(fpk_path, app_id, target_dir):
        with tarfile.open(fpk_path, 'r:gz') as tar:
            for member in tar.getmembers():
                basename = os.path.basename(member.name)
                if basename.upper() in ['ICON.PNG', 'ICON_256.PNG']:
                    f = tar.extractfile(member)
                    if f:
                        icon_path = os.path.join(target_dir, f"{app_id}.PNG")
                        os.makedirs(os.path.dirname(icon_path), exist_ok=True)
                        with open(icon_path, 'wb') as out:
                            out.write(f.read())
                        f.close()
                        return True
        return False

    @staticmethod
    def is_release_app(app_id, gitee_repo):
        icon_re_path = os.path.join(gitee_repo, 'server-data', 'icons-re', f"{app_id}.PNG")
        return os.path.exists(icon_re_path)

    @staticmethod
    def git_push(gitee_repo, app_id, version, log_callback=None):
        if log_callback:
            log_callback("  推送至 Gitee ...")
        subprocess.run(['git', '-C', gitee_repo, 'add', 'server-data/apps/', 'server-data/icons/'],
                       capture_output=True, text=True)
        msg = f"更新 {app_id} v{version} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(['git', '-C', gitee_repo, 'commit', '-m', msg], capture_output=True, text=True)
        result = subprocess.run(['git', '-C', gitee_repo, 'push'], capture_output=True, text=True)
        if result.returncode == 0:
            if log_callback:
                log_callback("  推送成功")
            return True
        else:
            if log_callback:
                log_callback(f"  推送失败: {result.stderr}")
            return False

    @staticmethod
    def update_json(fn_data_dir, info, download_url, log_callback=None):
        json_path = os.path.join(fn_data_dir, 'fn-appstores.json')
        if not os.path.exists(json_path):
            raise Exception(f"JSON 不存在: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            apps = json.load(f)
        found = False
        for app in apps:
            if app.get('id') == info['id']:
                found = True
                app.update(info)
                if download_url:
                    app['download_url'] = download_url
                elif 'download_url' in app:
                    del app['download_url']
                if log_callback:
                    log_callback(f"  更新: {info['name']}")
                break
        if not found:
            if download_url:
                info['download_url'] = download_url
            apps.append(info)
            if log_callback:
                log_callback(f"  新增: {info['name']}")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(apps, f, ensure_ascii=False, indent=2)
        if log_callback:
            log_callback(f"  JSON 已更新 (共 {len(apps)} 个应用)")
        return len(apps)

    @staticmethod
    def refresh_cache(server_url, log_callback=None):
        try:
            resp = requests.post(f"{server_url}/api/refresh", timeout=10)
            if resp.status_code == 200:
                if log_callback:
                    log_callback("  缓存已刷新")
                return True
            else:
                if log_callback:
                    log_callback(f"  刷新失败: HTTP {resp.status_code}")
                return False
        except Exception as e:
            if log_callback:
                log_callback(f"  刷新失败: {e}")
            return False


# ============================================================
# 批量处理工作线程
# ============================================================

class BatchPublishWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal(bool, str)

    def __init__(self, fpk_paths, config):
        super().__init__()
        self.fpk_paths = fpk_paths
        self.config = config

    def log(self, msg):
        self.log_signal.emit(msg)

    def run(self):
        success_count = 0
        fail_count = 0
        errors = []
        total = len(self.fpk_paths)
        has_gitee = bool(self.config.get('gitee_repo') and self.config.get('gitee_base'))
        has_fnos = bool(self.config.get('fn_data_dir') and self.config.get('server_url'))

        if not has_fnos:
            self.log("错误: 飞牛配置不完整，无法继续")
            self.finished_signal.emit(False, "飞牛配置不完整")
            return

        if not has_gitee:
            mode = 'fnos_only'
            self.log("模式: 仅飞牛本地 (未配置 Gitee)")
        else:
            threshold = int(self.config.get('local_threshold', 10))
            if threshold <= 0:
                mode = 'fnos_only'
                self.log("模式: 仅飞牛本地 (阈值<=0)")
            else:
                mode = 'auto'
                self.log(f"模式: 自动分流 (阈值: {threshold} MB)")

        if not os.path.exists(self.config['fn_data_dir']):
            self.log(f"错误: 飞牛 data 目录不存在: {self.config['fn_data_dir']}")
            self.finished_signal.emit(False, "飞牛 data 目录不存在")
            return

        for i, fpk_path in enumerate(self.fpk_paths):
            self.log("")
            self.log(f"[{i+1}/{total}] 处理: {os.path.basename(fpk_path)}")
            self.log("-" * 40)

            try:
                info = FPKPublisher.parse_fpk(fpk_path)
                app_id = info['id']
                version = info['version']
                size_mb = os.path.getsize(fpk_path) / (1024 * 1024)

                if not app_id or not version:
                    self.log(f"  错误: 缺少 id 或 version")
                    fail_count += 1
                    errors.append(f"{os.path.basename(fpk_path)}: 缺少 id/version")
                    self.progress_signal.emit(i + 1, total)
                    continue

                self.log(f"  应用: {info['name']}")
                self.log(f"  版本: {version}")
                self.log(f"  大小: {size_mb:.1f} MB")

                if has_gitee and FPKPublisher.is_release_app(app_id, self.config['gitee_repo']):
                    self.log(f"  警告: 发行版应用，跳过")
                    fail_count += 1
                    errors.append(f"{os.path.basename(fpk_path)}: 发行版应用，请手动处理")
                    self.progress_signal.emit(i + 1, total)
                    continue

                if mode == 'fnos_only':
                    self._publish_local(info, fpk_path)
                else:
                    if size_mb < threshold:
                        self._publish_gitee(info, fpk_path)
                    else:
                        self._publish_local(info, fpk_path)

                success_count += 1

            except Exception as e:
                self.log(f"  错误: {e}")
                fail_count += 1
                errors.append(f"{os.path.basename(fpk_path)}: {e}")

            self.progress_signal.emit(i + 1, total)

        self.log("")
        self.log("刷新服务端缓存 ...")
        FPKPublisher.refresh_cache(self.config['server_url'], self.log)

        self.log("=" * 50)
        self.log(f"批量完成. 成功: {success_count}, 失败: {fail_count}")
        if errors:
            self.log("")
            self.log("失败列表:")
            for err in errors[:10]:
                self.log(f"  - {err}")

        self.finished_signal.emit(fail_count == 0, f"成功: {success_count}, 失败: {fail_count}")

    def _publish_gitee(self, info, fpk_path):
        app_id = info['id']
        version = info['version']
        self.log(f"  目标: Gitee")

        target = os.path.join(self.config['gitee_repo'], 'server-data', 'apps', f"{app_id}-{version}.fpk")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(fpk_path, target)
        self.log("  复制 FPK 到 server-data/apps/")

        icon_dir = os.path.join(self.config['gitee_repo'], 'server-data', 'icons')
        if FPKPublisher.extract_icon(fpk_path, app_id, icon_dir):
            self.log("  提取图标到 server-data/icons/")
        else:
            self.log("  警告: 未找到图标")

        FPKPublisher.git_push(self.config['gitee_repo'], app_id, version, self.log)

        download_url = f"{self.config['gitee_base']}/apps/{app_id}-{version}.fpk"
        self.log(f"  下载地址: {download_url}")
        FPKPublisher.update_json(self.config['fn_data_dir'], info, download_url, self.log)

    def _publish_local(self, info, fpk_path):
        app_id = info['id']
        version = info['version']
        self.log(f"  目标: 飞牛本地")

        target = os.path.join(self.config['fn_data_dir'], 'apps', f"{app_id}-{version}.fpk")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(fpk_path, target)
        self.log("  复制 FPK 到飞牛 data/apps/")

        icon_dir = os.path.join(self.config['fn_data_dir'], 'icons')
        if FPKPublisher.extract_icon(fpk_path, app_id, icon_dir):
            self.log("  提取图标到飞牛 data/icons/")
        else:
            self.log("  警告: 未找到图标")

        self.log("  服务端自动拼接下载地址")
        FPKPublisher.update_json(self.config['fn_data_dir'], info, None, self.log)


# ============================================================
# 配置管理类
# ============================================================

class ConfigManager:
    CONFIG_KEY = "FNSoft/PublishHelper/profiles"

    @staticmethod
    def load_all():
        """加载所有配置方案"""
        settings = QSettings()
        data = settings.value(ConfigManager.CONFIG_KEY)
        if data:
            try:
                return json.loads(data)
            except:
                return {}
        return {}

    @staticmethod
    def save_all(profiles):
        """保存所有配置方案"""
        settings = QSettings()
        settings.setValue(ConfigManager.CONFIG_KEY, json.dumps(profiles, ensure_ascii=False))

    @staticmethod
    def get_profile(name):
        profiles = ConfigManager.load_all()
        return profiles.get(name, {})

    @staticmethod
    def save_profile(name, config):
        profiles = ConfigManager.load_all()
        profiles[name] = config
        ConfigManager.save_all(profiles)

    @staticmethod
    def delete_profile(name):
        profiles = ConfigManager.load_all()
        if name in profiles:
            del profiles[name]
            ConfigManager.save_all(profiles)
            return True
        return False


# ============================================================
# 主窗口
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FN软仓应用上架助手 v1.4--开发者:晦华先生")
        self.setFixedSize(750, 750)
        self.current_profile = ""
        self.init_ui()
        self.load_profile_list()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)

        # ===== 配置管理区域 =====
        mgr_group = QGroupBox("配置管理")
        mgr_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        mgr_layout = QHBoxLayout(mgr_group)

        mgr_layout.addWidget(QLabel("配置方案:"))

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        mgr_layout.addWidget(self.profile_combo)

        self.save_profile_btn = QPushButton("保存方案")
        self.save_profile_btn.clicked.connect(self.save_profile)
        mgr_layout.addWidget(self.save_profile_btn)

        self.delete_profile_btn = QPushButton("删除方案")
        self.delete_profile_btn.clicked.connect(self.delete_profile)
        mgr_layout.addWidget(self.delete_profile_btn)

        mgr_layout.addStretch()

        layout.addWidget(mgr_group)

        # ===== 配置区域 =====
        config_group = QGroupBox("配置 (飞牛必填，Gitee可选)")
        config_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        config_layout = QGridLayout(config_group)

        row = 0
        config_layout.addWidget(QLabel("飞牛 data 本地映射路径:"), row, 0)
        self.fn_data = QLineEdit()
        self.fn_data.setPlaceholderText("\\\\192.168.3.20\\docker\\fn-appstores-server\\data")
        config_layout.addWidget(self.fn_data, row, 1)

        row += 1
        config_layout.addWidget(QLabel("飞牛服务端地址:"), row, 0)
        self.server_url = QLineEdit()
        self.server_url.setPlaceholderText("http://192.168.3.20:5660")
        config_layout.addWidget(self.server_url, row, 1)

        row += 1
        config_layout.addWidget(QLabel("Gitee 仓库本地映射路径 (可选):"), row, 0)
        self.gitee_repo = QLineEdit()
        self.gitee_repo.setPlaceholderText("D:\\应用开发\\gitee\\fn-appstores")
        config_layout.addWidget(self.gitee_repo, row, 1)

        row += 1
        config_layout.addWidget(QLabel("Gitee Raw 地址 (可选):"), row, 0)
        self.gitee_base = QLineEdit()
        self.gitee_base.setPlaceholderText("https://gitee.com/用户名/仓库名/raw/master/server-data")
        config_layout.addWidget(self.gitee_base, row, 1)

        row += 1
        config_layout.addWidget(QLabel("本地阈值 (MB):"), row, 0)
        threshold_layout = QHBoxLayout()
        self.local_threshold = QLineEdit()
        self.local_threshold.setPlaceholderText("10")
        self.local_threshold.setFixedWidth(80)
        threshold_layout.addWidget(self.local_threshold)
        threshold_layout.addWidget(QLabel("(<=0 或未填则全部走飞牛本地)"))
        config_layout.addLayout(threshold_layout, row, 1)

        layout.addWidget(config_group)

        # ===== 文件选择区域 =====
        file_group = QGroupBox("FPK 文件列表 (支持批量)")
        file_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        file_layout = QVBoxLayout(file_group)

        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(80)
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        file_layout.addWidget(self.file_list)

        file_btn_layout = QHBoxLayout()
        file_btn_layout.setSpacing(8)

        add_files_btn = QPushButton("添加文件")
        add_files_btn.clicked.connect(self.add_files)

        add_folder_btn = QPushButton("添加文件夹")
        add_folder_btn.clicked.connect(self.add_folder)

        clear_files_btn = QPushButton("清空列表")
        clear_files_btn.clicked.connect(self.clear_files)

        file_btn_layout.addWidget(add_files_btn)
        file_btn_layout.addWidget(add_folder_btn)
        file_btn_layout.addStretch()
        file_btn_layout.addWidget(clear_files_btn)

        file_layout.addLayout(file_btn_layout)
        layout.addWidget(file_group)

        # ===== 操作按钮 =====
        btn_layout = QHBoxLayout()

        self.publish_btn = QPushButton("开始上架")
        self.publish_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 30px;
                font-size: 14px;
                font-weight: bold;
                background: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background: #388e3c; }
            QPushButton:disabled { background: #bdbdbd; }
        """)
        self.publish_btn.clicked.connect(self.start_publish)

        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.clear_log)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)

        btn_layout.addWidget(self.publish_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.progress_bar)
        btn_layout.addStretch()
        btn_layout.addWidget(clear_log_btn)

        layout.addLayout(btn_layout)

        # ===== 日志区域 =====
        log_group = QGroupBox("运行日志")
        log_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        # ===== 状态栏 =====
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        self.setAcceptDrops(True)

    # ===== 事件 =====

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith('.fpk'):
                existing = [self.file_list.item(i).text() for i in range(self.file_list.count())]
                if file_path not in existing:
                    self.file_list.addItem(file_path)
                event.accept()
            else:
                event.ignore()

    # ===== 配置管理 =====

    def load_profile_list(self):
        """加载所有配置方案到下拉框"""
        self.profile_combo.clear()
        self.profile_combo.addItem("(新建/未命名)")
        profiles = ConfigManager.load_all()
        for name in sorted(profiles.keys()):
            self.profile_combo.addItem(name)

    def on_profile_changed(self, name):
        """切换配置方案"""
        if not name or name == "(新建/未命名)":
            self.clear_config()
            self.current_profile = ""
            self.status_bar.showMessage("新建配置", 2000)
            return

        config = ConfigManager.get_profile(name)
        if config:
            self.fn_data.setText(config.get('fn_data_dir', ''))
            self.server_url.setText(config.get('server_url', ''))
            self.gitee_repo.setText(config.get('gitee_repo', ''))
            self.gitee_base.setText(config.get('gitee_base', ''))
            self.local_threshold.setText(str(config.get('local_threshold', 10)))
            self.current_profile = name
            self.status_bar.showMessage(f"已加载配置: {name}", 2000)

    def save_profile(self):
        """保存当前配置为方案"""
        config = self.get_config()

        if not config['fn_data_dir'] or not config['server_url']:
            QMessageBox.warning(self, "提示", "请至少填写飞牛 data 目录和服务端地址")
            return

        name, ok = QInputDialog.getText(self, "保存配置方案", "请输入方案名称:")
        if not ok or not name.strip():
            return

        name = name.strip()
        ConfigManager.save_profile(name, config)
        self.load_profile_list()

        # 选中刚保存的方案
        idx = self.profile_combo.findText(name)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

        self.status_bar.showMessage(f"配置已保存: {name}", 3000)

    def delete_profile(self):
        """删除当前配置方案"""
        name = self.profile_combo.currentText()
        if not name or name == "(新建/未命名)":
            QMessageBox.information(self, "提示", "请先选择一个配置方案")
            return

        reply = QMessageBox.question(self, "确认删除", f"确定要删除配置方案 '{name}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No:
            return

        ConfigManager.delete_profile(name)
        self.load_profile_list()
        self.profile_combo.setCurrentIndex(0)
        self.clear_config()
        self.current_profile = ""
        self.status_bar.showMessage(f"已删除: {name}", 3000)

    def clear_config(self):
        """清空配置输入框"""
        self.fn_data.clear()
        self.server_url.clear()
        self.gitee_repo.clear()
        self.gitee_base.clear()
        self.local_threshold.setText("10")

    def get_config(self):
        """获取当前配置"""
        return {
            'fn_data_dir': self.fn_data.text().strip(),
            'server_url': self.server_url.text().strip(),
            'gitee_repo': self.gitee_repo.text().strip(),
            'gitee_base': self.gitee_base.text().strip(),
            'local_threshold': int(self.local_threshold.text().strip()) if self.local_threshold.text().strip() else 10
        }

    # ===== 文件管理 =====

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择 FPK 文件", "", "FPK 文件 (*.fpk)")
        existing = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        for f in files:
            if f not in existing:
                self.file_list.addItem(f)
                existing.append(f)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择包含 FPK 的文件夹")
        if folder:
            existing = [self.file_list.item(i).text() for i in range(self.file_list.count())]
            for root, dirs, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith('.fpk'):
                        path = os.path.join(root, f)
                        if path not in existing:
                            self.file_list.addItem(path)
                            existing.append(path)

    def clear_files(self):
        self.file_list.clear()

    def clear_log(self):
        self.log_text.clear()

    def log(self, msg):
        self.log_text.append(msg)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    # ===== 上架 =====

    def start_publish(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "提示", "请添加 FPK 文件")
            return

        config = self.get_config()

        if not config['fn_data_dir']:
            QMessageBox.warning(self, "提示", "请填写飞牛 data 本地映射路径")
            return
        if not config['server_url']:
            QMessageBox.warning(self, "提示", "请填写飞牛服务端地址")
            return

        if not os.path.exists(config['fn_data_dir']):
            QMessageBox.warning(self, "提示", f"飞牛 data 目录不存在:\n{config['fn_data_dir']}")
            return

        if config['gitee_repo'] and not os.path.exists(config['gitee_repo']):
            reply = QMessageBox.question(self, "警告", f"Gitee 仓库不存在:\n{config['gitee_repo']}\n\n是否继续(仅飞牛模式)？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
            else:
                config['gitee_repo'] = ""
                config['gitee_base'] = ""

        self.publish_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("处理中 ...")

        fpk_paths = [self.file_list.item(i).text() for i in range(self.file_list.count())]

        self.worker = BatchPublishWorker(fpk_paths, config)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"处理中: {current}/{total}")

    def on_finished(self, success, message):
        self.publish_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"完成: {message}", 5000)


# ============================================================
# 启动
# ============================================================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("FN软仓应用上架助手")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
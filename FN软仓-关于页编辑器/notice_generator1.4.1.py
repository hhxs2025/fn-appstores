"""
FN软仓-关于页编辑器 v1.4.1
notice.json 图形化生成器
支持系统托盘，自动保存/加载编辑状态
预览仅显示公告内容
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
from datetime import datetime
import os
import sys
import threading

# 尝试导入系统托盘相关库
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    print("警告: pystray 或 PIL 未安装，系统托盘功能不可用")

# 获取资源路径（兼容 PyInstaller 打包）
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class NoticeGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("FN软仓-关于页编辑器 v1.4.1")
        self.root.geometry("950x800")
        self.root.resizable(True, True)
        self.root.minsize(800, 650)

        try:
            icon_path = resource_path("app.ico")
            self.root.iconbitmap(icon_path)
        except:
            pass

        self.tray_icon = None
        self.tray_thread = None
        self.running = True

        self.carousel_images = []
        self.base_url = "http://rc.hhxs2026.top:5660"

        self.settings_file = os.path.join(os.path.dirname(sys.executable), "settings.json")
        if not getattr(sys, 'frozen', False):
            self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

        self.setup_ui()
        self.load_defaults()
        self.load_settings()
        self.setup_tray()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top_frame, text="✅启用", variable=self.enabled_var).pack(side=tk.LEFT)

        ttk.Label(top_frame, text="更新时间：").pack(side=tk.RIGHT, padx=(0, 5))
        self.update_time_label = ttk.Label(top_frame, text=datetime.now().strftime("%Y-%m-%d"))
        self.update_time_label.pack(side=tk.RIGHT)

        # ===== 轮播图管理 =====
        carousel_frame = ttk.LabelFrame(main_frame, text="🖼️轮播图地址", padding="10")
        carousel_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(carousel_frame, text=f"官方基础地址：{self.base_url}", font=("", 9), foreground="blue").pack(anchor=tk.W)
        ttk.Label(carousel_frame, text="输入后半段路径（如 /previews/fnrc/D.PNG），点击「拼接添加」自动补全", font=("", 9), foreground="gray").pack(anchor=tk.W)

        list_frame = ttk.Frame(carousel_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.carousel_listbox = tk.Listbox(list_frame, height=4, yscrollcommand=scrollbar.set)
        self.carousel_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.carousel_listbox.yview)
        self.carousel_listbox.bind("<Double-Button-1>", self.edit_carousel_item)

        input_row = ttk.Frame(carousel_frame)
        input_row.pack(fill=tk.X, pady=(5, 0))

        self.carousel_entry = ttk.Entry(input_row)
        self.carousel_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(input_row, text="拼接添加", command=self.add_carousel_with_prefix, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(input_row, text="直接添加", command=self.add_carousel_image, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(input_row, text="删除选中", command=self.remove_carousel_image, width=10).pack(side=tk.LEFT)

        # ===== 公告内容 =====
        desc_frame = ttk.LabelFrame(main_frame, text="📝公告内容", padding="10")
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        info_row = ttk.Frame(desc_frame)
        info_row.pack(fill=tk.X)
        ttk.Label(info_row, text="支持 <br> 换行，可直接写 HTML 标签", font=("", 9), foreground="gray").pack(side=tk.LEFT)
        self.word_count_label = ttk.Label(info_row, text="字数：0", font=("", 9), foreground="gray")
        self.word_count_label.pack(side=tk.RIGHT)

        self.desc_text = scrolledtext.ScrolledText(desc_frame, height=10, wrap=tk.WORD, font=("", 11))
        self.desc_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.desc_text.bind("<KeyRelease>", self.update_word_count)

        # ===== 操作按钮 =====
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(action_frame, text="👁️预览", command=self.preview_notice, width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="📋生成JSON", command=self.generate_json, width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="🗑️清空", command=self.clear_form, width=12).pack(side=tk.LEFT)

        # ===== 预览区域（只显示公告内容） =====
        preview_frame = ttk.LabelFrame(main_frame, text="📺预览效果", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_text = tk.Text(
            preview_frame,
            wrap=tk.WORD,
            font=("", 11),
            bg='#fafafa',
            height=12
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        self.preview_text.config(state=tk.DISABLED)

        # ===== 状态栏 =====
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))

    # ---------- 加载/保存 ----------
    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'carousel' in data and isinstance(data['carousel'], list):
                self.carousel_images = data['carousel']
                self.refresh_carousel_listbox()
            if 'enabled' in data:
                self.enabled_var.set(data['enabled'])
            if 'desc' in data:
                self.desc_text.delete(1.0, tk.END)
                self.desc_text.insert(1.0, data['desc'])
                self.update_word_count()
            self.status_var.set("✅ 已加载上次编辑的内容")
        except Exception as e:
            print(f"加载设置失败: {e}")

    def save_settings(self):
        try:
            data = {
                'carousel': self.carousel_images,
                'enabled': self.enabled_var.get(),
                'desc': self.desc_text.get(1.0, tk.END).strip()
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存设置失败: {e}")

    # ---------- 轮播图操作 ----------
    def add_carousel_with_prefix(self):
        suffix = self.carousel_entry.get().strip()
        if not suffix:
            messagebox.showwarning("提示", "请输入图片路径")
            return
        if not suffix.startswith("/"):
            suffix = "/" + suffix
        full_url = self.base_url + suffix
        self.carousel_images.append(full_url)
        self.refresh_carousel_listbox()
        self.carousel_entry.delete(0, tk.END)
        self.status_var.set(f"✅ 已添加：{full_url}")
        self.save_settings()

    def edit_carousel_item(self, event):
        selection = self.carousel_listbox.curselection()
        if selection:
            index = selection[0]
            old_url = self.carousel_images[index]
            edit_window = tk.Toplevel(self.root)
            edit_window.title("修改轮播图地址")
            edit_window.geometry("500x120")
            edit_window.resizable(False, False)
            ttk.Label(edit_window, text=f"当前基础地址：{self.base_url}", font=("", 9), foreground="blue").pack(pady=(10, 0))
            ttk.Label(edit_window, text="修改完整 URL 或只输入后半段路径：").pack(pady=(5, 0))
            entry = ttk.Entry(edit_window, width=60)
            entry.pack(padx=10, pady=5)
            entry.insert(0, old_url)
            entry.select_range(0, tk.END)
            entry.focus()
            def save_edit():
                new_input = entry.get().strip()
                if not new_input:
                    messagebox.showwarning("提示", "URL 不能为空")
                    return
                if not new_input.startswith("http"):
                    if not new_input.startswith("/"):
                        new_input = "/" + new_input
                    new_url = self.base_url + new_input
                else:
                    new_url = new_input
                self.carousel_images[index] = new_url
                self.refresh_carousel_listbox()
                self.status_var.set(f"✅ 已修改：{new_url}")
                self.save_settings()
                edit_window.destroy()
            ttk.Button(edit_window, text="保存", command=save_edit).pack(pady=5)
            edit_window.bind("<Return>", lambda e: save_edit())

    def add_carousel_image(self):
        url = self.carousel_entry.get().strip()
        if url:
            self.carousel_images.append(url)
            self.refresh_carousel_listbox()
            self.carousel_entry.delete(0, tk.END)
            self.status_var.set(f"✅ 已添加图片：{url}")
            self.save_settings()
        else:
            messagebox.showwarning("提示", "请输入图片地址")

    def remove_carousel_image(self):
        selection = self.carousel_listbox.curselection()
        if selection:
            index = selection[0]
            removed = self.carousel_images.pop(index)
            self.refresh_carousel_listbox()
            self.status_var.set(f"🗑️ 已删除：{removed}")
            self.save_settings()

    def refresh_carousel_listbox(self):
        self.carousel_listbox.delete(0, tk.END)
        for url in self.carousel_images:
            self.carousel_listbox.insert(tk.END, url)

    def update_word_count(self, event=None):
        content = self.desc_text.get(1.0, tk.END).strip()
        self.word_count_label.config(text=f"字数：{len(content)}")

    def load_defaults(self):
        self.carousel_images = [
            f"{self.base_url}/previews/fnrc/A.PNG",
            f"{self.base_url}/previews/fnrc/B.PNG",
            f"{self.base_url}/previews/fnrc/C.PNG"
        ]
        self.refresh_carousel_listbox()
        default_desc = """📢 FN软仓 2.4.0
树状多源聚合-全新升级
✦ 服务端 2.4.0
✦ 客户端 2.3.2

★当前聚合内置源：
FN软仓官方内置源
frankluise 的源

Q群:2154077576"""
        self.desc_text.delete(1.0, tk.END)
        self.desc_text.insert(1.0, default_desc)
        self.update_word_count()

    # ============================================================
    # 生成 JSON（不含 interval）
    # ============================================================
    def get_data(self):
        desc_content = self.desc_text.get(1.0, tk.END).strip()
        desc_html = desc_content.replace("\n", "<br>")
        return {
            "enabled": self.enabled_var.get(),
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
            "carousel": self.carousel_images,
            "desc": desc_html
        }

    def generate_json(self):
        data = self.get_data()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)

        result_window = tk.Toplevel(self.root)
        result_window.title("生成的 notice.json")
        result_window.geometry("700x500")

        try:
            result_window.iconbitmap(resource_path("app.ico"))
        except:
            pass

        text_area = scrolledtext.ScrolledText(
            result_window,
            wrap=tk.WORD,
            font=("Courier", 10)
        )
        text_area.pack(fill=tk.BOTH, expand=True)
        text_area.insert(tk.END, json_str)
        text_area.config(state=tk.DISABLED)

        btn_frame = ttk.Frame(result_window)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="📋复制到剪贴板",
                   command=lambda: self.copy_to_clipboard(json_str)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾保存到文件",
                   command=lambda: self.save_json_file(json_str)).pack(side=tk.LEFT, padx=5)

        self.status_var.set("📋 JSON 已生成")

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("✅ 已复制到剪贴板")

    def save_json_file(self, json_str):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json")],
            initialfile="notice.json"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            self.status_var.set(f"💾 已保存到：{file_path}")
            messagebox.showinfo("成功", f"已保存到：{file_path}")

    # ============================================================
    # 预览（仅公告内容）
    # ============================================================
    def preview_notice(self):
        data = self.get_data()
        display_text = data['desc'].replace("<br>", "\n")

        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, display_text)
        self.preview_text.config(state=tk.DISABLED)

        self.status_var.set("👁️ 预览已更新")

    # ---------- 清空 ----------
    def clear_form(self):
        if messagebox.askyesno("确认清空", "确定要清空所有内容吗？"):
            self.carousel_images = []
            self.refresh_carousel_listbox()
            self.desc_text.delete(1.0, tk.END)
            self.enabled_var.set(True)
            self.status_var.set("🗑️ 已清空")
            self.save_settings()

    # ---------- 系统托盘 ----------
    def setup_tray(self):
        if not HAS_TRAY:
            return
        try:
            icon_path = resource_path("app.ico")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
            else:
                image = self.create_tray_icon()
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self.show_window),
                pystray.MenuItem("退出", self.quit_app)
            )
            self.tray_icon = pystray.Icon("FN软仓-关于页编辑器", image, "FN软仓-关于页编辑器", menu)
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
        except Exception as e:
            print(f"系统托盘初始化失败: {e}")

    def create_tray_icon(self):
        size = 64
        image = Image.new('RGB', (size, size), color='#2196F3')
        draw = ImageDraw.Draw(image)
        draw.rectangle([10, 10, 54, 40], fill='white', outline='white')
        draw.line([10, 30, 54, 30], fill='#2196F3', width=2)
        draw.line([10, 20, 54, 20], fill='#2196F3', width=2)
        draw.rectangle([20, 45, 44, 55], fill='white', outline='white')
        return image

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_closing(self):
        self.save_settings()
        if self.tray_icon:
            self.root.withdraw()
            self.status_var.set("程序已最小化到系统托盘")
        else:
            self.quit_app()

    def quit_app(self):
        self.save_settings()
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()
        os._exit(0)


def main():
    root = tk.Tk()
    app = NoticeGenerator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
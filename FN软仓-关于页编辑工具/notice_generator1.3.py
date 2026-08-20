"""
FN软仓-关于页编辑器 v1.3
notice.json 图形化生成器
支持设置轮播图切换间隔（秒）
支持系统托盘
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
    print("请运行: pip install pystray pillow")

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
        self.root.title("FN软仓-关于页编辑器 v1.3")
        self.root.geometry("950x800")
        self.root.resizable(True, True)
        self.root.minsize(800, 650)

        # 设置窗口图标
        try:
            icon_path = resource_path("app.ico")
            self.root.iconbitmap(icon_path)
        except:
            pass

        # 系统托盘相关
        self.tray_icon = None
        self.tray_thread = None
        self.running = True

        self.carousel_images = []
        self.interval_var = tk.IntVar(value=5)
        
        # 官方基础 URL（固定）
        self.base_url = "http://rc.hhxs2026.top:5660"

        self.setup_ui()
        self.load_defaults()
        self.setup_tray()

        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部：启用 + 更新时间
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

        # 提示当前使用的官方地址
        ttk.Label(carousel_frame, text=f"官方基础地址：{self.base_url}", font=("", 9), foreground="blue").pack(anchor=tk.W)
        ttk.Label(carousel_frame, text="输入后半段路径（如 /previews/fnrc/D.PNG），点击「拼接添加」自动补全", font=("", 9), foreground="gray").pack(anchor=tk.W)

        list_frame = ttk.Frame(carousel_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.carousel_listbox = tk.Listbox(list_frame, height=4, yscrollcommand=scrollbar.set)
        self.carousel_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.carousel_listbox.yview)
        
        # 双击修改
        self.carousel_listbox.bind("<Double-Button-1>", self.edit_carousel_item)

        input_row = ttk.Frame(carousel_frame)
        input_row.pack(fill=tk.X, pady=(5, 0))

        self.carousel_entry = ttk.Entry(input_row)
        self.carousel_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(input_row, text="拼接添加", command=self.add_carousel_with_prefix, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(input_row, text="直接添加", command=self.add_carousel_image, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(input_row, text="删除选中", command=self.remove_carousel_image, width=10).pack(side=tk.LEFT)

        # ===== 间隔时间设置 =====
        interval_frame = ttk.Frame(main_frame)
        interval_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(interval_frame, text="⏱️轮播切换间隔（秒）：").pack(side=tk.LEFT)
        interval_spinbox = ttk.Spinbox(interval_frame, from_=2, to=15, textvariable=self.interval_var, width=5)
        interval_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(interval_frame, text="（建议 4~8 秒）", font=("", 9), foreground="gray").pack(side=tk.LEFT, padx=(5, 0))

        # ===== 关于页内容  =====
        desc_frame = ttk.LabelFrame(main_frame, text="📝关于页内容", padding="10")
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

        # ===== 预览区域 =====
        preview_frame = ttk.LabelFrame(main_frame, text="预览效果（模拟软仓关于页）", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_container = ttk.Frame(preview_frame)
        self.preview_container.pack(fill=tk.BOTH, expand=True)

        self.preview_label = ttk.Label(self.preview_container, text="点击「预览」查看效果", font=("", 12), foreground="gray")
        self.preview_label.pack(expand=True)

        # ===== 状态栏 =====
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))

    def add_carousel_with_prefix(self):
        """使用官方地址拼接后添加"""
        suffix = self.carousel_entry.get().strip()
        if not suffix:
            messagebox.showwarning("提示", "请输入图片路径")
            return
        
        # 确保路径以 / 开头
        if not suffix.startswith("/"):
            suffix = "/" + suffix
        
        full_url = self.base_url + suffix
        self.carousel_images.append(full_url)
        self.refresh_carousel_listbox()
        self.carousel_entry.delete(0, tk.END)
        self.status_var.set(f"✅ 已添加：{full_url}")

    def edit_carousel_item(self, event):
        """双击修改轮播图地址"""
        selection = self.carousel_listbox.curselection()
        if selection:
            index = selection[0]
            old_url = self.carousel_images[index]
            
            # 弹出修改对话框
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
                
                # 如果输入的不是完整 URL，自动拼接
                if not new_input.startswith("http"):
                    if not new_input.startswith("/"):
                        new_input = "/" + new_input
                    new_url = self.base_url + new_input
                else:
                    new_url = new_input
                
                self.carousel_images[index] = new_url
                self.refresh_carousel_listbox()
                self.status_var.set(f"✅ 已修改：{new_url}")
                edit_window.destroy()
            
            ttk.Button(edit_window, text="保存", command=save_edit).pack(pady=5)
            edit_window.bind("<Return>", lambda e: save_edit())

    def setup_tray(self):
        """设置系统托盘"""
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
        """创建默认托盘图标"""
        size = 64
        image = Image.new('RGB', (size, size), color='#2196F3')
        draw = ImageDraw.Draw(image)
        draw.rectangle([10, 10, 54, 40], fill='white', outline='white')
        draw.line([10, 30, 54, 30], fill='#2196F3', width=2)
        draw.line([10, 20, 54, 20], fill='#2196F3', width=2)
        draw.rectangle([20, 45, 44, 55], fill='white', outline='white')
        return image

    def show_window(self):
        """显示窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_closing(self):
        """窗口关闭时，隐藏到托盘而不是退出"""
        if self.tray_icon:
            self.root.withdraw()
            self.status_var.set("程序已最小化到系统托盘")
        else:
            self.quit_app()

    def quit_app(self):
        """完全退出程序"""
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()
        os._exit(0)

    def update_word_count(self, event=None):
        content = self.desc_text.get(1.0, tk.END).strip()
        self.word_count_label.config(text=f"字数：{len(content)}")

    def load_defaults(self):
        # 默认轮播图使用官方地址
        self.carousel_images = [
            f"{self.base_url}/previews/fnrc/A.PNG",
            f"{self.base_url}/previews/fnrc/B.PNG",
            f"{self.base_url}/previews/fnrc/C.PNG"
        ]
        self.refresh_carousel_listbox()
        self.interval_var.set(5)

        default_desc = """📢FN软仓大升级
树状多源聚合-全新升级
✦ 服务端:
要求版本:2.4.0
✦ 客户端:
要求版本:2.3.2

★当前聚合内置源：
FN软仓官方内置源
frankluise 的源

Q群:2154077576"""
        self.desc_text.delete(1.0, tk.END)
        self.desc_text.insert(1.0, default_desc)
        self.update_word_count()

    def add_carousel_image(self):
        url = self.carousel_entry.get().strip()
        if url:
            self.carousel_images.append(url)
            self.refresh_carousel_listbox()
            self.carousel_entry.delete(0, tk.END)
            self.status_var.set(f"✅ 已添加图片：{url}")
        else:
            messagebox.showwarning("提示", "请输入图片地址")

    def remove_carousel_image(self):
        selection = self.carousel_listbox.curselection()
        if selection:
            index = selection[0]
            removed = self.carousel_images.pop(index)
            self.refresh_carousel_listbox()
            self.status_var.set(f"🗑️已删除：{removed}")

    def refresh_carousel_listbox(self):
        self.carousel_listbox.delete(0, tk.END)
        for url in self.carousel_images:
            self.carousel_listbox.insert(tk.END, url)

    def get_data(self):
        desc_content = self.desc_text.get(1.0, tk.END).strip()
        desc_html = desc_content.replace("\n", "<br>")
        return {
            "enabled": self.enabled_var.get(),
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
            "interval": self.interval_var.get(),
            "carousel": self.carousel_images,
            "desc": desc_html
        }

    def preview_notice(self):
        data = self.get_data()
        preview_text = f"📌 公告状态：{'✅已启用' if data['enabled'] else '❌已禁用'}\n"
        preview_text += f"📅更新时间：{data['updated_at']}\n"
        preview_text += f"⏱️切换间隔：{data['interval']} 秒\n"
        preview_text += f"🖼️轮播图：{len(data['carousel'])} 张\n"
        for i, url in enumerate(data['carousel'], 1):
            preview_text += f"   {i}. {url}\n"
        preview_text += f"\n{'─' * 50}\n"
        preview_text += "📝关于页内容：\n"
        preview_text += data['desc'].replace("<br>", "\n")

        self.preview_label.config(text=preview_text, justify=tk.LEFT, font=("Courier", 10), foreground="black")
        self.status_var.set("👁️预览已更新")

    def generate_json(self):
        data = self.get_data()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)

        result_window = tk.Toplevel(self.root)
        result_window.title("生成的 notice.json")
        result_window.geometry("600x400")

        try:
            result_window.iconbitmap(resource_path("app.ico"))
        except:
            pass

        text_area = scrolledtext.ScrolledText(result_window, wrap=tk.NONE, font=("Courier", 10))
        text_area.pack(fill=tk.BOTH, expand=True)
        text_area.insert(tk.END, json_str)
        text_area.config(state=tk.DISABLED)

        btn_frame = ttk.Frame(result_window)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="📋复制到剪贴板",
                   command=lambda: self.copy_to_clipboard(json_str)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾保存到文件",
                   command=lambda: self.save_json_file(json_str)).pack(side=tk.LEFT, padx=5)

        self.status_var.set("📋JSON 已生成")

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("✅已复制到剪贴板")

    def save_json_file(self, json_str):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json")],
            initialfile="notice.json"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            self.status_var.set(f"💾已保存到：{file_path}")
            messagebox.showinfo("成功", f"已保存到：{file_path}")

    def clear_form(self):
        if messagebox.askyesno("确认清空", "确定要清空所有内容吗？"):
            self.carousel_images = []
            self.refresh_carousel_listbox()
            self.desc_text.delete(1.0, tk.END)
            self.enabled_var.set(True)
            self.interval_var.set(5)
            self.status_var.set("🗑️已清空")


def main():
    root = tk.Tk()
    app = NoticeGenerator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
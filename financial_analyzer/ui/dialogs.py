"""
对话框模块 - Token配置、缓存设置、导出、数据源管理等
"""
import tkinter as tk
from tkinter import messagebox, filedialog, colorchooser
import threading
from datetime import datetime
from pathlib import Path

from ..config import (
    FONT_TITLE, FONT_SUBTITLE, FONT_LABEL, FONT_SMALL, FONT_BUTTON, FONT_ENTRY,
    COLOR_HIGHLIGHT, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, CONFIG_FILE,
    DEFAULT_CACHE_EXPIRY_HOURS, AUTO_SAVE_DIR,
)
from ..logging_config import get_logger
from .theme import Colors, Fonts, Spacing

logger = get_logger(__name__)

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    HAS_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    HAS_BOOTSTRAP = False


def _load_config():
    """加载配置文件"""
    import json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict):
    """保存配置文件"""
    import json
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _save_config_patch(patch: dict):
    """增量保存配置"""
    config = _load_config()
    config.update(patch)
    _save_config(config)


class TokenConfigDialog:
    """Token 配置对话框 - 管理数据源 API Token"""

    def __init__(self, parent, token_manager, data_adapter, on_save=None):
        self.parent = parent
        self.token_manager = token_manager
        self.data_adapter = data_adapter
        self.on_save = on_save

        self.win = tk.Toplevel(parent)
        self.win.title("Token 配置")
        self.win.geometry("700x560")
        self.win.resizable(True, True)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=Colors.BG_PRIMARY)

        self._center_window()
        self._build_ui()

    def _center_window(self):
        self.win.update_idletasks()
        w, h = 700, 560
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - w) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        c = Colors
        f = Fonts

        # 标题
        header = ttk.Frame(self.win)
        header.pack(fill="x", padx=Spacing.XL, pady=(Spacing.XL, Spacing.MD))
        ttk.Label(header, text="🔑 Token 管理", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="配置各数据源的 API Token", style="Muted.TLabel").pack(anchor="w")

        ttk.Separator(self.win).pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        # Tushare Token
        self._build_token_row("Tushare Pro Token", "tushare",
                              "注册 https://tushare.pro 获取")

        # DeepSeek API Key
        self._build_token_row("DeepSeek API Key", "deepseek_api_key",
                              "注册 https://platform.deepseek.com 获取")

        # 状态指示
        status_frame = tk.LabelFrame(self.win, text="数据源状态", bg=Colors.BG_CARD, fg=Colors.ACCENT, font=Fonts.HEADING, bd=1, relief="groove", padx=8, pady=8)
        status_frame.pack(fill="x", padx=Spacing.XL, pady=(Spacing.MD, Spacing.SM))

        for source in ["tushare", "yfinance", "akshare"]:
            row = ttk.Frame(status_frame)
            row.pack(fill="x", pady=2)
            available = self.data_adapter.data_sources.get(source, False)
            status = self.token_manager.token_status.get(source, "未知")
            icon = "🟢" if available else "🔴"
            ttk.Label(row, text=f"{icon} {source.upper()}: {status}", font=f.BODY).pack(side="left")

        # 按钮
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill="x", padx=Spacing.XL, pady=(Spacing.LG, Spacing.XL))

        ttk.Button(btn_frame, text="保存", style="Accent.TButton",
                   command=self._save).pack(side="right", padx=(Spacing.SM, 0))
        ttk.Button(btn_frame, text="取消", command=self.win.destroy).pack(side="right")

    def _build_token_row(self, label, key, hint):
        """构建一行 Token 输入"""
        f = Fonts
        frame = ttk.Frame(self.win)
        frame.pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        ttk.Label(frame, text=label, font=f.BODY_BOLD).pack(anchor="w")

        entry_frame = ttk.Frame(frame)
        entry_frame.pack(fill="x", pady=(Spacing.XS, 0))

        var = tk.StringVar()
        # 预填已有值
        config = _load_config()
        if key in config:
            var.set(config[key])
        elif key == "tushare" and self.token_manager.tokens.get("tushare"):
            var.set(self.token_manager.tokens["tushare"])

        entry = ttk.Entry(entry_frame, textvariable=var, show="•", font=f.INPUT)
        entry.pack(side="left", fill="x", expand=True)

        # 显示/隐藏切换
        show_var = tk.BooleanVar(value=False)
        def toggle():
            entry.config(show="" if show_var.get() else "•")
        ttk.Checkbutton(entry_frame, text="显示", variable=show_var,
                        command=toggle).pack(side="left", padx=(Spacing.SM, 0))

        ttk.Label(frame, text=hint, style="Muted.TLabel").pack(anchor="w")

        if not hasattr(self, '_entries'):
            self._entries = {}
        self._entries[key] = var

    def _save(self):
        """保存 Token 配置"""
        # 敏感 token（tushare）走 keyring 安全存储，不写入明文 config.json
        app_patch = {}
        for key, var in self._entries.items():
            val = var.get().strip()
            if not val:
                continue
            if key == "tushare":
                self.token_manager.set_token("tushare", val)
                self.data_adapter.set_tushare_token(val)
            else:
                app_patch[key] = val

        if app_patch:
            _save_config_patch(app_patch)

        if self.on_save:
            self.on_save()

        messagebox.showinfo("保存成功", "Token 配置已保存", parent=self.win)
        self.win.destroy()


class CacheSettingsDialog:
    """缓存设置对话框"""

    def __init__(self, parent, cache_manager):
        self.parent = parent
        self.cache_manager = cache_manager

        self.win = tk.Toplevel(parent)
        self.win.title("缓存设置")
        self.win.geometry("480x350")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=Colors.BG_PRIMARY)

        self._center_window()
        self._build_ui()

    def _center_window(self):
        self.win.update_idletasks()
        w, h = 480, 350
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - w) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        f = Fonts

        ttk.Label(self.win, text="⚙️ 缓存设置", style="Title.TLabel").pack(
            anchor="w", padx=Spacing.XL, pady=(Spacing.XL, Spacing.MD))
        ttk.Separator(self.win).pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        # 缓存过期时间
        frame = tk.LabelFrame(self.win, text="缓存过期", bg=Colors.BG_CARD, fg=Colors.ACCENT, font=Fonts.HEADING, bd=1, relief="groove", padx=8, pady=8)
        frame.pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Label(row, text="过期时间（小时）:", font=f.BODY).pack(side="left")

        self.hours_var = tk.IntVar(value=DEFAULT_CACHE_EXPIRY_HOURS)
        spin = ttk.Spinbox(row, from_=1, to=168, textvariable=self.hours_var, width=8, font=f.INPUT)
        spin.pack(side="left", padx=Spacing.SM)

        # 缓存大小
        info_frame = tk.LabelFrame(self.win, text="缓存信息", bg=Colors.BG_CARD, fg=Colors.ACCENT, font=Fonts.HEADING, bd=1, relief="groove", padx=8, pady=8)
        info_frame.pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        cache_info = self._get_cache_info()
        ttk.Label(info_frame, text=cache_info, font=f.BODY).pack(anchor="w")

        # 清除缓存
        ttk.Button(info_frame, text="🗑️ 清除所有缓存",
                   command=self._clear_cache).pack(anchor="w", pady=(Spacing.SM, 0))

        # 按钮
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill="x", padx=Spacing.XL, pady=(Spacing.LG, Spacing.XL))

        ttk.Button(btn_frame, text="应用", style="Accent.TButton",
                   command=self._apply).pack(side="right", padx=(Spacing.SM, 0))
        ttk.Button(btn_frame, text="取消", command=self.win.destroy).pack(side="right")

    def _get_cache_info(self):
        """获取缓存统计信息"""
        try:
            cache_dir = self.cache_manager.cache_dir if hasattr(self.cache_manager, 'cache_dir') else None
            if cache_dir and Path(cache_dir).exists():
                files = list(Path(cache_dir).glob("*"))
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                return f"缓存文件: {len(files)} 个\n缓存大小: {total_size / 1024:.1f} KB"
        except Exception:
            pass
        return "缓存信息: 暂无数据"

    def _clear_cache(self):
        """清除缓存"""
        if messagebox.askyesno("确认", "确定要清除所有缓存数据吗？", parent=self.win):
            try:
                self.cache_manager.clear_all()
                messagebox.showinfo("完成", "缓存已清除", parent=self.win)
            except Exception as e:
                messagebox.showerror("错误", f"清除缓存失败: {e}", parent=self.win)

    def _apply(self):
        """应用设置"""
        try:
            hours = self.hours_var.get()
            self.cache_manager.update_expiry(hours)
            _save_config_patch({"cache_expiry_hours": hours})
            messagebox.showinfo("成功", f"缓存过期时间已设为 {hours} 小时", parent=self.win)
            self.win.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"设置失败: {e}", parent=self.win)


class ExportDialog:
    """数据导出对话框"""

    def __init__(self, parent, data: dict, stock_code: str, analysis_result: str = ""):
        self.parent = parent
        self.data = data
        self.stock_code = stock_code
        self.analysis_result = analysis_result

        self.win = tk.Toplevel(parent)
        self.win.title("数据导出")
        self.win.geometry("520x520")
        self.win.resizable(True, True)
        self.win.minsize(450, 400)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=Colors.BG_PRIMARY)

        self._center_window()
        self._build_ui()

    def _center_window(self):
        self.win.update_idletasks()
        w, h = 520, 520
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - w) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        f = Fonts

        ttk.Label(self.win, text="📤 数据导出", style="Title.TLabel").pack(
            anchor="w", padx=Spacing.XL, pady=(Spacing.XL, Spacing.MD))
        ttk.Separator(self.win).pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        # 导出格式
        fmt_frame = tk.LabelFrame(self.win, text="导出格式", bg=Colors.BG_CARD, fg=Colors.ACCENT, font=Fonts.HEADING, bd=1, relief="groove", padx=8, pady=8)
        fmt_frame.pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        self.format_var = tk.StringVar(value="xlsx")
        formats = [("Excel (.xlsx)", "xlsx"), ("CSV (.csv)", "csv"), ("JSON (.json)", "json")]
        for text, val in formats:
            ttk.Radiobutton(fmt_frame, text=text, variable=self.format_var,
                           value=val).pack(anchor="w", pady=2)

        # 包含分析结果
        self.include_analysis = tk.BooleanVar(value=bool(self.analysis_result))
        ttk.Checkbutton(fmt_frame, text="包含分析结果", variable=self.include_analysis).pack(
            anchor="w", pady=(Spacing.SM, 0))

        # 数据类型选择
        type_frame = tk.LabelFrame(self.win, text="数据类型", bg=Colors.BG_CARD, fg=Colors.ACCENT, font=Fonts.HEADING, bd=1, relief="groove", padx=8, pady=8)
        type_frame.pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        self.type_vars = {}
        for dtype in self.data.keys():
            var = tk.BooleanVar(value=True)
            self.type_vars[dtype] = var
            ttk.Checkbutton(type_frame, text=dtype, variable=var).pack(anchor="w", pady=1)

        # 按钮
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill="x", padx=Spacing.XL, pady=(Spacing.LG, Spacing.XL))

        ttk.Button(btn_frame, text="导出", style="Accent.TButton",
                   command=self._export).pack(side="right", padx=(Spacing.SM, 0))
        ttk.Button(btn_frame, text="取消", command=self.win.destroy).pack(side="right")

    def _export(self):
        """执行导出"""
        fmt = self.format_var.get()
        ext = f".{fmt}"

        # 文件保存对话框
        default_name = f"{self.stock_code}_{datetime.now().strftime('%Y%m%d')}{ext}"
        file_path = filedialog.asksaveasfilename(
            parent=self.win,
            title="保存文件",
            initialdir=str(AUTO_SAVE_DIR),
            initialfile=default_name,
            filetypes=[
                ("Excel 文件", "*.xlsx"),
                ("CSV 文件", "*.csv"),
                ("JSON 文件", "*.json"),
            ]
        )

        if not file_path:
            return

        # 过滤选中的数据类型
        selected_data = {
            k: v for k, v in self.data.items()
            if self.type_vars.get(k, tk.BooleanVar(value=True)).get()
        }

        try:
            from ..utils.export import DataExporter
            if fmt == "xlsx":
                DataExporter.save_to_excel(
                    selected_data, file_path,
                    analysis_result=self.analysis_result if self.include_analysis.get() else "",
                    stock_code=self.stock_code
                )
            elif fmt == "json":
                DataExporter.save_to_json(selected_data, file_path)
            else:
                DataExporter.save_to_csv(selected_data, file_path)

            messagebox.showinfo("成功", f"数据已导出到:\n{file_path}", parent=self.win)
            self.win.destroy()
        except Exception as e:
            messagebox.showerror("导出失败", str(e), parent=self.win)


class DataSourceDialog:
    """数据源管理对话框"""

    def __init__(self, parent, data_adapter, on_change=None):
        self.parent = parent
        self.data_adapter = data_adapter
        self.on_change = on_change

        self.win = tk.Toplevel(parent)
        self.win.title("数据源管理")
        self.win.geometry("450x320")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=Colors.BG_PRIMARY)

        self._center_window()
        self._build_ui()

    def _center_window(self):
        self.win.update_idletasks()
        w, h = 450, 320
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - w) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        f = Fonts

        ttk.Label(self.win, text="📡 数据源管理", style="Title.TLabel").pack(
            anchor="w", padx=Spacing.XL, pady=(Spacing.XL, Spacing.MD))
        ttk.Separator(self.win).pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        # 刷新可用数据源
        self.data_adapter.refresh_sources()
        available = self.data_adapter.get_available_sources()

        # 当前数据源
        src_frame = tk.LabelFrame(self.win, text="活动数据源", bg=Colors.BG_CARD, fg=Colors.ACCENT, font=Fonts.HEADING, bd=1, relief="groove", padx=8, pady=8)
        src_frame.pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)

        self.source_var = tk.StringVar(value=self.data_adapter.active_source)
        for src in available:
            status = "✅ 已安装" if self.data_adapter.data_sources.get(src) else "❌ 未安装"
            row = ttk.Frame(src_frame)
            row.pack(fill="x", pady=2)
            ttk.Radiobutton(row, text=f"{src.upper()}", variable=self.source_var,
                           value=src).pack(side="left")
            ttk.Label(row, text=status, style="Muted.TLabel").pack(side="right")

        # 说明
        info_frame = tk.LabelFrame(self.win, text="说明", bg=Colors.BG_CARD, fg=Colors.ACCENT, font=Fonts.HEADING, bd=1, relief="groove", padx=8, pady=8)
        info_frame.pack(fill="x", padx=Spacing.XL, pady=Spacing.SM)
        ttk.Label(info_frame, text="• Tushare: A股数据，需 Token\n"
                                   "• Yahoo Finance: 全球数据，免费\n"
                                   "• Akshare: A股补充数据源",
                  font=f.SMALL, justify="left").pack(anchor="w")

        # 按钮
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill="x", padx=Spacing.XL, pady=(Spacing.LG, Spacing.XL))

        ttk.Button(btn_frame, text="应用", style="Accent.TButton",
                   command=self._apply).pack(side="right", padx=(Spacing.SM, 0))
        ttk.Button(btn_frame, text="取消", command=self.win.destroy).pack(side="right")

    def _apply(self):
        """应用数据源变更"""
        new_source = self.source_var.get()
        if self.data_adapter.set_active_source(new_source):
            _save_config_patch({"default_data_source": new_source})
            if self.on_change:
                self.on_change(new_source)
            messagebox.showinfo("成功", f"数据源已切换为 {new_source.upper()}", parent=self.win)
        else:
            messagebox.showerror("错误", f"无法切换到 {new_source}", parent=self.win)
        self.win.destroy()


class AboutDialog:
    """关于对话框"""

    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("关于")
        self.win.geometry("400x300")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=Colors.BG_PRIMARY)

        self.win.update_idletasks()
        w, h = 400, 300
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")

        c = Colors
        f = Fonts

        ttk.Label(self.win, text="📊 财务分析系统", style="Title.TLabel").pack(
            pady=(Spacing.XL, Spacing.SM))
        ttk.Label(self.win, text="v9.0.0", font=f.SUBTITLE, foreground=c.FG_SECONDARY).pack()

        ttk.Separator(self.win).pack(fill="x", padx=Spacing.XL, pady=Spacing.MD)

        info = (
            "多数据源架构\n"
            "Tushare · Yahoo Finance · Akshare\n\n"
            "DeepSeek AI 智能分析\n"
            "图表可视化 · 报告导出\n\n"
            "© 2024 财务分析系统开发团队"
        )
        ttk.Label(self.win, text=info, font=f.BODY, justify="center",
                  foreground=c.FG_SECONDARY).pack(pady=Spacing.MD)

        ttk.Button(self.win, text="确定", style="Accent.TButton",
                   command=self.win.destroy).pack(pady=(Spacing.MD, Spacing.XL))

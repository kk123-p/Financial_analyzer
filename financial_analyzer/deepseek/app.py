"""
DeepSeek AI 分析模块 - 独立入口
流程：配置 API → 验证 → 选择分析 → 生成报告
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import traceback
from datetime import datetime
from pathlib import Path

import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financial_analyzer.config import (
    FONT_TITLE, FONT_SUBTITLE, FONT_LABEL, FONT_SMALL, FONT_RESULT,
    COLOR_HIGHLIGHT, COLOR_WARNING, COLOR_SUCCESS, COLOR_MUTED, CONFIG_FILE,
)
from financial_analyzer.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    HAS_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    HAS_BOOTSTRAP = False

try:
    from financial_analyzer.deepseek.client import DeepSeekStreamClient
    HAS_DEEPSEEK = True
except ImportError:
    HAS_DEEPSEEK = False


def load_config():
    import json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config_patch(patch: dict):
    import json
    config = load_config()
    config.update(patch)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


class DeepSeekApp:
    """DeepSeek AI 独立应用"""

    def __init__(self):
        # 创建窗口
        if HAS_BOOTSTRAP:
            self.root = ttk.Window(themename="cosmo")
        else:
            self.root = tk.Tk()
        self.root.title("DeepSeek AI 财务智能分析")
        self.root.geometry("960x750")

        # 居中
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"960x750+{(sw-960)//2}+{(sh-750)//2}")

        # 客户端
        self.client = None
        self._api_verified = False

        # 加载配置
        config = load_config()
        self._saved_key = config.get("deepseek_api_key", "")
        self._saved_url = config.get("deepseek_base_url", "https://api.deepseek.com")
        self._saved_model = config.get("deepseek_model", "deepseek-v4-flash")
        if self._saved_model == "deepseek-chat":
            logger.warning("配置使用了已废弃模型 'deepseek-chat'，自动迁移到 'deepseek-v4-flash'")
            self._saved_model = "deepseek-v4-flash"

        # 构建 UI
        self._build_ui()

        # 如果已有 key，自动初始化客户端
        if self._saved_key and HAS_DEEPSEEK:
            self.client = DeepSeekStreamClient()
            self.client.set_api_key(self._saved_key)
            self.client.set_base_url(self._saved_url)
            self.client.set_model(self._saved_model)

    def _build_ui(self):
        """构建界面"""
        # ==================== 顶部标题 ====================
        header = ttk.Frame(self.root, padding="15")
        header.pack(fill=tk.X)

        ttk.Label(header, text="🤖 DeepSeek AI 财务智能分析", font=FONT_TITLE).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="请先完成 API 配置")
        ttk.Label(header, textvariable=self.status_var, font=FONT_SMALL,
                  foreground=COLOR_WARNING).pack(side=tk.RIGHT)

        ttk.Separator(self.root).pack(fill=tk.X)

        # ==================== 第一步：API 配置 ====================
        step1_outer = ttk.LabelFrame(self.root, text="  第一步：API 配置  ")
        step1_outer.pack(fill=tk.X, padx=15, pady=(15, 5))
        step1 = ttk.Frame(step1_outer, padding="15")
        step1.pack(fill=tk.X)

        # API Key
        r1 = ttk.Frame(step1)
        r1.pack(fill=tk.X, pady=3)
        ttk.Label(r1, text="API Key:", width=10, font=FONT_LABEL).pack(side=tk.LEFT)
        self.key_var = tk.StringVar(value=self._mask(self._saved_key))
        self.key_entry = ttk.Entry(r1, textvariable=self.key_var, width=50, show="*")
        self.key_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="显示", variable=self.show_var,
                        command=lambda: self.key_entry.configure(show="" if self.show_var.get() else "*")
                        ).pack(side=tk.LEFT)

        # API 地址
        r2 = ttk.Frame(step1)
        r2.pack(fill=tk.X, pady=3)
        ttk.Label(r2, text="API 地址:", width=10, font=FONT_LABEL).pack(side=tk.LEFT)
        self.url_var = tk.StringVar(value=self._saved_url)
        ttk.Entry(r2, textvariable=self.url_var, width=50).pack(side=tk.LEFT, padx=(5, 10))

        # 模型
        r3 = ttk.Frame(step1)
        r3.pack(fill=tk.X, pady=3)
        ttk.Label(r3, text="模型:", width=10, font=FONT_LABEL).pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=self._saved_model)
        ttk.Combobox(r3, textvariable=self.model_var, width=20, state="readonly",
                     values=["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"]).pack(side=tk.LEFT, padx=(5, 10))

        # 按钮行
        r4 = ttk.Frame(step1)
        r4.pack(fill=tk.X, pady=(8, 0))

        self.verify_btn = ttk.Button(r4, text="🔍 验证连接", command=self._verify, width=15)
        self.verify_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.save_btn = ttk.Button(r4, text="💾 保存配置", command=self._save, width=15)
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.verify_label = ttk.Label(r4, text="未验证", font=FONT_SMALL, foreground="orange")
        self.verify_label.pack(side=tk.LEFT, padx=(10, 0))

        # ==================== 第二步：分析设置 ====================
        step2_outer = ttk.LabelFrame(self.root, text="  第二步：分析设置  ")
        step2_outer.pack(fill=tk.X, padx=15, pady=5)
        step2 = ttk.Frame(step2_outer, padding="15")
        step2.pack(fill=tk.X)

        # 模板
        r5 = ttk.Frame(step2)
        r5.pack(fill=tk.X, pady=3)
        ttk.Label(r5, text="分析模板:", font=FONT_LABEL).pack(side=tk.LEFT)

        templates = ["综合分析", "盈利能力", "偿债风险", "成长潜力", "估值分析", "行业对比", "自定义"]
        self.template_var = tk.StringVar(value="综合分析")
        combo = ttk.Combobox(r5, textvariable=self.template_var, values=templates,
                             width=15, state="readonly")
        combo.pack(side=tk.LEFT, padx=(5, 10))
        combo.bind("<<ComboboxSelected>>", self._on_template)

        # 自定义提示词（默认隐藏）
        self.custom_frame = ttk.Frame(step2)
        ttk.Label(self.custom_frame, text="自定义提示词:", font=FONT_LABEL).pack(anchor=tk.W)
        self.custom_text = tk.Text(self.custom_frame, height=3, wrap=tk.WORD, font=FONT_SMALL)
        self.custom_text.pack(fill=tk.X, pady=2)
        self.custom_text.insert(1.0, "请根据以下财务数据，从专业角度进行详细分析...")

        # 数据来源
        r6 = ttk.Frame(step2)
        r6.pack(fill=tk.X, pady=3)
        ttk.Label(r6, text="数据来源:", font=FONT_LABEL).pack(side=tk.LEFT)
        self.source_var = tk.StringVar(value="输入数据")
        ttk.Radiobutton(r6, text="手动输入", variable=self.source_var,
                        value="输入数据").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(r6, text="从剪贴板读取", variable=self.source_var,
                        value="剪贴板").pack(side=tk.LEFT, padx=5)

        # 数据输入区
        ttk.Label(step2, text="粘贴财务数据或分析结果:", font=FONT_LABEL).pack(anchor=tk.W, pady=(8, 2))
        self.data_text = tk.Text(step2, height=6, wrap=tk.WORD, font=FONT_SMALL)
        self.data_text.pack(fill=tk.X, pady=2)
        self.data_text.insert(1.0, "请在此粘贴股票代码、财务数据或已有分析结果...\n"
                              "示例: 贵州茅台 600519.SH，获取2024年财报数据...")

        # 生成按钮
        r7 = ttk.Frame(step2)
        r7.pack(fill=tk.X, pady=(10, 0))

        self.gen_btn = ttk.Button(r7, text="🚀 生成 AI 分析报告", command=self._generate, width=22)
        self.gen_btn.pack(side=tk.LEFT)
        if HAS_BOOTSTRAP:
            try:
                self.gen_btn.configure(bootstyle=SUCCESS)
            except Exception:
                pass

        self.progress = ttk.Progressbar(r7, mode="indeterminate", length=200)
        self.progress.pack(side=tk.LEFT, padx=(15, 0))

        self.gen_status = ttk.Label(r7, text="", font=FONT_SMALL, foreground=COLOR_MUTED)
        self.gen_status.pack(side=tk.LEFT, padx=(10, 0))

        # ==================== 第三步：报告输出 ====================
        step3_outer = ttk.LabelFrame(self.root, text="  AI 分析报告  ")
        step3_outer.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))
        step3 = ttk.Frame(step3_outer, padding="10")
        step3.pack(fill=tk.BOTH, expand=True)

        self.report_text = tk.Text(step3, wrap=tk.WORD, font=FONT_RESULT,
                                   relief=tk.FLAT, padx=10, pady=10)
        sb = ttk.Scrollbar(step3, command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=sb.set)
        self.report_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.report_text.tag_configure("title", font=FONT_SUBTITLE, foreground=COLOR_HIGHLIGHT)
        self.report_text.tag_configure("ok", foreground=COLOR_SUCCESS)
        self.report_text.tag_configure("err", foreground=COLOR_WARNING)

        # 底部按钮
        btn_bar = ttk.Frame(self.root, padding="5")
        btn_bar.pack(fill=tk.X, padx=15, pady=(0, 10))

        ttk.Button(btn_bar, text="📋 复制报告", command=self._copy, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="💾 保存TXT", command=lambda: self._save_report("txt"), width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="📄 保存PDF", command=lambda: self._save_report("pdf"), width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="📝 保存Word", command=lambda: self._save_report("docx"), width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="❌ 退出", command=self.root.destroy, width=10).pack(side=tk.RIGHT, padx=2)

    # ==================== 功能方法 ====================

    def _mask(self, key):
        if not key:
            return ""
        return key[:4] + "****" + key[-4:] if len(key) > 8 else "****"

    def _on_template(self, event=None):
        if self.template_var.get() == "自定义":
            self.custom_frame.pack(fill=tk.X, pady=5)
        else:
            self.custom_frame.pack_forget()

    def _verify(self):
        """验证 API Key"""
        if not HAS_DEEPSEEK:
            messagebox.showerror("缺少依赖", "需要 requests 库\n\npip install requests")
            return

        key = self.key_var.get().strip()
        if "****" in key:
            key = self._saved_key
        if not key:
            messagebox.showwarning("提示", "请输入 API Key")
            return

        url = self.url_var.get().strip()
        model = self.model_var.get()

        self.client = DeepSeekStreamClient()
        self.client.set_api_key(key)
        self.client.set_base_url(url)
        self.client.set_model(model)

        self.verify_label.configure(text="验证中...", foreground="orange")
        self.verify_btn.configure(state="disabled")

        def do_verify():
            ok, msg = self.client.validate_key()
            self.root.after(0, lambda: self._on_verify_done(ok, msg, key, url, model))

        threading.Thread(target=do_verify, daemon=True).start()

    def _on_verify_done(self, ok, msg, key, url, model):
        self.verify_btn.configure(state="normal")
        if ok:
            self._api_verified = True
            self._saved_key = key
            self.verify_label.configure(text="✓ 验证成功", foreground="green")
            self.status_var.set("API 已就绪，可以开始分析")
            # 自动保存
            save_config_patch({
                "deepseek_api_key": key,
                "deepseek_base_url": url,
                "deepseek_model": model,
            })
        else:
            self._api_verified = False
            self.verify_label.configure(text="✗ 验证失败", foreground="red")
            messagebox.showerror("验证失败", msg)

    def _save(self):
        """保存配置"""
        key = self.key_var.get().strip()
        if "****" not in key and key:
            self._saved_key = key
        save_config_patch({
            "deepseek_api_key": self._saved_key,
            "deepseek_base_url": self.url_var.get().strip(),
            "deepseek_model": self.model_var.get(),
        })
        messagebox.showinfo("成功", "配置已保存")

    def _generate(self):
        """生成报告"""
        if not HAS_DEEPSEEK:
            messagebox.showerror("缺少依赖", "需要 requests 库\n\npip install requests")
            return

        if not self._saved_key:
            messagebox.showwarning("提示", "请先完成 API 配置并验证")
            return

        if self.client is None:
            self.client = DeepSeekStreamClient()
            self.client.set_api_key(self._saved_key)
            self.client.set_base_url(self.url_var.get().strip())
            self.client.set_model(self.model_var.get())

        # 获取数据
        if self.source_var.get() == "剪贴板":
            try:
                data = self.root.clipboard_get()
            except Exception:
                messagebox.showwarning("提示", "剪贴板为空")
                return
        else:
            data = self.data_text.get(1.0, tk.END).strip()
            if not data or "请在此粘贴" in data:
                messagebox.showwarning("提示", "请输入要分析的财务数据")
                return

        template = self.template_var.get()
        custom = None
        if template == "自定义":
            custom = self.custom_text.get(1.0, tk.END).strip()

        # UI 状态
        self.gen_btn.configure(state="disabled")
        self.progress.start(10)
        self.gen_status.configure(text="正在生成...")
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(1.0, "🤖 AI 正在分析中，请稍候...\n\n", "err")

        def do_gen():
            try:
                def on_chunk(text, done):
                    if not done:
                        self.root.after(0, lambda t=text: self._append(t))

                report = self.client.generate_report_stream(
                    data=data, template=template,
                    custom_prompt=custom, callback=on_chunk
                )
                self.root.after(0, lambda: self._on_done(report))
            except Exception as e:
                logger.error(traceback.format_exc())
                self.root.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=do_gen, daemon=True).start()

    def _append(self, text):
        self.report_text.insert(tk.END, text)
        self.report_text.see(tk.END)

    def _on_done(self, report):
        self.progress.stop()
        self.gen_btn.configure(state="normal")
        if report.success:
            self.report_text.delete(1.0, tk.END)
            header = f"# DeepSeek AI 财务分析报告\n\n"
            header += f"**时间:** {report.timestamp}  |  **模型:** {report.model}  |  **Tokens:** {report.tokens_used}\n\n---\n\n"
            self.report_text.insert(1.0, header, "title")
            self.report_text.insert(tk.END, report.content)
            self.gen_status.configure(text=f"完成 (消耗 {report.tokens_used} tokens)")
            self.status_var.set("报告生成完成")
        else:
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(1.0, f"❌ 失败: {report.error}")
            self.gen_status.configure(text="生成失败")
            messagebox.showerror("失败", report.error)

    def _on_error(self, msg):
        self.progress.stop()
        self.gen_btn.configure(state="normal")
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(1.0, f"❌ 异常: {msg}")
        self.gen_status.configure(text="异常")

    def _copy(self):
        content = self.report_text.get(1.0, tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            messagebox.showinfo("成功", "已复制到剪贴板")

    def _save_report(self, fmt):
        content = self.report_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "没有报告内容")
            return

        ext_map = {"txt": ".txt", "pdf": ".pdf", "docx": ".docx"}
        ext = ext_map.get(fmt, ".txt")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        path = filedialog.asksaveasfilename(
            defaultextension=ext, initialfile=f"AI分析报告_{ts}",
            filetypes=[(f"{fmt.upper()}文件", f"*{ext}")],
        )
        if not path:
            return

        try:
            if fmt == "pdf":
                from financial_analyzer.utils.export import DataExporter
                DataExporter.save_analysis_to_pdf(content, path, "", "AI智能分析")
            elif fmt == "docx":
                from financial_analyzer.utils.export import DataExporter
                DataExporter.save_analysis_to_docx(content, path, "", "AI智能分析")
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            messagebox.showinfo("成功", f"已保存到:\n{path}")
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def run(self):
        self.root.mainloop()


def main():
    setup_logging()
    app = DeepSeekApp()
    app.run()


if __name__ == "__main__":
    main()

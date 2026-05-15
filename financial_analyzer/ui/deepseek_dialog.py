"""
DeepSeek AI 分析对话框 - 嵌入主界面的 AI 分析面板
v10.1 改进：
1. 手动触发：用户需主动点击"发送"才触发AI
2. 提示词可见可编辑：自动构建的提示词在预览区显示，用户可编辑
3. 结构化数据可核实：新增"查看财务数据"按钮
4. 报告导出：支持 Markdown 和 HTML 格式导出
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import traceback
import json
from datetime import datetime
from pathlib import Path

from ..config import CONFIG_FILE, AUTO_SAVE_DIR
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

try:
    from ..deepseek.client import DeepSeekStreamClient
    HAS_DEEPSEEK = True
except ImportError:
    HAS_DEEPSEEK = False


def _load_config():
    import json as _json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return _json.load(f)
        except Exception:
            pass
    return {}


class DeepSeekPanel:
    """DeepSeek AI 分析面板 - 可嵌入主窗口"""

    # 预设分析模板
    TEMPLATES = [
        ("📊 综合财务分析", "请对 {stock} 进行全面的财务分析，包括盈利能力、偿债能力、运营效率和成长性分析，给出投资建议。"),
        ("⚠️ 风险评估", "请对 {stock} 进行风险评估，分析财务风险、市场风险和行业风险，给出风险等级。"),
        ("📈 投资建议", "基于 {stock} 的财务数据和市场表现，给出短期和中长期投资建议，包括买入/持有/卖出建议。"),
        ("🔍 行业对比", "请将 {stock} 与同行业公司进行对比分析，评估其竞争优势和劣势。"),
        ("📋 年报解读", "请解读 {stock} 最近年报的核心信息，包括营收变化、利润构成和未来展望。"),
        ("💡 自定义问题", ""),
    ]

    def __init__(self, parent, stock_code_getter=None, data_getter=None):
        """
        Args:
            parent: 父容器
            stock_code_getter: 获取当前股票代码的函数
            data_getter: 获取当前财务数据的函数
        """
        self.parent = parent
        self.stock_code_getter = stock_code_getter
        self.data_getter = data_getter
        self.client = None
        self._streaming = False
        self._stop_event = threading.Event()
        self._cached_context = None   # 缓存结构化上下文
        self._last_response = ""      # 保存最后一次AI响应（用于导出）

        self.frame = ttk.Frame(parent)
        self._build_ui()
        self._init_client()

    # ==================================================================
    # UI 构建
    # ==================================================================
    def _build_ui(self):
        """构建 AI 分析面板 UI"""
        c = Colors
        f = Fonts

        # ---- 顶部工具栏 ----
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, 0))

        ttk.Label(toolbar, text="🤖 DeepSeek AI 分析", style="Subtitle.TLabel").pack(side="left")

        self.status_label = ttk.Label(toolbar, text="", style="Muted.TLabel")
        self.status_label.pack(side="right")

        ttk.Separator(self.frame).pack(fill="x", padx=Spacing.MD, pady=Spacing.SM)

        # ---- 模板按钮区 ----
        template_frame = ttk.Frame(self.frame)
        template_frame.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.SM))

        btn_row = ttk.Frame(template_frame)
        btn_row.pack(fill="x")

        for i, (label, template) in enumerate(self.TEMPLATES):
            btn = ttk.Button(btn_row, text=label, style="Sidebar.TButton",
                           command=lambda t=template: self._apply_template(t))
            btn.pack(side="left", padx=(0, Spacing.XS), pady=2)

        # ---- 用户提问输入区 ----
        question_frame = tk.LabelFrame(self.frame, text="💬 你的问题",
                                       bg=Colors.BG_CARD, fg=Colors.ACCENT, font=Fonts.HEADING,
                                       bd=1, relief="groove", padx=8, pady=8)
        question_frame.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.SM))
        question_inner = ttk.Frame(question_frame)
        question_inner.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        self.input_text = tk.Text(question_inner, height=3, font=Fonts.BODY,
                                  bg=Colors.BG_INPUT, fg=Colors.FG_PRIMARY,
                                  insertbackground=Colors.ACCENT, relief="flat",
                                  wrap="word", undo=True)
        self.input_text.pack(fill="x")

        # ---- 提示词预览区（可见可编辑） ----
        prompt_frame = tk.LabelFrame(self.frame, text="📝 提示词（可编辑，发送前请确认）",
                                     bg=c.BG_CARD, fg=c.ACCENT, font=f.HEADING,
                                     bd=1, relief="groove", padx=8, pady=8)
        prompt_frame.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.SM))
        prompt_inner = ttk.Frame(prompt_frame)
        prompt_inner.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        self.prompt_text = tk.Text(prompt_inner, height=6, font=f.BODY,
                                   bg=c.BG_INPUT, fg=c.FG_PRIMARY,
                                   insertbackground=c.ACCENT, relief="flat",
                                   wrap="word", undo=True)
        self.prompt_text.pack(fill="x", pady=(0, Spacing.XS))

        # 提示词按钮行
        prompt_btns = ttk.Frame(prompt_inner)
        prompt_btns.pack(fill="x")

        ttk.Button(prompt_btns, text="📋 填充模板提示词",
                   command=self._fill_prompt_from_template).pack(side="left", padx=(0, Spacing.SM))
        ttk.Button(prompt_btns, text="📂 查看财务数据",
                   command=self._show_financial_data).pack(side="left", padx=(0, Spacing.SM))
        ttk.Button(prompt_btns, text="🔄 刷新数据",
                   command=self._refresh_context).pack(side="left")

        # ---- 发送控制区 ----
        send_frame = ttk.Frame(self.frame)
        send_frame.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.SM))

        self.send_btn = ttk.Button(send_frame, text="🚀 发送分析", style="Accent.TButton",
                                   command=self._send)
        self.send_btn.pack(side="right")

        self.stop_btn = ttk.Button(send_frame, text="⏹ 停止", command=self._stop_stream)
        self.stop_btn.pack(side="right", padx=(0, Spacing.SM))
        self.stop_btn.state(["disabled"])

        ttk.Button(send_frame, text="🗑️ 清空输出", command=self._clear_output).pack(side="left")
        ttk.Button(send_frame, text="💾 导出报告", command=self._export_report).pack(side="left", padx=(Spacing.SM, 0))

        # ---- 输出区 ----
        output_frame = tk.LabelFrame(self.frame, text="分析结果", bg=c.BG_CARD, fg=c.ACCENT,
                                     font=f.HEADING, bd=1, relief="groove", padx=8, pady=8)
        output_frame.pack(fill="both", expand=True, padx=Spacing.MD, pady=(0, Spacing.MD))
        output_inner = ttk.Frame(output_frame)
        output_inner.pack(fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)

        text_container = ttk.Frame(output_inner)
        text_container.pack(fill="both", expand=True)

        self.output_text = tk.Text(text_container, font=f.RESULT,
                                   bg=c.BG_SECONDARY, fg=c.FG_PRIMARY,
                                   relief="flat", wrap="word", state="disabled",
                                   spacing1=2, spacing3=2)
        scrollbar = ttk.Scrollbar(text_container, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scrollbar.set)

        self.output_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._configure_tags()

    def _configure_tags(self):
        """配置文字样式标签"""
        c = Colors
        self.output_text.tag_configure("heading", font=Fonts.HEADING, foreground=c.ACCENT)
        self.output_text.tag_configure("bold", font=Fonts.BODY_BOLD)
        self.output_text.tag_configure("success", foreground=c.SUCCESS)
        self.output_text.tag_configure("danger", foreground=c.DANGER)
        self.output_text.tag_configure("warning", foreground=c.WARNING)
        self.output_text.tag_configure("info", foreground=c.INFO)
        self.output_text.tag_configure("muted", foreground=c.FG_MUTED)
        self.output_text.tag_configure("timestamp", foreground=c.FG_MUTED, font=Fonts.TINY)

    # ==================================================================
    # 客户端初始化
    # ==================================================================
    def _init_client(self):
        """初始化 DeepSeek 客户端"""
        if not HAS_DEEPSEEK:
            self.status_label.config(text="⚠️ 未安装 DeepSeek 模块")
            self.send_btn.state(["disabled"])
            return

        config = _load_config()
        api_key = config.get("deepseek_api_key", "")
        if not api_key:
            self.status_label.config(text="⚠️ 未配置 API Key (请在设置中配置)")
            self.send_btn.state(["disabled"])
            return

        try:
            from ..deepseek.client import DeepSeekConfig
            ds_config = DeepSeekConfig(
                api_key=api_key,
                base_url=config.get("deepseek_base_url", "https://api.deepseek.com"),
                model=config.get("deepseek_model", "deepseek-chat"),
            )
            self.client = DeepSeekStreamClient(config=ds_config)
            self.status_label.config(text="✅ 已就绪")
        except Exception as e:
            self.status_label.config(text=f"❌ 初始化失败: {e}")
            self.send_btn.state(["disabled"])

    def refresh_client(self):
        """刷新客户端（Token 更新后调用）"""
        self._init_client()

    # ==================================================================
    # 提示词管理
    # ==================================================================
    def _apply_template(self, template: str):
        """应用分析模板到用户输入区（旧接口兼容）"""
        self.input_text.delete("1.0", "end")
        stock_code = self.stock_code_getter() if self.stock_code_getter else ""
        if template and stock_code:
            template = template.replace("{stock}", stock_code)
        self.input_text.insert("1.0", template)
        self.input_text.focus_set()

    def _fill_prompt_from_template(self):
        """将用户输入 + 结构化数据 构建为完整提示词，填入提示词预览区"""
        question = self.input_text.get("1.0", "end").strip() if hasattr(self, 'input_text') else ""
        if not question:
            question = "请对该公司的财务状况进行全面分析。"

        context = self._build_financial_context()
        if context:
            full_prompt = (
                f"你是一位专业的财务分析师。请基于以下结构化财务数据，回答用户的问题。\n\n"
                f"## 输出要求\n"
                f"1. 使用 Markdown 格式，结构清晰\n"
                f"2. 先给出核心结论（1-2句话），再展开详细分析\n"
                f"3. 数据引用要具体（如「毛利率62.5%」而非「毛利率较高」）\n"
                f"4. 每个分析维度用 ## 标题分隔\n"
                f"5. 最后给出明确的投资建议和风险提示\n\n"
                f"## 结构化财务数据\n\n{context}\n\n"
                f"---\n\n## 用户问题\n\n{question}"
            )
        else:
            full_prompt = question

        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", full_prompt)

    def _refresh_context(self):
        """刷新财务数据上下文"""
        self._cached_context = None
        self._build_financial_context()
        messagebox.showinfo("提示", "财务数据上下文已刷新")

    # ==================================================================
    # 查看财务数据
    # ==================================================================
    def _show_financial_data(self):
        """弹窗展示第一阶段结构化财务数据，供用户核实"""
        context = self._build_financial_context()
        if not context:
            messagebox.showinfo("提示", "暂无财务数据。请先获取股票数据。")
            return

        win = tk.Toplevel(self.parent)
        win.title("📂 第一阶段结构化财务数据（将投喂给AI）")
        win.geometry("800x600")

        text = tk.Text(win, wrap="word", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        text.insert("1.0", context)
        text.config(state="disabled")

    # ==================================================================
    # 发送与流式响应
    # ==================================================================
    def _send(self):
        """发送分析请求 — 使用提示词预览区的内容"""
        if self._streaming:
            return

        # 从提示词预览区获取完整prompt
        full_prompt = self.prompt_text.get("1.0", "end").strip()
        if not full_prompt:
            # 如果提示词区为空，自动构建
            self._fill_prompt_from_template()
            full_prompt = self.prompt_text.get("1.0", "end").strip()
        if not full_prompt:
            messagebox.showinfo("提示", "请输入问题或选择模板")
            return

        if not self.client:
            messagebox.showwarning("提示", "DeepSeek 客户端未初始化，请先配置 API Key")
            return

        self._streaming = True
        self.send_btn.state(["disabled"])
        self.stop_btn.state(["!disabled"])
        self.status_label.config(text="⏳ 分析中...")
        self._last_response = ""

        # 在输出区追加用户提问摘要
        question_preview = full_prompt.split("## 用户问题")[-1].strip()[:200] if "## 用户问题" in full_prompt else full_prompt[:200]
        self._append_output(f"\n{'━' * 55}\n", "muted")
        self._append_output(f"  📤 发送时间: {datetime.now().strftime('%H:%M:%S')}\n", "timestamp")
        self._append_output(f"  📝 提问: {question_preview}...\n", "bold")
        self._append_output(f"  📊 提示词: {len(full_prompt)} 字符\n", "muted")
        self._append_output(f"{'━' * 55}\n\n", "muted")
        self._append_output(f"  🤖 DeepSeek 分析结果:\n\n", "heading")

        # 启动流式请求线程
        self._stop_event.clear()
        thread = threading.Thread(target=self._stream_request, args=(full_prompt,), daemon=True)
        thread.start()

    def _stream_request(self, question: str):
        """流式请求线程"""
        try:
            full_response = []
            for chunk in self.client.chat_stream(question):
                if self._stop_event.is_set():
                    break
                full_response.append(chunk)
                self.parent.after(0, self._append_output, chunk, None)

            response_text = "".join(full_response)
            self._last_response = response_text
            self.parent.after(0, self._on_stream_complete, response_text)
        except Exception as e:
            logger.error(f"DeepSeek 请求失败: {e}\n{traceback.format_exc()}")
            self.parent.after(0, self._on_stream_error, str(e))

    def _on_stream_complete(self, full_text: str):
        """流式输出完成"""
        self._streaming = False
        self.send_btn.state(["!disabled"])
        self.stop_btn.state(["disabled"])
        self.status_label.config(text="✅ 分析完成")
        self._append_output("\n\n", None)

    def _on_stream_error(self, error: str):
        """流式输出出错"""
        self._streaming = False
        self.send_btn.state(["!disabled"])
        self.stop_btn.state(["disabled"])
        self.status_label.config(text=f"❌ 错误: {error}")
        self._append_output(f"\n\n❌ 错误: {error}\n", "danger")

    def _stop_stream(self):
        """停止流式输出"""
        self._stop_event.set()
        self.status_label.config(text="⏹ 已停止")

    # ==================================================================
    # 输出区操作
    # ==================================================================
    def _append_output(self, text: str, tag=None):
        """追加文字到输出区"""
        self.output_text.config(state="normal")
        if tag:
            self.output_text.insert("end", text, tag)
        else:
            self.output_text.insert("end", text)
        self.output_text.see("end")
        self.output_text.config(state="disabled")

    def _clear_output(self):
        """清空输出"""
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.config(state="disabled")
        self._last_response = ""

    def get_output_text(self) -> str:
        """获取当前输出文本"""
        return self.output_text.get("1.0", "end").strip()

    # ==================================================================
    # 导出报告
    # ==================================================================
    def _export_report(self):
        """导出分析报告（支持 Markdown 和 HTML）"""
        output = self.get_output_text()
        if not output:
            messagebox.showinfo("提示", "没有可导出的分析结果")
            return

        stock_code = self.stock_code_getter() if self.stock_code_getter else "unknown"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filepath = filedialog.asksaveasfilename(
            title="导出分析报告",
            initialdir=str(AUTO_SAVE_DIR),
            initialfile=f"{stock_code}_AI分析_{timestamp}",
            defaultextension=".md",
            filetypes=[
                ("Markdown", "*.md"),
                ("HTML", "*.html"),
                ("文本", "*.txt"),
            ],
        )
        if not filepath:
            return

        try:
            if filepath.endswith(".html"):
                content = self._to_html(output, stock_code)
            else:
                content = self._to_markdown(output, stock_code)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            messagebox.showinfo("成功", f"报告已导出到:\n{filepath}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")

    def _to_markdown(self, text: str, stock_code: str) -> str:
        """转换为 Markdown 格式"""
        return (
            f"# AI 财务分析报告\n\n"
            f"**股票代码**: {stock_code}\n"
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**模型**: DeepSeek\n\n"
            f"---\n\n"
            f"{text}\n\n"
            f"---\n\n"
            f"*本报告由 AI 自动生成，仅供参考，不构成投资建议。*\n"
        )

    def _to_html(self, text: str, stock_code: str) -> str:
        """转换为 HTML 格式"""
        import re
        # 简单 markdown → HTML 转换
        html_body = text
        # 标题
        html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_body, flags=re.MULTILINE)
        # 粗体
        html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
        # 列表
        html_body = re.sub(r'^- (.+)$', r'<li>\1</li>', html_body, flags=re.MULTILINE)
        # 换行
        html_body = html_body.replace('\n', '<br>\n')

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI 财务分析报告 - {stock_code}</title>
    <style>
        body {{ font-family: "Microsoft YaHei", sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.8; }}
        h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        h3 {{ color: #555; }}
        strong {{ color: #c0392b; }}
        li {{ margin: 5px 0; }}
        .meta {{ color: #888; font-size: 14px; margin-bottom: 30px; }}
        .disclaimer {{ color: #999; font-size: 12px; margin-top: 40px; border-top: 1px solid #ddd; padding-top: 10px; }}
    </style>
</head>
<body>
    <h1>AI 财务分析报告</h1>
    <div class="meta">
        <p><strong>股票代码</strong>: {stock_code}</p>
        <p><strong>生成时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>模型</strong>: DeepSeek</p>
    </div>
    <hr>
    {html_body}
    <div class="disclaimer">
        <p>本报告由 AI 自动生成，仅供参考，不构成投资建议。</p>
    </div>
</body>
</html>"""

    # ==================================================================
    # 股票上下文
    # ==================================================================
    def set_stock_context(self, stock_code: str, stock_name: str = ""):
        """设置股票上下文信息"""
        context = f"当前分析: {stock_name} ({stock_code})" if stock_name else f"当前分析: {stock_code}"
        self._append_output(f"[上下文] {context}\n", "info")
        self._cached_context = None

    # ==================================================================
    # 结构化财务数据构建
    # ==================================================================
    def refresh_context(self):
        """刷新财务数据上下文（数据更新后调用）"""
        self._cached_context = None

    def _build_financial_context(self) -> str:
        """构建第一阶段结构化财务数据上下文"""
        if self._cached_context:
            return self._cached_context

        if not self.data_getter:
            return ""

        try:
            data = self.data_getter()
            if not data:
                return ""

            stock_code = self.stock_code_getter() if self.stock_code_getter else ""

            parts = []

            # 1. 体检报告（ReportBuilder）
            try:
                from ..ai.report_builder import ReportBuilder
                report = ReportBuilder.build(data, stock_code)
                parts.append(f"## 公司体检报告\n{json.dumps(report, ensure_ascii=False, indent=2, default=str)}")
            except Exception:
                pass

            # 2. 财务比率分析
            try:
                from ..analyzers.financial_ratios import FinancialRatioAnalyzer
                ratio = FinancialRatioAnalyzer(data, stock_code)
                ratio_result = ratio.analyze()
                parts.append(f"## 财务比率分析\n{json.dumps(ratio_result, ensure_ascii=False, indent=2, default=str)}")
            except Exception:
                pass

            # 3. 矛盾信号
            try:
                from ..ai.signal_detector import SignalDetector
                from ..ai.report_builder import ReportBuilder as RB2
                report2 = RB2.build(data, stock_code)
                signals = SignalDetector.detect(report2)
                if signals:
                    sig_text = "\n".join([f"- {s['name']}: {s.get('trigger_data', '')}" for s in signals])
                    parts.append(f"## 已检测到的矛盾信号\n{sig_text}")
            except Exception:
                pass

            if parts:
                self._cached_context = "\n\n".join(parts)
                return self._cached_context

        except Exception as e:
            logger.warning(f"构建财务上下文失败: {e}")

        return ""

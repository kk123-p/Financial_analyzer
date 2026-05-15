"""
AI 深度投研面板 - 三方辩论式投研分析 UI
通过 DeepSeek API 实现三个分析师角色的流式辩论
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import threading
from pathlib import Path

from ..ai.report_builder import ReportBuilder
from ..ai.signal_detector import SignalDetector
from ..ai.debate_engine import DebateEngine
from ..ai.report_template import ReportTemplate
from ..deepseek.prompts import (
    _load_config, _save_config, reload_config,
    get_analyst_roles, get_debate_system_prompt,
    DEBATE_ROUND1_PROMPT, DEBATE_ROUND2_PROMPT, DEBATE_ROUND3_PROMPT,
    USER_FOLLOWUP_PROMPT, WEIGHT_ADJUSTMENT_PROMPT,
    ANALYST_ROLES,
)
from ..logging_config import get_logger

logger = get_logger(__name__)


class ResearchPanel:
    """AI 深度投研面板 - 三方辩论"""

    def __init__(self, parent, stock_code_getter=None, data_getter=None, app=None):
        self.parent = parent
        self.stock_code_getter = stock_code_getter
        self.data_getter = data_getter
        self.app = app
        self.config = _load_config()
        self.engine = None
        self._report = None
        self._signals = None
        self._debate_running = False

        self._build_ui()

    def _build_ui(self):
        """构建UI"""
        # ===== 工具栏 =====
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill="x", padx=8, pady=(8, 4))

        self.btn_start = ttk.Button(toolbar, text="▶ 启动辩论", command=self._start_debate)
        self.btn_start.pack(side="left", padx=2)
        self.btn_stop = ttk.Button(toolbar, text="⏹ 停止", command=self._stop_debate, state="disabled")
        self.btn_stop.pack(side="left", padx=2)
        ttk.Button(toolbar, text="🗑 清空", command=self._clear_all).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(toolbar, text="📋 体检报告", command=self._show_health_report).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📄 生成报告", command=self._generate_report).pack(side="left", padx=2)
        ttk.Button(toolbar, text="💾 导出", command=self._export_report).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(toolbar, text="✏️ Prompt编辑", command=self._show_prompt_editor).pack(side="left", padx=2)

        self.status_label = ttk.Label(toolbar, text="就绪", foreground="gray")
        self.status_label.pack(side="right", padx=8)

        # ===== 权重滑块 =====
        weight_frame = ttk.LabelFrame(self.parent, text="📊 分析师权重", padding=6)
        weight_frame.pack(fill="x", padx=8, pady=4)

        self.weight_vars = {}
        roles = get_analyst_roles()
        for key, role in roles.items():
            frame = ttk.Frame(weight_frame)
            frame.pack(side="left", expand=True, padx=10)
            ttk.Label(frame, text=f"{role['emoji']} {role['name']}").pack()
            var = tk.DoubleVar(value=self.config.get("analyst_weights", {}).get(key, 0.33))
            self.weight_vars[key] = var
            scale = ttk.Scale(frame, from_=0.0, to=1.0, variable=var, orient="horizontal", length=120)
            scale.pack()
            lbl = ttk.Label(frame, text=f"{var.get():.0%}")
            lbl.pack()
            var.trace_add("write", lambda *a, l=lbl, v=var: l.config(text=f"{v.get():.0%}"))

        # ===== 追问区（先打包，确保始终可见） =====
        followup_frame = ttk.Frame(self.parent)
        followup_frame.pack(fill="x", padx=8, pady=(0, 4), side="bottom")

        self.followup_entry = ttk.Entry(followup_frame, font=("Microsoft YaHei UI", 10))
        self.followup_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.followup_entry.bind("<Return>", lambda e: self._send_followup())
        ttk.Button(followup_frame, text="💬 追问", command=self._send_followup).pack(side="right")

        # ===== 主内容区域（可分割） =====
        main_pane = ttk.PanedWindow(self.parent, orient="vertical")
        main_pane.pack(fill="both", expand=True, padx=8, pady=4)

        # 上半部分：三个分析师卡片
        cards_frame = ttk.Frame(main_pane)
        main_pane.add(cards_frame, weight=1)

        self.analyst_texts = {}
        roles = get_analyst_roles()
        for i, (key, role) in enumerate(roles.items()):
            lf = ttk.LabelFrame(cards_frame, text=f"{role['emoji']} {role['name']}", padding=4)
            lf.grid(row=0, column=i, padx=4, pady=4, sticky="nsew")
            cards_frame.columnconfigure(i, weight=1)
            cards_frame.rowconfigure(0, weight=1)

            text = tk.Text(lf, wrap="word", font=("Microsoft YaHei UI", 9),
                           bg="#1a1a2e", fg="#e0e0e0", insertbackground="white",
                           selectbackground="#3b82f6", relief="flat", bd=0)
            scrollbar = ttk.Scrollbar(lf, orient="vertical", command=text.yview)
            text.configure(yscrollcommand=scrollbar.set)
            text.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            self.analyst_texts[key] = text

        # 下半部分：辩论综合区
        debate_frame = ttk.LabelFrame(main_pane, text="⚖️ 辩论综合 & 共识地图", padding=4)
        main_pane.add(debate_frame, weight=1)

        self.debate_text = tk.Text(debate_frame, wrap="word", font=("Microsoft YaHei UI", 9),
                                   bg="#0f172a", fg="#e2e8f0", insertbackground="white",
                                   selectbackground="#3b82f6", relief="flat", bd=0)
        ds = ttk.Scrollbar(debate_frame, orient="vertical", command=self.debate_text.yview)
        self.debate_text.configure(yscrollcommand=ds.set)
        self.debate_text.pack(side="left", fill="both", expand=True)
        ds.pack(side="right", fill="y")

    # ========================================================================
    # 辩论流程
    # ========================================================================
    def _start_debate(self):
        """启动三方辩论"""
        stock_code = self.stock_code_getter() if self.stock_code_getter else ""
        if not stock_code:
            messagebox.showwarning("提示", "请先输入股票代码")
            return

        # 获取数据
        data = None
        if self.app and hasattr(self.app, '_current_data'):
            data = self.app._current_data
        elif self.data_getter:
            data = self.data_getter()
        if not data:
            messagebox.showwarning("提示", "请先获取财务数据（点击侧边栏任意分析项加载数据）")
            return

        # 读取API配置
        api_key, base_url, model = self._load_api_config()
        if not api_key:
            messagebox.showwarning("提示", "请先配置 DeepSeek API Key\n（设置 → DeepSeek API Key）")
            return

        # 清空显示
        self._clear_all()

        # 构建体检报告
        self._set_status("正在构建体检报告...")
        self._report = ReportBuilder.build(data, stock_code)
        self._signals = SignalDetector.detect(self._report)

        # 初始化辩论引擎
        self.engine = DebateEngine(api_key=api_key, model=model, base_url=base_url)

        # 收集权重
        weights = {k: v.get() for k, v in self.weight_vars.items()}
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        # UI状态
        self._debate_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")

        # 辩论回调：流式接收AI输出
        def debate_callback(analyst_id, chunk, done):
            """流式回调 - 实时更新UI"""
            if analyst_id == "_meta":
                # 元信息：阶段切换
                self.parent.after(0, lambda: self._handle_meta(chunk, done))
            elif analyst_id == "consensus":
                # 第三轮共识地图 - 写入辩论区
                self.parent.after(0, lambda: self._append_debate(chunk))
                if done:
                    self.parent.after(0, lambda: self._on_debate_complete())
            else:
                # 分析师发言 - 写入对应卡片
                if chunk:
                    self.parent.after(0, lambda: self._append_analyst(analyst_id, chunk))

        def on_complete(state):
            """辩论完成"""
            self.parent.after(0, lambda: self._on_debate_complete())

        # 在后台线程运行
        def run():
            try:
                self.parent.after(0, lambda: self._set_status("Step 1/3: 第一轮独立陈述..."))
                self.engine.prepare(data, stock_code)
                self.engine.start_debate(stock_code, stock_code,
                                         callback=debate_callback,
                                         on_complete=on_complete)
            except Exception as e:
                logger.error(f"辩论启动失败: {e}")
                self.parent.after(0, lambda: self._append_debate(f"\n❌ 启动失败: {e}\n"))
                self.parent.after(0, lambda: self._set_status("启动失败"))
                self.parent.after(0, lambda: self._reset_buttons())

        threading.Thread(target=run, daemon=True).start()

    def _handle_meta(self, meta: str, done: bool):
        """处理元信息回调"""
        if meta == "round1_start":
            self._set_status("第一轮: 独立视角陈述...")
        elif meta == "round2_start":
            self._set_status("第二轮: 交叉质询...")
            self._append_debate("\n" + "="*50 + "\n")
            self._append_debate("第二轮：交叉质询\n")
            self._append_debate("="*50 + "\n\n")
        elif meta == "round3_start":
            self._set_status("第三轮: 共识地图...")
            self._append_debate("\n" + "="*50 + "\n")
            self._append_debate("第三轮：共识地图\n")
            self._append_debate("="*50 + "\n\n")
        elif meta.startswith("analyst_") and meta.endswith("_start"):
            analyst_id = meta.replace("analyst_", "").replace("_start", "")
            roles = get_analyst_roles()
            role = roles.get(analyst_id, {})
            phase = "独立陈述" if "round1" in (self._get_current_phase()) else "交叉质询"
            self._append_analyst(analyst_id, f"\n--- {phase} ---\n\n")
        elif meta.startswith("error:"):
            self._append_debate(f"\n❌ 错误: {meta[6:]}\n")
            self._set_status("出错")

    def _get_current_phase(self):
        if self.engine:
            return self.engine.state.phase
        return ""

    def _on_debate_complete(self):
        """辩论完成"""
        self._debate_running = False
        self._set_status("投研分析完成 ✅")
        self._append_debate("\n\n✅ 深度投研分析完成\n")
        self._reset_buttons()

    def _stop_debate(self):
        """停止辩论"""
        if self.engine:
            self.engine.stop()
        self._debate_running = False
        self._set_status("已停止")
        self._reset_buttons()

    def _reset_buttons(self):
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    # ========================================================================
    # 追问
    # ========================================================================
    def _send_followup(self):
        """发送追问"""
        question = self.followup_entry.get().strip()
        if not question:
            return
        if not self.engine:
            self._append_debate("❌ 请先启动辩论\n")
            return

        self.followup_entry.delete(0, "end")
        self._append_debate(f"\n💬 用户追问: {question}\n\n")

        def followup_cb(analyst_id, chunk, done):
            if analyst_id == "_meta":
                if "error" in str(chunk):
                    self.parent.after(0, lambda: self._append_debate(f"\n❌ {chunk}\n"))
            elif analyst_id == "consensus":
                pass
            else:
                if chunk:
                    self.parent.after(0, lambda: self._append_analyst(analyst_id, chunk))

        self.engine.send_followup(question, callback=followup_cb)

    # ========================================================================
    # 体检报告（查看投喂给AI的结构化数据）
    # ========================================================================
    def _show_health_report(self):
        """显示体检报告 - 确认投喂给AI的真实数据"""
        if not self._report:
            # 如果还没运行过辩论，先构建报告
            data = None
            if self.app and hasattr(self.app, '_current_data'):
                data = self.app._current_data
            if not data:
                messagebox.showinfo("提示", "请先获取财务数据")
                return
            stock_code = self.stock_code_getter() if self.stock_code_getter else ""
            self._report = ReportBuilder.build(data, stock_code)
            self._signals = SignalDetector.detect(self._report)

        win = tk.Toplevel(self.parent)
        win.title("📋 体检报告 - 投喂给AI的结构化数据")
        win.geometry("700x600")

        text = tk.Text(win, wrap="word", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 格式化显示
        report_json = json.dumps(self._report, ensure_ascii=False, indent=2, default=str)
        text.insert("1.0", report_json)

        # 显示矛盾信号
        if self._signals:
            text.insert("end", "\n\n" + "="*50 + "\n")
            text.insert("end", "⚠️ 检测到的矛盾信号:\n")
            text.insert("end", "="*50 + "\n\n")
            for sig in self._signals:
                text.insert("end", f"🚨 {sig['name']}\n")
                text.insert("end", f"   {sig.get('trigger_data', '')}\n")
                text.insert("end", f"   AI诊断任务: {sig.get('task', '')}\n\n")

        text.config(state="disabled")

    # ========================================================================
    # 生成报告 / 导出
    # ========================================================================
    def _generate_report(self):
        """生成HTML报告"""
        if not self.engine or not self.engine.state.round1_statements:
            messagebox.showinfo("提示", "请先完成辩论")
            return

        html = ReportTemplate.build_html_report(
            self.engine.state, self._report or {},
            self._signals or [], "")

        # 在新窗口中显示
        win = tk.Toplevel(self.parent)
        win.title("📄 深度投研报告")
        win.geometry("800x600")
        text = tk.Text(win, wrap="word", font=("Consolas", 9))
        text.pack(fill="both", expand=True)
        text.insert("1.0", html)
        self._append_debate("\n📄 报告已生成\n")

    def _export_report(self):
        """导出报告"""
        if not self.engine or not self.engine.state.round1_statements:
            messagebox.showinfo("提示", "请先完成辩论")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML", "*.html"), ("JSON", "*.json")],
            title="导出投研报告",
        )
        if not filepath:
            return

        try:
            if filepath.endswith(".html"):
                html = ReportTemplate.build_html_report(
                    self.engine.state, self._report or {},
                    self._signals or [], "")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html)
            else:
                export = {
                    "report": self._report,
                    "signals": self._signals,
                    "round1": self.engine.state.round1_statements,
                    "round2": self.engine.state.round2_statements,
                    "consensus": self.engine.state.round3_result,
                }
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(export, f, ensure_ascii=False, indent=2, default=str)

            self._append_debate(f"\n✅ 已导出: {filepath}\n")
        except Exception as e:
            self._append_debate(f"\n❌ 导出失败: {e}\n")

    # ========================================================================
    # Prompt编辑器
    # ========================================================================
    def _show_prompt_editor(self):
        """编辑三个分析师的prompt"""
        win = tk.Toplevel(self.parent)
        win.title("✏️ 分析师 Prompt 编辑器")
        win.geometry("800x600")

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        roles = get_analyst_roles()
        self._prompt_texts = {}

        for key, role in roles.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=f"{role['emoji']} {role['name']}")

            # 说明
            ttk.Label(frame, text=f"角色: {role['name']} | 核心问题: {role['core_question']}",
                      font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", padx=4, pady=4)

            # 编辑区
            text = tk.Text(frame, wrap="word", font=("Consolas", 10))
            text.pack(fill="both", expand=True, padx=4, pady=4)
            text.insert("1.0", role["system_prompt"])
            self._prompt_texts[key] = text

        # 辩论系统提示词
        sys_frame = ttk.Frame(notebook)
        notebook.add(sys_frame, text="🎯 辩论系统")
        sys_text = tk.Text(sys_frame, wrap="word", font=("Consolas", 10))
        sys_text.pack(fill="both", expand=True, padx=4, pady=4)
        sys_text.insert("1.0", get_debate_system_prompt())
        self._prompt_texts["_system"] = sys_text

        # 按钮
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill="x", padx=8, pady=4)
        ttk.Button(btn_frame, text="💾 保存", command=self._save_prompts).pack(side="left")
        ttk.Button(btn_frame, text="🔄 重置默认", command=self._reset_prompts).pack(side="left", padx=8)

    def _save_prompts(self):
        """保存自定义prompt"""
        # 保存到配置文件
        custom_prompts = {}
        for key, text in self._prompt_texts.items():
            custom_prompts[key] = text.get("1.0", "end").strip()

        cfg_path = Path.home() / ".financialanalyzer" / "custom_prompts.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(custom_prompts, f, ensure_ascii=False, indent=2)

        self._append_debate("✅ Prompt 已保存\n")

    def _reset_prompts(self):
        """重置为默认prompt"""
        roles = get_analyst_roles()
        for key, text in self._prompt_texts.items():
            if key == "_system":
                text.delete("1.0", "end")
                text.insert("1.0", get_debate_system_prompt())
            elif key in roles:
                text.delete("1.0", "end")
                text.insert("1.0", roles[key]["system_prompt"])
        self._append_debate("✅ 已重置为默认 Prompt\n")

    # ========================================================================
    # 清空
    # ========================================================================
    def _clear_all(self):
        """清空所有显示"""
        for text in self.analyst_texts.values():
            text.delete("1.0", "end")
        self.debate_text.delete("1.0", "end")
        self._set_status("就绪")

    # ========================================================================
    # 工具方法
    # ========================================================================
    def _append_analyst(self, analyst_id, text):
        """追加文本到分析师卡片"""
        tw = self.analyst_texts.get(analyst_id)
        if tw:
            tw.insert("end", text)
            tw.see("end")

    def _append_debate(self, text):
        """追加文本到辩论区"""
        self.debate_text.insert("end", text)
        self.debate_text.see("end")

    def _set_status(self, text):
        self.status_label.config(text=text)

    def _load_api_config(self):
        """加载DeepSeek API配置"""
        try:
            cfg_path = Path.home() / ".financialanalyzer" / "config.json"
            if cfg_path.exists():
                with open(cfg_path) as f:
                    cfg = json.load(f)
                    return (cfg.get("deepseek_api_key", ""),
                            cfg.get("deepseek_base_url", "https://api.deepseek.com"),
                            cfg.get("deepseek_model", "deepseek-chat"))
        except Exception:
            pass
        return ("", "https://api.deepseek.com", "deepseek-chat")

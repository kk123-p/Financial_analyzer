"""
Debate Engine - Orchestrates the three-round debate flow.
Supports streaming output, user follow-ups, and weight adjustments.
"""
import threading
import time
from dataclasses import dataclass, field

from ..deepseek.client import DeepSeekStreamClient, DeepSeekConfig
from ..deepseek.prompts import (
    get_debate_system_prompt, get_analyst_roles,
    build_debate_round1, build_debate_round2, build_debate_round3,
    build_user_followup, build_weight_adjustment,
)
from .report_builder import ReportBuilder
from .signal_detector import SignalDetector
from .briefing_generator import BriefingGenerator
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DebateState:
    """Debate state container"""
    phase: str = "idle"
    round1_statements: dict = field(default_factory=dict)
    round2_statements: dict = field(default_factory=dict)
    round3_result: str = ""
    full_debate_text: str = ""
    current_analyst: str = ""
    report: dict = field(default_factory=dict)
    report_text: str = ""
    signals: list = field(default_factory=list)
    error: str = ""


class DebateEngine:
    """Debate engine that orchestrates three-round analyst debates."""

    def __init__(self, api_key: str, model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com", config=None):
        if config:
            self.client = DeepSeekStreamClient(config=config)
        else:
            self.client = DeepSeekStreamClient(config=DeepSeekConfig(
                api_key=api_key, model=model, base_url=base_url))
        self.state = DebateState()
        self._stop_event = threading.Event()
        self._thread = None

    def prepare(self, data: dict, stock_code: str,
                data_adapter=None, cache_manager=None) -> dict:
        """Build report and detect signals before debate."""
        report = ReportBuilder.build(data, stock_code, data_adapter, cache_manager)
        report_text = self._report_to_text(report)
        signals = SignalDetector.detect(report)
        briefings = BriefingGenerator.generate_all(report)

        self.state.report = report
        self.state.report_text = report_text
        self.state.signals = signals

        return {
            "report": report,
            "report_text": report_text,
            "signals": signals,
            "briefings": briefings,
        }

    def _report_to_text(self, report: dict) -> str:
        """将体检报告dict转为可读文本，作为AI的输入"""
        import json
        parts = []
        snap = report.get("company_snapshot", {})
        parts.append(f"公司: {report.get('stock_code', '')}")
        parts.append(f"股价: {snap.get('price', 'N/A')} | PE: {snap.get('pe', 'N/A')} | PB: {snap.get('pb', 'N/A')} | 市值: {snap.get('market_cap_yi', 'N/A')}亿")
        parts.append("")

        # 财务健康
        health = report.get("financial_health", {})
        parts.append("## 财务健康仪表盘")
        for section in ["盈利能力", "偿债能力", "营运能力", "发展能力"]:
            data = health.get(section, {})
            if data:
                parts.append(f"\n### {section}")
                for k, v in data.items():
                    parts.append(f"  {k}: {v}")

        # 杜邦
        dupont = report.get("dupont_analysis", {})
        if dupont.get("three_factor"):
            parts.append("\n## 杜邦分析")
            for dp in dupont["three_factor"]:
                parts.append(f"  {dp.get('end_date','')}: ROE={dp.get('roe','')}% 净利率={dp.get('net_margin','')}% 周转={dp.get('asset_turnover','')} 杠杆={dp.get('equity_multiplier','')}")

        # 风险模型
        risk = report.get("risk_models", {})
        parts.append("\n## 风险模型")
        for key, name in [("zscore", "Z-score"), ("fscore", "F-score"), ("mscore", "M-score")]:
            d = risk.get(key, {})
            if d:
                parts.append(f"  {name}: {d}")

        # 矛盾信号
        signals = report.get("anomaly_signals", [])
        if signals:
            parts.append("\n## 异常信号")
            for s in signals:
                parts.append(f"  - {s.get('name','')}: {s.get('data','')}")

        return "\n".join(parts)

    def start_debate(self, company_name: str, stock_code: str,
                     callback=None, on_complete=None):
        """Start the three-round debate (async)."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_debate,
            args=(company_name, stock_code, callback, on_complete),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Stop the debate."""
        self._stop_event.set()

    def send_followup(self, question: str, callback=None, on_complete=None):
        """Send a user follow-up question."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_followup,
            args=(question, callback, on_complete),
            daemon=True,
        )
        self._thread.start()

    def adjust_weights(self, weight_value: int, weight_growth: int, weight_risk: int,
                       callback=None, on_complete=None):
        """Adjust perspective weights."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_weight_adjustment,
            args=(weight_value, weight_growth, weight_risk, callback, on_complete),
            daemon=True,
        )
        self._thread.start()

    # ========================================================================
    # Internal execution
    # ========================================================================

    def _run_debate(self, company_name, stock_code, callback, on_complete):
        """Execute the three-round debate."""
        try:
            report_text = self.state.report_text
            roles = get_analyst_roles()

            # --- Round 1: Independent statements ---
            self.state.phase = "round1"
            if callback:
                callback("_meta", "round1_start", False)

            for analyst_id in ["value", "growth", "risk"]:
                if self._stop_event.is_set():
                    break
                self.state.current_analyst = analyst_id
                role = roles[analyst_id]
                if callback:
                    callback("_meta", f"analyst_{analyst_id}_start", False)

                prompt = build_debate_round1(report_text, company_name, stock_code, analyst_id)
                result = self._stream_call(prompt, role["system_prompt"], callback, analyst_id)

                if result.success:
                    self.state.round1_statements[analyst_id] = result.content
                else:
                    self.state.round1_statements[analyst_id] = f"[Error: {result.error}]"

                if callback:
                    callback("_meta", f"analyst_{analyst_id}_done", False)

            if self._stop_event.is_set():
                return

            # --- Round 2: Cross-examination ---
            self.state.phase = "round2"
            if callback:
                callback("_meta", "round2_start", False)

            round2_prompt = build_debate_round2(self.state.round1_statements)

            for analyst_id in ["value", "growth", "risk"]:
                if self._stop_event.is_set():
                    break
                self.state.current_analyst = analyst_id
                role = roles[analyst_id]
                if callback:
                    callback("_meta", f"analyst_{analyst_id}_start", False)

                full_prompt = f"You are {role['name']}.\n\n{round2_prompt}"
                result = self._stream_call(full_prompt, role["system_prompt"], callback, analyst_id)

                if result.success:
                    self.state.round2_statements[analyst_id] = result.content
                else:
                    self.state.round2_statements[analyst_id] = f"[Error: {result.error}]"

                if callback:
                    callback("_meta", f"analyst_{analyst_id}_done", False)

            if self._stop_event.is_set():
                return

            # --- Round 3: Consensus map ---
            self.state.phase = "round3"
            if callback:
                callback("_meta", "round3_start", False)

            full_debate = self._build_full_debate_text()
            self.state.full_debate_text = full_debate
            round3_prompt = build_debate_round3(full_debate)

            def consensus_cb(chunk, done):
                if callback:
                    callback("consensus", chunk, done)

            result = self.client.generate_deep_analysis_stream(
                round3_prompt, system_prompt=get_debate_system_prompt(), callback=consensus_cb
            )

            if result.success:
                self.state.round3_result = result.content
            else:
                self.state.round3_result = f"[Error: {result.error}]"

            self.state.phase = "complete"
            if callback:
                callback("_meta", "debate_complete", True)
            if on_complete:
                on_complete(self.state)

        except Exception as e:
            logger.error(f"Debate failed: {e}")
            self.state.error = str(e)
            self.state.phase = "error"
            if callback:
                callback("_meta", f"error:{e}", True)

    def _run_followup(self, question, callback, on_complete):
        """Execute user follow-up."""
        try:
            self.state.phase = "followup"
            roles = get_analyst_roles()
            debate_context = self._build_full_debate_text()
            prompt = build_user_followup(question, debate_context)

            for analyst_id in ["value", "growth", "risk"]:
                if self._stop_event.is_set():
                    break
                self.state.current_analyst = analyst_id
                role = roles[analyst_id]
                if callback:
                    callback("_meta", f"analyst_{analyst_id}_start", False)

                full_prompt = f"You are {role['name']}.\n\n{prompt}"
                self._stream_call(full_prompt, role["system_prompt"], callback, analyst_id)

                if callback:
                    callback("_meta", f"analyst_{analyst_id}_done", False)

            self.state.phase = "complete"
            if callback:
                callback("_meta", "followup_complete", True)
            if on_complete:
                on_complete(self.state)

        except Exception as e:
            logger.error(f"Followup failed: {e}")
            self.state.error = str(e)
            if callback:
                callback("_meta", f"error:{e}", True)

    def _run_weight_adjustment(self, wv, wg, wr, callback, on_complete):
        """Execute weight adjustment."""
        try:
            self.state.phase = "weight"
            prompt = build_weight_adjustment(wv, wg, wr, self.state.round3_result or "")
            full_debate = self._build_full_debate_text()
            prompt = f"Full debate record:\n{full_debate}\n\n{prompt}"

            def consensus_cb(chunk, done):
                if callback:
                    callback("consensus", chunk, done)

            result = self.client.generate_deep_analysis_stream(
                prompt, system_prompt=get_debate_system_prompt(), callback=consensus_cb
            )

            if result.success:
                self.state.round3_result = result.content

            self.state.phase = "complete"
            if callback:
                callback("_meta", "weight_complete", True)
            if on_complete:
                on_complete(self.state)

        except Exception as e:
            logger.error(f"Weight adjustment failed: {e}")
            self.state.error = str(e)
            if callback:
                callback("_meta", f"error:{e}", True)

    def _stream_call(self, prompt, system_prompt, callback, analyst_id):
        """Helper to make a streaming API call."""
        def stream_cb(chunk, done):
            if callback:
                callback(analyst_id, chunk, done)

        return self.client.generate_deep_analysis_stream(
            prompt, system_prompt=system_prompt, callback=stream_cb
        )

    def _build_full_debate_text(self) -> str:
        """Combine all debate content into text."""
        roles = get_analyst_roles()
        parts = []

        if self.state.round1_statements:
            parts.append("### Round 1: Independent Statements")
            for aid, stmt in self.state.round1_statements.items():
                role = roles.get(aid, {})
                parts.append(f"\n#### {role.get('emoji', '')} {role.get('name', aid)}:")
                parts.append(stmt)

        if self.state.round2_statements:
            parts.append("\n\n### Round 2: Cross-Examination")
            for aid, stmt in self.state.round2_statements.items():
                role = roles.get(aid, {})
                parts.append(f"\n#### {role.get('emoji', '')} {role.get('name', aid)}:")
                parts.append(stmt)

        return "\n".join(parts)

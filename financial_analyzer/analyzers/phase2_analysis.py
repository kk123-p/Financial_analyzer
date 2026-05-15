"""
二阶段分析模块 - 专业级财务分析
v10.5: 基于专业财务分析框架全面重写
"""
import pandas as pd
import numpy as np
from ..logging_config import get_logger

logger = get_logger(__name__)


class Phase2Analyzer:
    """二阶段分析器 - 估值、股东回报、财报质量分析"""

    def __init__(self, data: dict, stock_code: str = "", data_adapter=None):
        self.data = data
        self.stock_code = stock_code
        self.data_adapter = data_adapter

    def analyze(self, peers_data: list = None) -> dict:
        """执行二阶段分析"""
        result = {
            "估值分析": self.valuation_analysis(),
            "PE历史分位": self.pe_percentile_analysis(),
            "PB_ROE模型": self.pb_roe_analysis(),
            "EV_EBITDA": self.ev_ebitda_analysis(),
            "股东回报": self.shareholder_return_analysis(),
            "财务质量": self.financial_quality_analysis(),
        }
        if peers_data:
            result["同行对比"] = self.compare_with_peers(peers_data)
        return result

    # ====================================================================
    # 辅助方法
    # ====================================================================
    COLUMN_ALIASES = {
        "net_profit": ["n_income", "n_income_attr_p", "净利润"],
        "revenue": ["total_revenue", "营业收入", "营业总收入"],
        "total_equity": ["total_hldr_eqy_exc_min_int", "total_hldr_eqy_inc_min_int", "股东权益合计"],
        "total_assets": ["资产总计"],
        "total_liab": ["负债合计"],
        "money_cap": ["cash", "货币资金"],
        "accounts_receivable": ["accounts_receiv", "acc_receivable", "应收账款"],
        "operate_profit": ["营业利润"],
        "interest_expense": ["fin_exp", "财务费用"],
        "close": ["收盘价"],
        "total_share": ["total_share_y", "总股本"],
        "inventories": ["inventory", "存货"],
        "goodwill": ["商誉"],
        "construction_in_process": ["在建工程"],
        "gross_margin": ["grossprofit_margin", "毛利率"],
        "net_margin": ["netprofit_margin", "净利率"],
        "roe": ["净资产收益率", "roe_yoy"],
        "eps": ["basic_eps", "每股收益"],
        "n_cashflow_act": ["经营活动现金流净额"],
        "c_fr_sale_sg": ["销售商品收到的现金"],
        "income_tax": ["所得税"],
        "total_profit": ["利润总额"],
    }

    def _val(self, row, keys: list):
        if row is None:
            return None
        for key in keys:
            if key in row.index:
                v = row[key]
                if pd.notna(v):
                    return float(v)
        for key in keys:
            for alias in self.COLUMN_ALIASES.get(key, []):
                if alias in row.index:
                    v = row[alias]
                    if pd.notna(v):
                        return float(v)
        return None

    def _get_price_data(self):
        """获取股价数据（从 daily 或 basic 中查找）"""
        # 优先从 daily 获取
        daily = self.data.get("daily")
        if daily is not None and not daily.empty:
            return daily
        # 退而从 basic 获取
        basic = self._get_price_data()
        if basic is not None and not basic.empty:
            return basic
        return None

    def _get_multi_year(self, data_type: str, years: int = 5) -> pd.DataFrame:
        """获取多年数据（按时间正序：最旧在前）"""
        df = self.data.get(data_type)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return pd.DataFrame()
        if "end_date" in df.columns:
            annual = df[df["end_date"].astype(str).str.endswith("1231")].drop_duplicates("end_date").head(years)
            if annual.empty:
                annual = df.drop_duplicates("end_date").head(years)
            # 按时间正序排列（最旧在前）
            annual = annual.sort_values("end_date").reset_index(drop=True)
            return annual
        return df.head(years)

    def _fmt_yi(self, val):
        if val is None: return "N/A"
        return f"{val / 1e8:.2f}亿"

    def _fmt_pct(self, val):
        if val is None: return "N/A"
        return f"{val:.2f}%"

    # ====================================================================
    # 1. 股东回报分析
    # ====================================================================
    def shareholder_return_analysis(self) -> str:
        """
        股东回报分析
        核心问题：股东投入的钱，获得了多少回报？
        指标：ROE趋势、EPS趋势、分红率、综合回报率
        """
        income = self._get_multi_year("income", 5)
        balance = self._get_multi_year("balance", 5)
        basic = self._get_price_data()
        financial = self._get_multi_year("financial", 5)

        if income.empty or balance.empty:
            return "⚠️ 数据不足，无法进行股东回报分析"

        lines = ["=" * 55, "  股东回报分析", "=" * 55]

        try:
            # --- ROE 趋势 ---
            lines.append("\n  【ROE趋势（净资产收益率）】")
            roe_list = []
            for i in range(min(len(income), len(balance))):
                np_ = self._val(income.iloc[i], ["net_profit"])
                eq = self._val(balance.iloc[i], ["total_equity"])
                ed = str(income.iloc[i].get("end_date", ""))
                if np_ is not None and eq and eq > 0:
                    roe = np_ / eq * 100
                    roe_list.append((ed, roe))
                    bar = "█" * max(0, int(roe / 2))
                    lines.append(f"  {ed}: ROE={roe:>7.2f}% {bar}")

            if len(roe_list) >= 2:
                first_roe = roe_list[0][1]
                last_roe = roe_list[-1][1]
                if last_roe > first_roe * 1.1:
                    lines.append(f"  → ROE趋势上升（{first_roe:.1f}% → {last_roe:.1f}%），盈利能力增强")
                elif last_roe < first_roe * 0.9:
                    lines.append(f"  → ROE趋势下降（{first_roe:.1f}% → {last_roe:.1f}%），需关注")
                else:
                    lines.append(f"  → ROE保持稳定（约{last_roe:.1f}%）")

            # --- EPS 趋势 ---
            lines.append("\n  【EPS趋势（每股收益）】")
            eps_list = []
            if financial is not None and not financial.empty:
                for i in range(len(financial)):
                    eps = self._val(financial.iloc[i], ["eps"])
                    ed = str(financial.iloc[i].get("end_date", ""))
                    if eps is not None:
                        eps_list.append((ed, eps))
                        lines.append(f"  {ed}: EPS = {eps:.4f} 元")

            if not eps_list:
                # 从 basic 获取
                if basic is not None and len(basic) > 0:
                    for i in range(min(5, len(basic))):
                        close = self._val(basic.iloc[i], ["close"])
                        pe = self._val(basic.iloc[i], ["pe"])
                        ed = str(basic.iloc[i].get("trade_date", ""))
                        if close and pe and pe > 0:
                            eps = close / pe
                            eps_list.append((ed, eps))
                            lines.append(f"  {ed}: EPS ≈ {eps:.4f} 元（估算）")

            if len(eps_list) >= 2:
                if eps_list[-1][1] > eps_list[0][1] * 1.1:
                    lines.append(f"  → EPS持续增长，股东价值提升")
                elif eps_list[-1][1] < eps_list[0][1] * 0.9:
                    lines.append(f"  → EPS下降，需关注盈利可持续性")

            # --- 综合股东回报率 ---
            lines.append("\n  【综合股东回报率】")
            if basic is not None and len(basic) >= 2:
                close_now = self._val(basic.iloc[-1], ["close"])
                close_prev = self._val(basic.iloc[0], ["close"])
                if close_now and close_prev and close_prev > 0:
                    price_return = (close_now - close_prev) / close_prev * 100
                    lines.append(f"  股价变动: {close_prev:.2f} → {close_now:.2f}（{price_return:+.2f}%）")
                    lines.append(f"  注：综合回报率 = 股价涨幅 + 累计分红（分红数据需额外获取）")

            # --- 留存收益效率 ---
            if len(balance) >= 2 and len(income) >= 2:
                eq_cur = self._val(balance.iloc[-1], ["total_equity"])
                eq_prev = self._val(balance.iloc[0], ["total_equity"])
                np_sum = sum(self._val(income.iloc[i], ["net_profit"]) or 0 for i in range(len(income)))
                if eq_cur and eq_prev and np_sum > 0:
                    equity_growth = eq_cur - eq_prev
                    retention_ratio = 1 - 0.3  # 假设30%分红
                    expected_retention = np_sum * retention_ratio
                    if expected_retention > 0:
                        efficiency = equity_growth / expected_retention
                        lines.append(f"\n  【留存收益再投资效率】")
                        lines.append(f"  累计净利润: {self._fmt_yi(np_sum)}")
                        lines.append(f"  净资产增长: {self._fmt_yi(equity_growth)}")
                        lines.append(f"  留存效率: {efficiency:.2f}（>1表示留存收益有效转化为净资产）")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"股东回报分析异常: {e}")
            return f"⚠️ 股东回报分析异常: {e}"

    # ====================================================================
    # 2. 估值分析
    # ====================================================================
    def valuation_analysis(self) -> str:
        """
        估值分析
        核心问题：当前股价相对于公司价值，贵了还是便宜了？
        指标：PE/PB/PS/PEG、历史分位、行业对比
        """
        income = self._get_multi_year("income", 5)
        balance = self._get_multi_year("balance", 5)
        basic = self._get_price_data()
        financial = self._get_multi_year("financial", 5)

        if income.empty:
            return "⚠️ 数据不足"

        lines = ["=" * 55, "  估值分析", "=" * 55]

        try:
            latest_inc = income.iloc[-1]
            np_ = self._val(latest_inc, ["net_profit"])
            revenue = self._val(latest_inc, ["revenue"])

            latest_bal = balance.iloc[-1] if not balance.empty else None
            total_equity = self._val(latest_bal, ["total_equity"]) if latest_bal is not None else None

            close = None
            total_share = None
            if basic is not None and len(basic) > 0:
                close = self._val(basic.iloc[-1], ["close"])
                total_share = self._val(basic.iloc[-1], ["total_share"])

            if not (close and total_share and total_share > 0):
                lines.append("\n  ⚠️ 缺少股价/股本数据")
                return "\n".join(lines)

            market_cap = close * total_share
            lines.append(f"\n  股价: {close:.2f} 元 | 总市值: {self._fmt_yi(market_cap)}")

            # --- PE ---
            if np_ and np_ > 0:
                pe = market_cap / np_
                earnings_yield = 1 / pe * 100
                lines.append(f"\n  【PE估值（市盈率）】")
                lines.append(f"  PE(TTM) = {pe:.1f}倍")
                lines.append(f"  盈利收益率 = {earnings_yield:.2f}%（银行存款约2.5%，10年国债约2.8%）")
                if pe < 10:
                    lines.append(f"  → 低估区间：PE<10，市场对盈利预期很低或公司有风险")
                elif pe < 20:
                    lines.append(f"  → 合理区间：PE 10-20，估值正常")
                elif pe < 40:
                    lines.append(f"  → 偏高区间：PE 20-40，需要高增长支撑")
                else:
                    lines.append(f"  → 高估区间：PE>40，市场给予极高成长溢价")

                # PEG
                if len(income) >= 2:
                    np_prev = self._val(income.iloc[-2], ["net_profit"])
                    if np_prev and np_prev > 0:
                        growth = (np_ - np_prev) / np_prev * 100
                        if growth > 0:
                            peg = pe / growth
                            lines.append(f"\n  【PEG估值】")
                            lines.append(f"  净利润增速: {growth:.1f}%")
                            lines.append(f"  PEG = PE/增速 = {pe:.1f}/{growth:.1f} = {peg:.2f}")
                            if peg < 1:
                                lines.append(f"  → PEG<1，增长未被充分定价，可能低估")
                            elif peg < 2:
                                lines.append(f"  → PEG合理（1-2），增长与估值匹配")
                            else:
                                lines.append(f"  → PEG>2，估值相对增速偏高")

            # --- PB ---
            if total_equity and total_equity > 0:
                pb = market_cap / total_equity
                roe = np_ / total_equity * 100 if np_ else 0
                lines.append(f"\n  【PB估值（市净率）】")
                lines.append(f"  PB = {pb:.2f}倍 | ROE = {roe:.2f}%")
                if roe > 0:
                    # PB-ROE匹配度
                    fair_pb = roe / 10  # 简化：ROE/要求回报率
                    lines.append(f"  PB-ROE匹配: ROE {roe:.1f}% 支撑约 {fair_pb:.1f}倍PB")
                    if pb < fair_pb * 0.8:
                        lines.append(f"  → PB低于ROE支撑水平，可能低估")
                    elif pb > fair_pb * 1.2:
                        lines.append(f"  → PB高于ROE支撑水平，可能高估")
                    else:
                        lines.append(f"  → PB与ROE基本匹配")

            # --- PS ---
            if revenue and revenue > 0:
                ps = market_cap / revenue
                net_margin = np_ / revenue * 100 if np_ and revenue else 0
                lines.append(f"\n  【PS估值（市销率）】")
                lines.append(f"  PS = {ps:.2f}倍 | 净利率 = {net_margin:.2f}%")
                if ps < 1:
                    lines.append(f"  → PS<1，营收规模大于市值，可能低估或行业低利润")
                elif ps < 5:
                    lines.append(f"  → PS合理")
                else:
                    lines.append(f"  → PS偏高，需要高利润率或高增长支撑")

            # --- 行业对比维度 ---
            lines.append(f"\n  【估值总结】")
            pe_val = market_cap / np_ if np_ and np_ > 0 else None
            pb_val = market_cap / total_equity if total_equity and total_equity > 0 else None
            if pe_val and pe_val < 15 and pb_val and pb_val < 2:
                lines.append(f"  综合判断: 偏低估（PE和PB均处于较低水平）")
            elif pe_val and pe_val > 30 or pb_val and pb_val > 5:
                lines.append(f"  综合判断: 偏高估（估值指标偏高）")
            else:
                lines.append(f"  综合判断: 估值合理区间")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"估值分析异常: {e}")
            return f"⚠️ 估值分析异常: {e}"

    # ====================================================================
    # 3. 财报质量分析
    # ====================================================================
    def financial_quality_analysis(self) -> str:
        """
        财报质量分析
        核心问题：财报数字是否真实可靠？有没有粉饰/造假嫌疑？
        维度：盈余质量、收入质量、资产质量、会计政策
        """
        income = self._get_multi_year("income", 3)
        balance = self._get_multi_year("balance", 3)
        cashflow = self._get_multi_year("cashflow", 3)
        financial = self._get_multi_year("financial", 3)

        if income.empty:
            return "⚠️ 数据不足"

        lines = ["=" * 55, "  财报质量分析", "=" * 55]

        try:
            latest_inc = income.iloc[-1]
            np_ = self._val(latest_inc, ["net_profit"])
            revenue = self._val(latest_inc, ["revenue"])

            latest_bal = balance.iloc[-1] if not balance.empty else None
            total_assets = self._val(latest_bal, ["total_assets"]) if latest_bal is not None else None

            # === 盈余质量 ===
            lines.append(f"\n  【盈余质量】")

            # 经营现金流/净利润
            if not cashflow.empty:
                ocf = self._val(cashflow.iloc[-1], ["n_cashflow_act"])
                if np_ and np_ > 0 and ocf is not None:
                    cf_np_ratio = ocf / np_
                    lines.append(f"  经营现金流/净利润 = {cf_np_ratio:.2f}")
                    if cf_np_ratio >= 1:
                        lines.append(f"  → ✅ 优秀：利润有充足的现金支撑，盈利质量高")
                    elif cf_np_ratio >= 0.7:
                        lines.append(f"  → 良好：大部分利润有现金支撑")
                    elif cf_np_ratio >= 0:
                        lines.append(f"  → ⚠️ 偏低：部分利润未转化为现金，可能有应计项目")
                    else:
                        lines.append(f"  → ❌ 差：经营现金流为负，利润质量严重存疑")

            # 应计利润比率 = (净利润 - 经营现金流) / 总资产
            if not cashflow.empty and total_assets and total_assets > 0:
                ocf = self._val(cashflow.iloc[-1], ["n_cashflow_act"])
                if np_ is not None and ocf is not None:
                    accrual = (np_ - ocf) / total_assets
                    lines.append(f"  应计利润比率 = {accrual:.4f}")
                    if abs(accrual) < 0.05:
                        lines.append(f"  → ✅ 应计利润低，盈余质量好")
                    elif abs(accrual) < 0.1:
                        lines.append(f"  → 应计利润偏高，需关注")
                    else:
                        lines.append(f"  → ❌ 应计利润过高，可能存在盈余管理")

            # === 收入质量 ===
            lines.append(f"\n  【收入质量】")

            if len(income) >= 2 and not balance.empty and len(balance) >= 2:
                rev_cur = self._val(income.iloc[-1], ["revenue"])
                rev_prev = self._val(income.iloc[-2], ["revenue"])
                ar_cur = self._val(balance.iloc[-1], ["accounts_receivable"])
                ar_prev = self._val(balance.iloc[-2], ["accounts_receivable"])

                if rev_cur and rev_prev and rev_prev > 0:
                    rev_growth = (rev_cur - rev_prev) / rev_prev * 100
                    lines.append(f"  营收增速: {rev_growth:.1f}%")

                    if ar_cur and ar_prev and ar_prev > 0:
                        ar_growth = (ar_cur - ar_prev) / ar_prev * 100
                        lines.append(f"  应收增速: {ar_growth:.1f}%")
                        gap = ar_growth - rev_growth
                        if gap > 20:
                            lines.append(f"  → ❌ 应收增速远超营收（差{gap:.0f}pct），可能虚增收入")
                        elif gap > 10:
                            lines.append(f"  → ⚠️ 应收增速略高于营收，需关注")
                        else:
                            lines.append(f"  → ✅ 应收与营收增速匹配")

            # 收入现金比
            if not cashflow.empty and revenue and revenue > 0:
                cash_receipts = self._val(cashflow.iloc[-1], ["c_fr_sale_sg"])
                if cash_receipts and cash_receipts > 0:
                    receipt_ratio = cash_receipts / revenue
                    # 单位修正
                    if receipt_ratio > 100:
                        receipt_ratio = cash_receipts / (revenue * 10000)
                    lines.append(f"  收入现金比 = {receipt_ratio:.2f}（销售收到现金/营收）")
                    if receipt_ratio >= 1:
                        lines.append(f"  → ✅ 收入质量好，营收都有现金支撑")
                    elif receipt_ratio >= 0.8:
                        lines.append(f"  → 收入质量一般")
                    else:
                        lines.append(f"  → ⚠️ 收入现金比偏低，可能有大量赊销")

            # === 资产质量 ===
            if not balance.empty and len(balance) >= 2:
                lines.append(f"\n  【资产质量】")

                # 存货异常
                inv_cur = self._val(balance.iloc[-1], ["inventories"])
                inv_prev = self._val(balance.iloc[-2], ["inventories"])
                if inv_cur and inv_prev and inv_prev > 0:
                    inv_growth = (inv_cur - inv_prev) / inv_prev * 100
                    cost_cur = self._val(income.iloc[-1], ["operate_profit"])
                    cost_prev = self._val(income.iloc[-2], ["operate_profit"]) if len(income) >= 2 else None
                    lines.append(f"  存货增速: {inv_growth:.1f}%")
                    if inv_growth > 30:
                        lines.append(f"  → ⚠️ 存货大幅增长，需关注是否有滞销或虚增")

                # 商誉风险
                gw = self._val(balance.iloc[-1], ["goodwill"])
                eq = self._val(balance.iloc[-1], ["total_equity"])
                if gw and eq and eq > 0:
                    gw_ratio = gw / eq * 100
                    lines.append(f"  商誉/净资产 = {gw_ratio:.1f}%")
                    if gw_ratio > 30:
                        lines.append(f"  → ❌ 商誉占比高，减值风险大")
                    elif gw_ratio > 10:
                        lines.append(f"  → ⚠️ 商誉有一定占比，需关注减值测试")
                    else:
                        lines.append(f"  → ✅ 商誉占比正常")

            # === M-score（盈余操纵检测）===
            if len(income) >= 2 and len(balance) >= 2:
                lines.append(f"\n  【盈余操纵检测（M-score）】")
                try:
                    mscore = self._calc_mscore(income, balance, cashflow)
                    if mscore is not None:
                        lines.append(f"  M-score = {mscore:.2f}")
                        if mscore > -1.78:
                            lines.append(f"  → ⚠️ M-score > -1.78，存在盈余操纵嫌疑")
                        else:
                            lines.append(f"  → ✅ M-score < -1.78，无明显操纵迹象")
                except Exception:
                    lines.append(f"  数据不足，无法计算M-score")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"财报质量分析异常: {e}")
            return f"⚠️ 财报质量分析异常: {e}"

    def _calc_mscore(self, income, balance, cashflow):
        """计算Beneish M-score"""
        if len(income) < 2 or len(balance) < 2:
            return None

        cur_inc = income.iloc[-1]
        prev_inc = income.iloc[-2]
        cur_bal = balance.iloc[-1]
        prev_bal = balance.iloc[-2]

        rev_cur = self._val(cur_inc, ["revenue"])
        rev_prev = self._val(prev_inc, ["revenue"])
        ar_cur = self._val(cur_bal, ["accounts_receivable"])
        ar_prev = self._val(prev_bal, ["accounts_receivable"])
        ta_cur = self._val(cur_bal, ["total_assets"])
        ta_prev = self._val(prev_bal, ["total_assets"])
        np_cur = self._val(cur_inc, ["net_profit"])
        ocf_cur = self._val(cashflow.iloc[-1], ["n_cashflow_act"]) if not cashflow.empty else None

        if not all([rev_cur, rev_prev, ar_cur, ar_prev, ta_cur, ta_prev]):
            return None

        # DSRI
        dsri = (ar_cur / rev_cur) / (ar_prev / rev_prev) if rev_prev > 0 and rev_cur > 0 else 1.0

        # GMI
        gm_prev = (rev_prev - self._val(prev_inc, ["operate_profit"])) / rev_prev if rev_prev > 0 else 0.5
        gm_cur = (rev_cur - self._val(cur_inc, ["operate_profit"])) / rev_cur if rev_cur > 0 else 0.5
        gmi = gm_prev / gm_cur if gm_cur > 0 else 1.0

        # SGI
        sgi = rev_cur / rev_prev if rev_prev > 0 else 1.0

        # LVGI
        debt_cur = self._val(cur_bal, ["total_liab"]) / ta_cur if ta_cur > 0 else 0
        debt_prev = self._val(prev_bal, ["total_liab"]) / ta_prev if ta_prev > 0 else 0
        lvgi = debt_cur / debt_prev if debt_prev > 0 else 1.0

        # TATA
        tata = (np_cur - ocf_cur) / ta_cur if np_cur is not None and ocf_cur is not None and ta_cur > 0 else 0

        m = (-4.84 + 0.920 * dsri + 0.528 * gmi + 0.892 * sgi
             - 0.172 * 1.0 + 4.679 * tata - 0.327 * lvgi)
        return m

    # ====================================================================
    # 4. 行业对比
    # ====================================================================
    def compare_with_peers(self, peers_data: list) -> str:
        """行业对比分析"""
        if not peers_data:
            return "⚠️ 无同行数据"

        income = self._get_multi_year("income", 1)
        balance = self._get_multi_year("balance", 1)

        if income.empty or balance.empty:
            return "⚠️ 数据不足"

        lines = ["=" * 55, "  行业对比分析", "=" * 55]

        try:
            np_ = self._val(income.iloc[-1], ["net_profit"])
            revenue = self._val(income.iloc[-1], ["revenue"])
            eq = self._val(balance.iloc[-1], ["total_equity"])
            ta = self._val(balance.iloc[-1], ["total_assets"])

            metrics = {}
            if revenue and revenue > 0 and np_:
                metrics["净利率"] = np_ / revenue * 100
            if ta and ta > 0 and revenue:
                metrics["资产周转率"] = revenue / ta
            if eq and eq > 0 and np_:
                metrics["ROE"] = np_ / eq * 100
            if ta and ta > 0:
                liab = self._val(balance.iloc[-1], ["total_liab"])
                if liab:
                    metrics["资产负债率"] = liab / ta * 100

            for name, val in metrics.items():
                peer_vals = [p.get(name) for p in peers_data if p.get(name) is not None]
                lines.append(f"\n  【{name}】")
                lines.append(f"  本公司: {val:.2f}")
                if peer_vals:
                    avg = np.mean(peer_vals)
                    med = np.median(peer_vals)
                    lines.append(f"  行业均值: {avg:.2f} | 中位数: {med:.2f}")
                    pct = sum(1 for v in peer_vals if v <= val) / len(peer_vals) * 100
                    lines.append(f"  行业分位: {pct:.0f}%")
                    if name == "资产负债率":
                        if val > avg * 1.2:
                            lines.append(f"  → 负债率高于行业均值，财务风险偏高")
                        elif val < avg * 0.8:
                            lines.append(f"  → 负债率低于行业均值，财务保守")
                        else:
                            lines.append(f"  → 负债率与行业水平相当")
                    else:
                        if val > avg * 1.2:
                            lines.append(f"  → 高于行业均值20%以上，具有竞争优势")
                        elif val < avg * 0.8:
                            lines.append(f"  → 低于行业均值20%以上，竞争力偏弱")
                        else:
                            lines.append(f"  → 处于行业平均水平")

            return "\n".join(lines)

        except Exception as e:
            return f"⚠️ 行业对比异常: {e}"

    # ====================================================================
    # PE分位 / PB-ROE / EV-EBITDA（保留但简化）
    # ====================================================================
    def pe_percentile_analysis(self) -> str:
        basic = self._get_price_data()
        income = self._get_multi_year("income", 5)
        if basic is None or income.empty or len(basic) < 10:
            return "⚠️ 数据不足（需要足够的历史数据）"
        try:
            pe_list = []
            np_ = self._val(income.iloc[-1], ["net_profit"])
            if not (np_ and np_ > 0):
                return "⚠️ 净利润数据不足"
            for i in range(len(basic)):
                c = self._val(basic.iloc[i], ["close"])
                s = self._val(basic.iloc[i], ["total_share"])
                if c and s and s > 0:
                    pe = c * s / np_
                    if 0 < pe < 500:
                        pe_list.append(pe)
            if not pe_list:
                return "⚠️ 无法计算PE"
            cur = pe_list[-1]
            pct = sum(1 for p in pe_list if p <= cur) / len(pe_list) * 100
            lines = ["=" * 55, "  PE历史分位", "=" * 55]
            lines.append(f"\n  当前PE: {cur:.1f}倍")
            lines.append(f"  历史范围: {min(pe_list):.1f} ~ {max(pe_list):.1f}倍")
            lines.append(f"  中位数: {np.median(pe_list):.1f}倍")
            lines.append(f"  当前分位: {pct:.1f}%")
            if pct <= 20:
                lines.append(f"  → 历史低位，可能低估")
            elif pct <= 40:
                lines.append(f"  → 偏低估")
            elif pct <= 60:
                lines.append(f"  → 合理区间")
            elif pct <= 80:
                lines.append(f"  → 偏高估")
            else:
                lines.append(f"  → 历史高位，可能高估")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ PE分位异常: {e}"

    def pb_roe_analysis(self, required_return: float = 10.0) -> str:
        income = self._get_multi_year("income", 1)
        balance = self._get_multi_year("balance", 1)
        basic = self._get_price_data()
        if income.empty or balance.empty:
            return "⚠️ 数据不足"
        try:
            np_ = self._val(income.iloc[-1], ["net_profit"])
            eq = self._val(balance.iloc[-1], ["total_equity"])
            if not (np_ and eq and eq > 0):
                return "⚠️ 数据不足"
            roe = np_ / eq * 100
            g = roe / 100 * 0.7
            r = required_return / 100
            lines = ["=" * 55, "  PB-ROE模型", "=" * 55]
            lines.append(f"\n  ROE = {roe:.2f}%")
            if r > g:
                fair_pb = (roe / 100 - g) / (r - g)
                lines.append(f"  理论PB = {fair_pb:.2f}倍（要求回报率{required_return}%）")
                if basic is not None and len(basic) > 0:
                    c = self._val(basic.iloc[-1], ["close"])
                    s = self._val(basic.iloc[-1], ["total_share"])
                    if c and s and s > 0:
                        actual_pb = c * s / eq
                        dev = (actual_pb - fair_pb) / fair_pb * 100 if fair_pb > 0 else 0
                        lines.append(f"  实际PB = {actual_pb:.2f}倍（偏离{dev:+.1f}%）")
                        if dev < -20:
                            lines.append(f"  → 明显低估")
                        elif dev < -5:
                            lines.append(f"  → 略低估")
                        elif dev <= 5:
                            lines.append(f"  → 合理估值")
                        elif dev <= 20:
                            lines.append(f"  → 略高估")
                        else:
                            lines.append(f"  → 明显高估")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ PB-ROE异常: {e}"

    def ev_ebitda_analysis(self) -> str:
        income = self._get_multi_year("income", 1)
        balance = self._get_multi_year("balance", 1)
        basic = self._get_price_data()
        if income.empty or balance.empty:
            return "⚠️ 数据不足"
        try:
            op = self._val(income.iloc[-1], ["operate_profit"])
            fin = self._val(income.iloc[-1], ["interest_expense"])
            liab = self._val(balance.iloc[-1], ["total_liab"])
            cash = self._val(balance.iloc[-1], ["money_cap"])
            if op is None:
                return "⚠️ 营业利润数据缺失"
            ebitda = op + (abs(fin) if fin and fin > 0 else 0)
            if basic is None or len(basic) == 0:
                return "⚠️ 缺少股价数据"
            c = self._val(basic.iloc[-1], ["close"])
            s = self._val(basic.iloc[-1], ["total_share"])
            if not (c and s and s > 0):
                return "⚠️ 缺少股价数据"
            mcap = c * s
            ev = mcap + (liab or 0) - (cash or 0)
            lines = ["=" * 55, "  EV/EBITDA", "=" * 55]
            lines.append(f"\n  EV = {self._fmt_yi(ev)}")
            lines.append(f"  EBITDA ≈ {self._fmt_yi(ebitda)}")
            if ebitda > 0:
                ratio = ev / ebitda
                lines.append(f"  EV/EBITDA = {ratio:.1f}倍")
                if ratio < 6:
                    lines.append(f"  → 可能低估")
                elif ratio < 10:
                    lines.append(f"  → 合理区间")
                elif ratio < 15:
                    lines.append(f"  → 偏高")
                else:
                    lines.append(f"  → 高估")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ EV/EBITDA异常: {e}"

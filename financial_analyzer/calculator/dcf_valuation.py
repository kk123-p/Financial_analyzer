"""
DCF估值引擎 — FA Pro v11
======================
基于CAPM-WACC的两阶段DCF估值模型：
  1. 使用CAPM动态计算WACC（而非硬编码折现率）
  2. 两阶段FCFF折现模型（预测期5年+永续）
  3. 敏感性分析（WACC × 永续增长率矩阵）
  4. 多情景分析（乐观/基准/悲观）

公式：
  FCFF = EBIT×(1-t) + 折旧摊销 - 资本支出 - Δ营运资本
  WACC = E/V×Re + D/V×Rd×(1-t)
  企业价值 = Σ(FCFF_t/(1+WACC)^t) + 终值/(1+WACC)^n
  每股公允价值 = (企业价值 - 净负债) / 总股本
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DCFResult:
    """DCF估值结果"""
    # 核心结果
    enterprise_value: float = 0.0       # 企业价值（亿元）
    equity_value: float = 0.0           # 股权价值（亿元）
    fair_price: float = 0.0             # 每股公允价值
    current_price: float = 0.0          # 当前股价
    upside_pct: float = 0.0             # 上涨空间%

    # 参数
    wacc: float = 0.0                   # 加权平均资本成本
    terminal_value_pct: float = 0.0     # 终值占企业价值比例
    fcf_growth_stage1: float = 0.0      # 阶段1增长率
    perpetuity_growth: float = 0.0      # 永续增长率

    # 明细
    projected_fcf: list[float] = field(default_factory=list)
    pv_fcf: list[float] = field(default_factory=list)
    terminal_value: float = 0.0
    net_debt: float = 0.0               # 净负债（亿元）
    total_shares: float = 0.0           # 总股本（亿股）

    # 风险参数
    risk_free_rate: float = 0.0
    beta: float = 0.0
    market_premium: float = 0.0
    cost_of_equity: float = 0.0
    cost_of_debt: float = 0.0
    tax_rate: float = 0.0
    debt_ratio: float = 0.0             # D/(D+E)

    # 多情景
    scenarios: dict = field(default_factory=dict)
    sensitivity_matrix: dict = field(default_factory=dict)

    # 评级
    valuation_rating: str = ""          # 低估/合理/高估
    confidence: str = ""                # 置信度评估


class DCFValuator:
    """DCF估值计算器"""

    # A股市场参数默认值
    DEFAULT_RISK_FREE = 0.025           # 中国10年期国债收益率 ~2.5%
    DEFAULT_MARKET_PREMIUM = 0.065      # A股历史市场风险溢价 ~6.5%
    DEFAULT_PERPETUITY_G = 0.025        # 默认永续增长率 2.5%
    TAX_RATE = 0.25                     # 企业所得税率 25%

    def __init__(
        self,
        risk_free_rate: float = None,
        market_premium: float = None,
    ):
        self.rf = risk_free_rate or self.DEFAULT_RISK_FREE
        self.mrp = market_premium or self.DEFAULT_MARKET_PREMIUM

    # ========================================================================
    # WACC 计算
    # ========================================================================

    def estimate_wacc(
        self,
        financial_data: dict,
        stock_code: str = "",
    ) -> dict:
        """
        基于CAPM计算WACC

        输入 financial_data 应包含：
          - total_equity: 股东权益（或从balance获取）
          - total_liab: 总负债
          - interest_expense: 利息支出
          - interest_bearing_debt: 有息负债（短期借款+长期借款+应付债券等）
          - close: 股价
          - total_share: 总股本
          - net_profit: 净利润

        返回 {wacc, re, rd, beta, debt_ratio, ...}
        """
        # 1. 估算Beta — 简化方法：从行业基准Beta查表
        # 在实际使用中会通过股票收益率回归来计算
        beta = self._estimate_beta(financial_data, stock_code)

        # 2. 权益成本 Re = Rf + β×(Rm-Rf)
        re = self.rf + beta * self.mrp

        # 3. 债务成本 Rd
        rd = self._estimate_cost_of_debt(financial_data)

        # 4. 资本结构
        eq = self._safe_float(self._extract(financial_data, [
            "total_equity", "total_hldr_eqy_exc_min_int",
            "tot_equity", "parent_equity",
        ]))
        debt = self._safe_float(self._extract(financial_data, [
            "total_liab", "tot_liabilities",
        ]))
        # 有息负债估算（优先从财报科目，降级用总负债50%近似）
        ib_debt = self._safe_float(self._extract(financial_data, [
            "interest_bearing_debt",
        ]))
        if ib_debt is None:
            short_borrowing = self._safe_float(self._extract(financial_data, [
                "short_borrowing", "短期借款",
            ])) or 0
            long_borrowing = self._safe_float(self._extract(financial_data, [
                "long_borrowing", "长期借款",
            ])) or 0
            bonds_payable = self._safe_float(self._extract(financial_data, [
                "bonds_payable", "应付债券",
            ])) or 0
            ib_debt = short_borrowing + long_borrowing + bonds_payable
            if ib_debt == 0:
                ib_debt = (debt * 0.5 if debt else 0)  # 最后降级

        # 市值权重
        close = self._safe_float(self._extract(financial_data, ["close", "price"]))
        shares = self._safe_float(self._extract(financial_data, [
            "total_share", "total_share_y",
        ]))
        market_cap = (close * shares) if close and shares else eq

        total_value = market_cap + ib_debt
        if total_value <= 0:
            total_value = eq + debt or 1.0

        weight_equity = market_cap / total_value
        weight_debt = ib_debt / total_value

        # 5. WACC = E/V × Re + D/V × Rd × (1-t)
        wacc = weight_equity * re + weight_debt * rd * (1 - self.TAX_RATE)

        # 确保WACC在合理范围内 (4%-20%)
        wacc = max(0.04, min(0.20, wacc))

        return {
            "wacc": round(wacc, 4),
            "cost_of_equity": round(re, 4),
            "cost_of_debt": round(rd, 4),
            "beta": round(beta, 2),
            "risk_free_rate": self.rf,
            "market_premium": self.mrp,
            "debt_ratio": round(weight_debt, 4),
            "market_cap_yi": round(market_cap / 1e8, 2) if market_cap else 0,
            "tax_rate": self.TAX_RATE,
        }

    def _estimate_beta(self, financial_data: dict, stock_code: str = "") -> float:
        """
        估算Beta系数

        简化方法（无历史收益率数据时）：
        — 基于行业查表（金融1.2, 科技1.3, 消费0.9, 医药1.1, 制造1.1）
        — 基于财务杠杆调整：β_equity = β_asset × (1 + D/E×(1-t))

        默认：1.0（市场平均）
        """
        # 尝试从数据中获取行业
        industry = self._extract(financial_data, ["industry", "所属行业"])
        industry_betas = {
            "银行": 0.7, "金融": 1.0, "保险": 0.8, "证券": 1.3,
            "医药": 1.0, "生物": 1.1, "医疗": 1.0,
            "食品": 0.8, "饮料": 0.8, "白酒": 0.9, "消费": 0.8,
            "科技": 1.3, "软件": 1.3, "计算机": 1.3, "互联网": 1.4,
            "电子": 1.2, "半导体": 1.4, "通信": 1.1,
            "房地产": 0.9, "建筑": 0.9, "建材": 1.0,
            "能源": 1.0, "化工": 1.1, "钢铁": 1.1, "有色": 1.2,
            "汽车": 1.1, "机械": 1.1, "电力": 0.6, "公用": 0.6,
            "传媒": 1.2, "零售": 1.0, "旅游": 1.1,
        }
        if industry:
            for key, beta in industry_betas.items():
                if key in str(industry):
                    return beta
        return 1.0

    def _estimate_cost_of_debt(self, financial_data: dict) -> float:
        """
        估算债务成本 Rd

        Rd = 利息支出 / 有息负债（近似）
        若无法计算，用 4% 作为中国企业的默认债务成本
        """
        interest = self._safe_float(self._extract(financial_data, [
            "interest_expense", "fin_exp",
        ]))
        ib_debt = self._safe_float(self._extract(financial_data, [
            "interest_bearing_debt",
        ]))

        if interest and ib_debt and ib_debt > 0:
            rd = interest / ib_debt
            return max(0.02, min(0.10, rd))  # 限制在2%-10%
        return 0.04  # 默认4%

    # ========================================================================
    # FCFF 预测
    # ========================================================================

    def calculate_historical_fcff(self, financial_data: dict) -> float | None:
        """计算最近一期的FCFF"""
        ebit = self._safe_float(self._extract(financial_data, [
            "operate_profit", "ebit", "营业利润",
        ]))
        if not ebit:
            np_val = self._safe_float(self._extract(financial_data, [
                "net_profit", "n_income_attr_p", "净利润",
            ]))
            interest = self._safe_float(self._extract(financial_data, [
                "interest_expense", "fin_exp",
            ])) or 0
            tax = self._safe_float(self._extract(financial_data, [
                "income_tax", "所得税",
            ])) or 0
            if np_val:
                ebit = np_val + interest + tax

        if not ebit:
            return None

        # 折旧摊销 — 优先从财务数据提取，否则估算
        da = self._safe_float(self._extract(financial_data, [
            "depreciation", "depreciation_amortization",
        ]))
        if da is None:
            da = (ebit * 0.15)  # 降级：假设折旧摊销占EBIT的15%

        # 资本支出 — 优先从财务数据提取，否则估算
        capex = self._safe_float(self._extract(financial_data, [
            "capital_expenditure", "capex",
        ]))
        if capex is None:
            capex = (ebit * 0.25)  # 降级：假设CapEx占EBIT的25%

        # 营运资本增加 — 优先从财务数据提取，否则估算
        revenue = self._safe_float(self._extract(financial_data, [
            "revenue", "total_revenue", "营业收入",
        ]))
        delta_wc = self._safe_float(self._extract(financial_data, [
            "delta_working_capital", "working_capital_change",
        ]))
        if delta_wc is None:
            delta_wc = (revenue * 0.03) if revenue else 0  # 降级：假设ΔWC占营收3%

        fcff = (ebit * (1 - self.TAX_RATE) + da - capex - delta_wc)
        return fcff

    def forecast_fcf(
        self,
        base_fcff: float,
        growth_stage1: float,
        years: int = 5,
    ) -> list[float]:
        """预测阶段1（高增长期）的FCFF"""
        fcf_list = []
        for t in range(1, years + 1):
            fcf = base_fcff * ((1 + growth_stage1) ** t)
            fcf_list.append(fcf)
        return fcf_list

    # ========================================================================
    # DCF 计算
    # ========================================================================

    def terminal_value_gordon(
        self,
        final_fcf: float,
        perpetuity_g: float,
        wacc: float,
    ) -> float:
        """Gordon增长模型计算终值"""
        if wacc <= perpetuity_g:
            perpetuity_g = wacc - 0.01  # 防止除零或负数
        return final_fcf * (1 + perpetuity_g) / (wacc - perpetuity_g)

    def calculate(
        self,
        financial_data: dict,
        growth_stage1: float = None,
        perpetuity_g: float = None,
        projection_years: int = 5,
    ) -> DCFResult:
        """
        执行完整DCF估值

        流程：
        1. 计算WACC
        2. 计算历史FCFF
        3. 预测未来FCFF（阶段1）
        4. 计算终值（阶段2）
        5. 折现所有现金流
        6. 计算每股公允价值
        """
        # 1. WACC
        wacc_params = self.estimate_wacc(financial_data)
        wacc = wacc_params["wacc"]

        # 2. 历史FCFF
        base_fcff = self.calculate_historical_fcff(financial_data)
        if not base_fcff:
            return DCFResult(
                current_price=self._safe_float(self._extract(
                    financial_data, ["close", "price"]
                )) or 0,
                valuation_rating="数据不足",
                confidence="无法计算FCFF",
            )

        # 3. 增长率
        if growth_stage1 is None:
            # 从历史净利润CAGR估算
            growth_stage1 = self._estimate_growth(financial_data)
        if perpetuity_g is None:
            perpetuity_g = self.DEFAULT_PERPETUITY_G

        # 4. 预测期FCFF
        projected_fcf = self.forecast_fcf(base_fcff, growth_stage1, projection_years)

        # 5. 终值
        tv = self.terminal_value_gordon(projected_fcf[-1], perpetuity_g, wacc)

        # 6. 折现
        pv_fcf = []
        total_pv = 0.0
        for t, fcf in enumerate(projected_fcf, 1):
            pv = fcf / ((1 + wacc) ** t)
            pv_fcf.append(pv)
            total_pv += pv

        pv_terminal = tv / ((1 + wacc) ** projection_years)
        total_pv += pv_terminal

        # 单位转换：FCFF是万元→亿元
        ev = total_pv / 1e4  # 转亿元

        # 7. 每股价值
        net_debt_val = self._calculate_net_debt(financial_data)
        equity_val = ev - net_debt_val

        shares = self._safe_float(self._extract(financial_data, [
            "total_share", "total_share_y",
        ]))
        # total_share可能是万股，转为亿股
        if shares and shares > 1000:
            shares = shares / 1e4  # 万股→亿股

        if shares and shares > 0:
            fair_price = equity_val / shares
        else:
            fair_price = 0

        current_price = self._safe_float(self._extract(financial_data, [
            "close", "price",
        ])) or 0

        upside = ((fair_price - current_price) / current_price * 100) if current_price > 0 else 0

        # 8. 估值评级
        if upside > 30:
            rating = "显著低估"
            confidence = "安全边际充足"
        elif upside > 10:
            rating = "偏低"
            confidence = "有一定安全边际"
        elif upside > -10:
            rating = "合理估值"
            confidence = "估值基本合理"
        elif upside > -30:
            rating = "偏高"
            confidence = "估值偏高，注意风险"
        else:
            rating = "显著高估"
            confidence = "估值泡沫风险较大"

        # 9. 敏感性分析
        sens = self.sensitivity_matrix(base_fcff, wacc, growth_stage1,
                                       perpetuity_g, projection_years, shares or 1)

        # 10. 情景分析
        scenarios = self.scenario_analysis(financial_data, base_fcff, wacc, shares or 1)

        return DCFResult(
            enterprise_value=round(ev, 2),
            equity_value=round(equity_val, 2),
            fair_price=round(fair_price, 2),
            current_price=current_price,
            upside_pct=round(upside, 1),
            wacc=round(wacc * 100, 2),
            terminal_value_pct=round(pv_terminal / total_pv * 100, 1),
            fcf_growth_stage1=round(growth_stage1 * 100, 1),
            perpetuity_growth=round(perpetuity_g * 100, 1),
            projected_fcf=[round(f, 2) for f in projected_fcf],
            pv_fcf=[round(p, 2) for p in pv_fcf],
            terminal_value=round(tv / 1e4, 2),
            net_debt=round(net_debt_val, 2),
            total_shares=round(shares, 2) if shares else 0,
            risk_free_rate=round(self.rf * 100, 2),
            beta=wacc_params["beta"],
            market_premium=round(self.mrp * 100, 2),
            cost_of_equity=round(wacc_params["cost_of_equity"] * 100, 2),
            cost_of_debt=round(wacc_params["cost_of_debt"] * 100, 2),
            tax_rate=round(self.TAX_RATE * 100, 1),
            debt_ratio=round(wacc_params["debt_ratio"] * 100, 1),
            scenarios=scenarios,
            sensitivity_matrix=sens,
            valuation_rating=rating,
            confidence=confidence,
        )

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _estimate_growth(self, financial_data: dict) -> float:
        """从历史数据估算增长率的默认值"""
        np_vals = []
        if "income" in financial_data:
            income = financial_data["income"]
            if hasattr(income, 'iloc') and len(income) >= 2:
                for i in range(min(5, len(income))):
                    v = self._safe_float(self._extract_row(
                        income.iloc[i],
                        ["net_profit", "n_income_attr_p", "净利润"]
                    ))
                    if v:
                        np_vals.append(v)

        if len(np_vals) >= 2:
            cagr = (np_vals[0] / np_vals[-1]) ** (1 / (len(np_vals) - 1)) - 1
            return max(0.03, min(0.25, cagr))  # 限制在3%-25%

        return 0.08  # 默认8%

    def sensitivity_matrix(
        self,
        base_fcff: float,
        base_wacc: float,
        growth_s1: float,
        perpetuity_g: float,
        years: int,
        shares: float,
    ) -> dict:
        """WACC ±2% × 永续增长率 ±1% 的敏感性矩阵"""
        matrix = {}
        for wacc_delta in [-0.02, -0.01, 0, 0.01, 0.02]:
            wacc_val = base_wacc + wacc_delta
            if wacc_val <= 0.02:
                continue
            for g_delta in [-0.01, -0.005, 0, 0.005, 0.01]:
                g_val = perpetuity_g + g_delta
                if g_val <= 0 or g_val >= wacc_val:
                    continue
                fcf = self.forecast_fcf(base_fcff, growth_s1, years)
                tv = self.terminal_value_gordon(fcf[-1], g_val, wacc_val)
                pv = sum(fcf[t] / (1 + wacc_val) ** (t + 1) for t in range(years))
                pv += tv / (1 + wacc_val) ** years
                price = (pv / 1e4 / shares) if shares > 0 else 0
                key = f"WACC={(wacc_val*100):.1f}%_g={(g_val*100):.1f}%"
                matrix[key] = round(price, 2)

        return matrix

    def scenario_analysis(
        self,
        financial_data: dict,
        base_fcff: float,
        base_wacc: float,
        shares: float,
    ) -> dict:
        """乐观/基准/悲观三情景DCF"""
        scenarios = {}

        for name, growth_mult, g_mult in [
            ("乐观", 1.3, 1.5),
            ("基准", 1.0, 1.0),
            ("悲观", 0.7, 0.5),
        ]:
            g = self._estimate_growth(financial_data)
            fcf = self.forecast_fcf(base_fcff, g * growth_mult)
            tv = self.terminal_value_gordon(
                fcf[-1], self.DEFAULT_PERPETUITY_G * g_mult, base_wacc
            )
            pv = sum(fcf[t] / (1 + base_wacc) ** (t + 1) for t in range(5))
            pv += tv / (1 + base_wacc) ** 5
            price = (pv / 1e4 / shares) if shares > 0 else 0
            scenarios[name] = {
                "fair_price": round(price, 2),
                "growth_rate": round(g * growth_mult * 100, 1),
                "perpetuity_g": round(self.DEFAULT_PERPETUITY_G * g_mult * 100, 1),
            }

        return scenarios

    def _calculate_net_debt(self, financial_data: dict) -> float:
        """计算净负债（亿元）"""
        cash = self._safe_float(self._extract(financial_data, [
            "money_cap", "现金", "cash",
        ])) or 0
        ib_debt = self._safe_float(self._extract(financial_data, [
            "interest_bearing_debt",
        ])) or 0
        # 若无法获取精确有息负债，从财报科目估算
        if not ib_debt:
            short_borrowing = self._safe_float(self._extract(financial_data, [
                "short_borrowing", "短期借款",
            ])) or 0
            long_borrowing = self._safe_float(self._extract(financial_data, [
                "long_borrowing", "长期借款",
            ])) or 0
            bonds_payable = self._safe_float(self._extract(financial_data, [
                "bonds_payable", "应付债券",
            ])) or 0
            ib_debt = short_borrowing + long_borrowing + bonds_payable
            if ib_debt == 0:
                total_liab = self._safe_float(self._extract(financial_data, [
                    "total_liab", "负债合计",
                ])) or 0
                ib_debt = total_liab * 0.5  # 最后降级：用总负债的50%近似
        return (ib_debt - cash) / 1e4  # 转亿元

    @staticmethod
    def _extract(data: dict, keys: list[str]) -> Any:
        """从字典中按优先级提取值"""
        for key in keys:
            if key in data:
                return data[key]
        return None

    @staticmethod
    def _extract_row(row, keys: list[str]) -> Any:
        """从DataFrame行中按优先级提取值"""
        for key in keys:
            if hasattr(row, 'get') and row.get(key):
                return row[key]
            if key in row.index:
                return row[key]
        return None

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        """安全转换为float"""
        if val is None:
            return None
        try:
            v = float(val)
            if np.isnan(v) or np.isinf(v):
                return None
            return v
        except (ValueError, TypeError):
            return None

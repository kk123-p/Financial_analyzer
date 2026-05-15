"""
Tushare 扩展数据分析器 - 审计意见、财务指标、主营业务构成
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..logging_config import get_logger

import unicodedata

logger = get_logger(__name__)


def _cjk_ljust(s, width):
    s = str(s)
    cjk_count = sum(1 for c in s if unicodedata.east_asian_width(c) in ('F', 'W'))
    return s + ' ' * max(0, width - len(s) - cjk_count)


def _cjk_rjust(s, width):
    s = str(s)
    cjk_count = sum(1 for c in s if unicodedata.east_asian_width(c) in ('F', 'W'))
    return ' ' * max(0, width - len(s) - cjk_count) + s


class TushareDataAnalyzer(BaseAnalyzer):
    """Tushare 扩展数据分析器"""

    def __init__(self, data: dict, stock_code: str, data_adapter, cache_manager):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    def _get_basic_info(self) -> dict:
        info = {}
        stock_basic = self.data.get("stock_basic")
        if stock_basic is not None and not stock_basic.empty:
            sb = stock_basic.iloc[0]
            info["name"] = sb.get("name", "N/A")
            info["industry"] = sb.get("industry", "N/A")
        return info

    def _fetch_or_get(self, data_type: str, years: int = 5):
        """获取数据（优先从 self.data 取，没有再调适配器）"""
        df = self.data.get(data_type)
        if df is not None and not df.empty:
            return df
        df, err = self._fetch_data(data_type, years)
        if df is not None and not df.empty:
            self.data[data_type] = df  # 缓存到 self.data
            return df
        return None

    # ========================================================================
    # 1. 财务审计意见
    # ========================================================================

    def analyze_fina_audit(self) -> str:
        """财务审计意见分析报告"""
        result = RF.header("财务审计意见")

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        df = self._fetch_or_get("fina_audit")
        if df is None or df.empty:
            result += "  未获取到审计意见数据（需要 Tushare 权限）\n"
            result += RF.footer()
            return result

        result += f"  数据来源: Tushare fina_audit\n"
        result += f"  记录数: {len(df)} 条\n\n"

        # 表头
        result += RF.section("历年审计意见")
        result += f"  {_cjk_ljust('报告期', 12)}{_cjk_ljust('审计意见', 20)}{_cjk_ljust('审计师', 16)}{_cjk_ljust('事务所', 20)}\n"
        result += f"  {'─' * 70}\n"

        # 审计意见类型判断
        opinion_keywords = {
            "标准无保留": "🟢",
            "无保留": "🟢",
            "带强调事项段": "🟡",
            "保留": "🔴",
            "否定": "⛔",
            "无法表示": "⛔",
        }

        for _, row in df.head(10).iterrows():
            end_date = str(row.get("end_date", "N/A"))
            opinion = str(row.get("audit_opinion", row.get("audit_result", "N/A")))
            auditor = str(row.get("audit_agency", row.get("accounting_firm", "N/A")))
            sign = str(row.get("signature", "N/A"))

            # 审计意见着色
            icon = "⚪"
            for kw, ic in opinion_keywords.items():
                if kw in opinion:
                    icon = ic
                    break

            result += f"  {_cjk_ljust(end_date, 12)}{icon} {_cjk_ljust(opinion, 18)}{_cjk_ljust(sign, 16)}{_cjk_ljust(auditor, 20)}\n"

        # 分析
        result += f"\n{RF.section('审计意见分析')}\n"
        opinions = df["audit_opinion"].dropna().tolist() if "audit_opinion" in df.columns else []
        if opinions:
            latest = str(opinions[0])
            result += f"  最新审计意见: {latest}\n"

            non_standard = [o for o in opinions if "标准" not in str(o) and "无保留" not in str(o)]
            if non_standard:
                result += f"  ⚠️ 历史存在非标准审计意见: {len(non_standard)} 次\n"
                for o in non_standard[:3]:
                    result += f"    · {o}\n"
            else:
                result += f"  ✓ 历史审计意见均为标准无保留\n"

        result += RF.footer()
        return result

    # ========================================================================
    # 2. 财务指标数据
    # ========================================================================

    def analyze_financial_indicators(self) -> str:
        """财务指标数据展示报告"""
        result = RF.header("财务指标数据")

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        df = self._fetch_or_get("financial")
        if df is None or df.empty:
            result += "  未获取到财务指标数据\n"
            result += RF.footer()
            return result

        result += f"  数据来源: Tushare fina_indicator\n"
        result += f"  记录数: {len(df)} 条\n\n"

        # 选取关键指标列
        key_cols = {
            "end_date": "报告期",
            "roe": "ROE(%)",
            "roe_dt": "扣非ROE(%)",
            "grossprofit_margin": "毛利率(%)",
            "netprofit_margin": "净利率(%)",
            "debt_to_assets": "资产负债率(%)",
            "current_ratio": "流动比率",
            "quick_ratio": "速动比率",
            "op_yoy": "营收同比(%)",
            "dt_netprofit_yoy": "扣非净利同比(%)",
            "ocfps": "每股经营现金流",
            "eps": "基本EPS",
            "bps": "每股净资产",
            "cfps": "每股现金流",
        }

        # 过滤存在的列
        available = {k: v for k, v in key_cols.items() if k in df.columns}

        # 表头
        result += RF.section("核心财务指标（近5年）\n")
        header = "  "
        for k, label in available.items():
            header += _cjk_rjust(label, 12)
        result += header + "\n"
        result += f"  {'─' * (12 * len(available))}\n"

        # 数据行
        for _, row in df.head(5).iterrows():
            line = "  "
            for k in available:
                val = row.get(k)
                if val is None or (isinstance(val, float) and str(val) == "nan"):
                    line += _cjk_rjust("N/A", 12)
                elif k == "end_date":
                    line += _cjk_rjust(str(val), 12)
                else:
                    line += _cjk_rjust(f"{val:.2f}", 12)
            result += line + "\n"

        result += f"\n  * 数据来源于 Tushare fina_indicator 接口\n"

        result += RF.footer()
        return result

    # ========================================================================
    # 3. 主营业务构成
    # ========================================================================

    def analyze_main_business(self) -> str:
        """主营业务构成分析报告"""
        result = RF.header("主营业务构成")

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        df = self._fetch_or_get("mainbz")
        if df is None or df.empty:
            result += "  未获取到主营业务构成数据（需要 Tushare 权限）\n"
            result += RF.footer()
            return result

        result += f"  数据来源: Tushare mainbiz（按产品分类）\n"
        result += f"  记录数: {len(df)} 条\n\n"

        # 按报告期分组
        if "end_date" in df.columns:
            periods = df["end_date"].unique()[:3]  # 最近3期

            for period in periods:
                period_df = df[df["end_date"] == period]
                result += RF.section(f"报告期: {period}")

                # 按收入占比排序
                sort_col = None
                for col in ["mainbz_income_ratio", "mainbz_ratio"]:
                    if col in period_df.columns:
                        sort_col = col
                        break

                if sort_col:
                    period_df = period_df.sort_values(sort_col, ascending=False)

                # 表头
                result += f"  {_cjk_ljust('业务名称', 20)}"
                if "mainbz_income" in period_df.columns:
                    result += _cjk_rjust("收入(亿)", 12)
                if "mainbz_income_ratio" in period_df.columns:
                    result += _cjk_rjust("收入占比", 10)
                if "mainbz_profit" in period_df.columns:
                    result += _cjk_rjust("利润(亿)", 12)
                if "mainbz_profit_ratio" in period_df.columns:
                    result += _cjk_rjust("利润占比", 10)
                if "industry" in period_df.columns:
                    result += _cjk_ljust("行业", 16)
                result += "\n"
                result += f"  {'─' * 70}\n"

                for _, row in period_df.head(10).iterrows():
                    bz_name = str(row.get("bz_name", row.get("mainbz", "N/A")))
                    if len(bz_name) > 18:
                        bz_name = bz_name[:18] + ".."

                    line = f"  {_cjk_ljust(bz_name, 20)}"
                    if "mainbz_income" in period_df.columns:
                        inc = row.get("mainbz_income")
                        line += _cjk_rjust(f"{inc/1e8:.2f}" if inc else "N/A", 12)
                    if "mainbz_income_ratio" in period_df.columns:
                        ratio = row.get("mainbz_income_ratio")
                        line += _cjk_rjust(f"{ratio:.1f}%" if ratio else "N/A", 10)
                    if "mainbz_profit" in period_df.columns:
                        pft = row.get("mainbz_profit")
                        line += _cjk_rjust(f"{pft/1e8:.2f}" if pft else "N/A", 12)
                    if "mainbz_profit_ratio" in period_df.columns:
                        ratio = row.get("mainbz_profit_ratio")
                        line += _cjk_rjust(f"{ratio:.1f}%" if ratio else "N/A", 10)
                    if "industry" in period_df.columns:
                        ind = str(row.get("industry", "N/A"))
                        line += _cjk_ljust(ind[:14], 16)
                    result += line + "\n"

                result += "\n"

        result += RF.footer()
        return result

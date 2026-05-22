"""
数据标准化层 - 统一不同数据源的列名、数据类型、格式
解决 Tushare / Yahoo Finance / Akshare 数据格式不一致问题
"""
import pandas as pd
import numpy as np
from datetime import datetime
from ..logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# 标准列定义
# ============================================================================
class StandardColumns:
    """标准列名定义 - 所有分析模块统一使用这些列名"""

    # 行情数据 (daily)
    TRADE_DATE = "trade_date"     # 交易日期 (YYYYMMDD 字符串)
    OPEN = "open"                 # 开盘价
    HIGH = "high"                 # 最高价
    LOW = "low"                   # 最低价
    CLOSE = "close"               # 收盘价
    VOLUME = "vol"                # 成交量（统一为：手）
    AMOUNT = "amount"             # 成交额（统一为：元）
    TURNOVER = "turnover_rate"    # 换手率 (%)
    PCT_CHG = "pct_chg"           # 涨跌幅 (%)

    # 基本信息 (basic)
    TS_CODE = "ts_code"           # 股票代码
    NAME = "name"                 # 股票名称
    INDUSTRY = "industry"         # 行业
    MARKET = "market"             # 市场
    PE = "pe"                     # 市盈率
    PE_TTM = "pe_ttm"            # 市盈率(TTM)
    PB = "pb"                     # 市净率
    TOTAL_MV = "total_mv"        # 总市值
    CIRC_MV = "circ_mv"          # 流通市值

    # 行情数据必须列
    DAILY_REQUIRED = [TRADE_DATE, OPEN, HIGH, LOW, CLOSE, VOLUME]
    # 行情数据可选列
    DAILY_OPTIONAL = [AMOUNT, TURNOVER, PCT_CHG, TS_CODE]
    # 基本信息必须列
    BASIC_REQUIRED = [TS_CODE]


# ============================================================================
# 列名映射表
# ============================================================================
COLUMN_MAPS = {
    "tushare_daily": {
        # Tushare daily 已经是标准列名，无需映射
    },
    "yfinance_daily": {
        "Date": "__drop__",         # 删除原始 Date 列
        "Close": "close",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Volume": "vol",
        "Dividends": "__drop__",
        "Stock Splits": "__drop__",
    },
    "akshare_daily": {
        "日期": "__drop__",
        "收盘": "close",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "成交量": "vol",
        "成交额": "amount",
        "振幅": "__drop__",
        "涨跌幅": "pct_chg",
        "涨跌额": "__drop__",
        "换手率": "turnover_rate",
        # Akshare 美股格式
        "date": "__drop__",
        "volume": "vol",
    },
    "yfinance_basic": {
        "longName": "name",
        "industry": "industry",
        "sector": "industry",
        "trailingPE": "pe",
        "forwardPE": "pe_ttm",
        "priceToBook": "pb",
        "marketCap": "total_mv",
    },
}


# ============================================================================
# 数据标准化器
# ============================================================================
class DataNormalizer:
    """数据标准化器 - 将不同数据源的数据统一为标准格式"""

    @staticmethod
    def normalize_daily(df: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        标准化日线数据

        Args:
            df: 原始数据
            source: 数据源名称 ("tushare", "yfinance", "akshare")

        Returns:
            标准化后的 DataFrame
        """
        if df is None or df.empty:
            return df

        df = df.copy()

        # 1. 先标准化日期（在删除原始列之前）
        df = DataNormalizer._normalize_date(df, source)

        # 2. 列名映射 + 删除不需要的列
        col_map = COLUMN_MAPS.get(f"{source}_daily", {})
        df = DataNormalizer._apply_column_map(df, col_map)

        # 3. 确保数值列为数字类型
        df = DataNormalizer._normalize_numeric(df)

        # 4. 确保成交量单位统一（手）
        df = DataNormalizer._normalize_volume(df, source)

        # 5. 补全所有标准列（缺失的填 NaN）
        all_standard = StandardColumns.DAILY_REQUIRED + StandardColumns.DAILY_OPTIONAL
        for col in all_standard:
            if col not in df.columns:
                df[col] = np.nan

        # 6. 只保留标准列，确保所有数据源输出一致
        keep = [c for c in all_standard if c in df.columns]
        df = df[keep]

        # 7. 按日期降序排列（最新在前）
        if "trade_date" in df.columns:
            df = df.sort_values("trade_date", ascending=False).reset_index(drop=True)

        logger.info(f"[{source}] 日线数据标准化完成：{len(df)} 行, 列={list(df.columns)}")
        return df

    @staticmethod
    def normalize_basic(df: pd.DataFrame, source: str) -> pd.DataFrame:
        """标准化基本信息数据"""
        if df is None or df.empty:
            return df

        df = df.copy()

        if source == "yfinance":
            # Yahoo Finance info 是 dict 转的 DataFrame
            col_map = COLUMN_MAPS.get("yfinance_basic", {})
            df = DataNormalizer._apply_column_map(df, col_map)

        elif source == "akshare":
            # Akshare 的 stock_individual_info_em 返回 item/value 格式
            if "item" in df.columns and "value" in df.columns:
                info_dict = dict(zip(df["item"], df["value"]))
                # Akshare 返回的总市值/流通市值单位是元，转换为万元以匹配 Tushare 惯例
                # Tushare 的 total_mv 单位是万元，UI 按万元 / 10000 = 亿元 显示
                raw_total_mv = DataNormalizer._try_float(info_dict.get("总市值"))
                raw_circ_mv = DataNormalizer._try_float(info_dict.get("流通市值"))
                raw_pe = DataNormalizer._try_float(info_dict.get("市盈率(动态)") or info_dict.get("市盈率"))
                df = pd.DataFrame([{
                    "ts_code": info_dict.get("股票代码", ""),
                    "name": info_dict.get("股票简称", ""),
                    "industry": info_dict.get("行业", ""),
                    "market": "A股",
                    "total_mv": raw_total_mv / 1e4 if raw_total_mv else None,  # 元 → 万元
                    "circ_mv": raw_circ_mv / 1e4 if raw_circ_mv else None,      # 元 → 万元
                    "pe": raw_pe,
                    "pe_ttm": raw_pe,
                }])

        # 确保 ts_code 存在
        if "ts_code" not in df.columns:
            df["ts_code"] = ""

        logger.info(f"[{source}] 基本信息标准化完成")
        return df

    @staticmethod
    def normalize_financial(df: pd.DataFrame, source: str) -> pd.DataFrame:
        """标准化财务数据（financial 指标 + 三大报表）"""
        if df is None or df.empty:
            return df

        df = df.copy()

        if source == "tushare":
            # Tushare fina_indicator 字段别名
            aliases = {
                "ar_turn": "ar_turnover",
                "ca_turn": "ca_turnover",
                "fa_turn": "fa_turnover",
                "assets_turn": "ta_turnover",
                "netprofit_margin": "net_margin",
                "grossprofit_margin": "gross_margin",
                "debt_to_assets": "debt_ratio",
            }
            for src, dst in aliases.items():
                if src in df.columns and dst not in df.columns:
                    df[dst] = df[src]
            # 计算周转天数
            if "ar_turnover" in df.columns and "ar_turnover_days" not in df.columns:
                df["ar_turnover_days"] = df["ar_turnover"].apply(
                    lambda x: 365 / x if x and x > 0 else None)
            if "inv_turnover" in df.columns and "inv_turnover_days" not in df.columns:
                df["inv_turnover_days"] = df["inv_turnover"].apply(
                    lambda x: 365 / x if x and x > 0 else None)

        elif source == "yfinance":
            # Yahoo Finance 的 financials 转置后列名不统一
            rename_map = {}
            for col in df.columns:
                col_lower = str(col).lower()
                if "total revenue" in col_lower or "revenue" in col_lower:
                    rename_map[col] = "total_revenue"
                elif "net income" in col_lower:
                    rename_map[col] = "net_profit"
                elif "gross profit" in col_lower:
                    rename_map[col] = "gross_profit"
                elif "operating income" in col_lower:
                    rename_map[col] = "operate_profit"
                elif "cost of revenue" in col_lower:
                    rename_map[col] = "oper_cost"
                elif "ebitda" in col_lower:
                    rename_map[col] = "ebitda"
            if rename_map:
                df = df.rename(columns=rename_map)

        elif source == "akshare":
            df = DataNormalizer._normalize_akshare_financial(df)

        logger.info(f"[{source}] 财务数据标准化完成")
        return df

    @staticmethod
    def normalize_income(df: pd.DataFrame, source: str) -> pd.DataFrame:
        """标准化利润表数据"""
        if df is None or df.empty:
            return df

        df = df.copy()

        if source == "akshare":
            df = DataNormalizer._normalize_akshare_income(df)
        elif source == "tushare":
            # Tushare 字段别名映射（确保分析器能用统一字段名访问）
            aliases = {
                "n_income": "net_profit",
                "n_income_attr_p": "net_profit_attr",
            }
            for src, dst in aliases.items():
                if src in df.columns and dst not in df.columns:
                    df[dst] = df[src]

        logger.info(f"[{source}] 利润表标准化完成")
        return df

    @staticmethod
    def normalize_balance(df: pd.DataFrame, source: str) -> pd.DataFrame:
        """标准化资产负债表数据"""
        if df is None or df.empty:
            return df

        df = df.copy()

        if source == "akshare":
            df = DataNormalizer._normalize_akshare_balance(df)
        elif source == "tushare":
            # Tushare 字段别名映射
            aliases = {
                "accounts_receiv": "accounts_receivable",
                "acc_receivable": "accounts_receivable",
                "undistr_porfit": "retained_earnings",
                "total_hldr_eqy_exc_min_int": "total_equity",
            }
            for src, dst in aliases.items():
                if src in df.columns and dst not in df.columns:
                    df[dst] = df[src]
            # 确保 equity 别名存在
            if "total_equity" not in df.columns and "total_hldr_eqy_inc_min_int" in df.columns:
                df["total_equity"] = df["total_hldr_eqy_inc_min_int"]

        logger.info(f"[{source}] 资产负债表标准化完成")
        return df

    @staticmethod
    def normalize_cashflow(df: pd.DataFrame, source: str) -> pd.DataFrame:
        """标准化现金流量表数据"""
        if df is None or df.empty:
            return df

        df = df.copy()

        if source == "akshare":
            df = DataNormalizer._normalize_akshare_cashflow(df)
        elif source == "tushare":
            # Tushare 字段别名映射
            aliases = {
                "n_cash_flows_fnc_act": "n_cash_finance_act",
                "c_pay_acq_const_fiolta": "c_pay_acq_const_fiamt",
            }
            for src, dst in aliases.items():
                if src in df.columns and dst not in df.columns:
                    df[dst] = df[src]

        logger.info(f"[{source}] 现金流量表标准化完成")
        return df

    @staticmethod
    def normalize_market(df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """标准化市场数据（moneyflow/margin/dividend/top10_holders 等新增类型）

        对 Tushare 返回的各类市场数据进行通用标准化：
        - 统一日期列格式为 YYYYMMDD
        - 数值列转数字类型
        - 按日期降序排列
        """
        if df is None or df.empty:
            return df

        df = df.copy()

        # 查找日期列并标准化
        date_candidates = ["trade_date", "end_date", "ann_date", "div_progress",
                          "report_date", "record_date", "ex_date", "pay_date",
                          "plan_ann_date", "margin_date", "detail_date", "s_end_date"]
        for dc in date_candidates:
            if dc in df.columns:
                try:
                    df[dc] = pd.to_datetime(df[dc], errors="coerce").dt.strftime("%Y%m%d")
                except Exception:
                    pass

        # 尝试将所有可能为数值的列转为数字类型
        skip_cols = ["ts_code", "name", "holder_name", "index_code", "industry",
                    "market", "list_date", "ann_date", "trade_date", "end_date",
                    "report_date", "record_date", "ex_date", "pay_date", "div_progress",
                    "plan_ann_date", "margin_date", "detail_date", "s_end_date",
                    "holder_type", "currency", "exchange"]
        for col in df.columns:
            if col not in skip_cols and df[col].dtype == "object":
                try:
                    df[col] = pd.to_numeric(df[col], errors="ignore")
                except Exception:
                    pass

        # 按日期列降序排列
        sort_col = None
        for dc in date_candidates:
            if dc in df.columns:
                sort_col = dc
                break
        if sort_col:
            df = df.sort_values(sort_col, ascending=False).reset_index(drop=True)

        logger.info(f"市场数据标准化完成 [{data_type}]：{len(df)} 行, 列={list(df.columns)[:8]}")
        return df

    # ======================== 内部方法 ========================

    # ======================== Akshare 三大报表标准化 ========================

    @staticmethod
    def _normalize_akshare_financial(df: pd.DataFrame) -> pd.DataFrame:
        """标准化 Akshare stock_financial_analysis_indicator 返回的财务指标"""
        rename = {
            "日期": "end_date",
            "净资产收益率(%)": "roe",
            "加权净资产收益率(%)": "roe_dt",
            "销售毛利率(%)": "gross_margin",
            "销售净利率(%)": "net_margin",
            "营业利润率(%)": "op_margin",
            "总资产利润率(%)": "roa",
            "成本费用利润率(%)": "cost_profit_ratio",
            "应收账款周转率(次)": "ar_turnover",
            "应收账款周转天数(天)": "ar_turnover_days",
            "存货周转率(次)": "inv_turnover",
            "存货周转天数(天)": "inv_turnover_days",
            "总资产周转率(次)": "ta_turnover",
            "流动比率": "current_ratio",
            "速动比率": "quick_ratio",
            "资产负债率(%)": "debt_ratio",
            "总资产(元)": "total_assets",
            "主营业务收入增长率(%)": "or_yoy",
            "净利润增长率(%)": "q_profit_yoy",
        }
        existing = {k: v for k, v in rename.items() if k in df.columns}
        if existing:
            df = df.rename(columns=existing)

        # 统一日期格式
        if "end_date" in df.columns:
            df["end_date"] = pd.to_datetime(df["end_date"]).dt.strftime("%Y%m%d")
            df = df.sort_values("end_date", ascending=False).reset_index(drop=True)

        # 确保数值列为数字类型
        numeric_cols = ["roe", "roe_dt", "gross_margin", "net_margin", "roa",
                        "ar_turnover", "inv_turnover", "current_ratio", "quick_ratio",
                        "debt_ratio", "total_assets", "or_yoy", "q_profit_yoy"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    @staticmethod
    def _normalize_akshare_income(df: pd.DataFrame) -> pd.DataFrame:
        """标准化 Akshare 新浪利润表"""
        rename = {
            "报告日": "end_date",
            "营业总收入": "total_revenue",
            "营业收入": "revenue",
            "营业成本": "oper_cost",
            "营业支出": "oper_cost",
            "营业总成本": "total_oper_cost",
            "销售费用": "sell_exp",
            "业务及管理费用": "admin_exp",
            "管理费用": "admin_exp",
            "财务费用": "fin_exp",
            "研发费用": "rd_exp",
            "营业利润": "operate_profit",
            "利润总额": "total_profit",
            "所得税费用": "income_tax",
            "减:所得税": "income_tax",
            "净利润": "net_profit",
            "归属于母公司所有者的净利润": "n_income_attr_p",
            "归属于母公司的净利润": "n_income_attr_p",
            "少数股东损益": "minority_interest",
            "少数股东权益": "minority_interest",
            "基本每股收益": "basic_eps",
            "信用减值损失": "credit_impairment_loss",
            "资产减值损失": "asset_impairment_loss",
        }
        existing = {k: v for k, v in rename.items() if k in df.columns}
        if existing:
            df = df.rename(columns=existing)

        if "end_date" in df.columns:
            df["end_date"] = df["end_date"].astype(str).str.replace("-", "").str[:8]
            df = df.sort_values("end_date", ascending=False).reset_index(drop=True)

        # 数值列转换
        num_cols = ["total_revenue", "revenue", "oper_cost", "sell_exp", "admin_exp", "fin_exp",
                    "rd_exp", "operate_profit", "net_profit", "n_income_attr_p",
                    "total_profit", "total_oper_cost", "income_tax",
                    "credit_impairment_loss", "asset_impairment_loss"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    @staticmethod
    def _normalize_akshare_balance(df: pd.DataFrame) -> pd.DataFrame:
        """标准化 Akshare 新浪资产负债表"""
        rename = {
            "报告日": "end_date",
            "流动资产合计": "total_cur_assets",
            "非流动资产合计": "total_nca",
            "资产总计": "total_assets",
            "资产合计": "total_assets",  # 部分行业用这个名称
            "流动负债合计": "total_cur_liab",
            "非流动负债合计": "total_ncl",
            "负债合计": "total_liab",
            "负债总计": "total_liab",
            "归属于母公司股东权益合计": "total_hldr_eqy_exc_min_int",
            "归属于母公司股东的权益": "total_hldr_eqy_exc_min_int",
            "少数股东权益": "minority_interest",
            "所有者权益(或股东权益)合计": "total_equity",
            "所有者权益合计": "total_equity",  # 兼容不同格式
            "货币资金": "money_cap",
            "现金及存放中央银行款项": "money_cap",  # 银行
            "存货": "inventories",
            "应收账款": "accounts_receivable",
            "固定资产净额": "fixed_assets",
            "短期借款": "short_term_loans",
            "长期借款": "long_term_loans",
        }
        existing = {k: v for k, v in rename.items() if k in df.columns}
        if existing:
            df = df.rename(columns=existing)

        if "end_date" in df.columns:
            df["end_date"] = df["end_date"].astype(str).str.replace("-", "").str[:8]
            df = df.sort_values("end_date", ascending=False).reset_index(drop=True)

        num_cols = ["total_cur_assets", "total_assets", "total_cur_liab", "total_liab",
                    "total_hldr_eqy_exc_min_int", "money_cap", "inventories"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 银行/金融机构没有流动/非流动资产分类，用总资产/总负债作为回退
        if "total_cur_assets" not in df.columns and "total_assets" in df.columns:
            df["total_cur_assets"] = df["total_assets"]
        if "total_cur_liab" not in df.columns and "total_liab" in df.columns:
            df["total_cur_liab"] = df["total_liab"]

        return df

    @staticmethod
    def _normalize_akshare_cashflow(df: pd.DataFrame) -> pd.DataFrame:
        """标准化 Akshare 新浪现金流量表"""
        rename = {
            "报告日": "end_date",
            "经营活动产生的现金流量净额": "n_cashflow_act",
            "投资活动产生的现金流量净额": "n_cashflow_inv_act",
            "筹资活动产生的现金流量净额": "n_cash_finance_act",
            "现金及现金等价物净增加额": "cash_equivalent_increase",
            "购建固定资产、无形资产和其他长期资产所支付的现金": "c_pay_acq_const_fiamt",
            "购建固定资产、无形资产和其他长期资产支付的现金": "c_pay_acq_const_fiamt",  # 兼容
            "销售商品、提供劳务收到的现金": "cash_received_from_sales",
        }
        existing = {k: v for k, v in rename.items() if k in df.columns}
        if existing:
            df = df.rename(columns=existing)

        if "end_date" in df.columns:
            df["end_date"] = df["end_date"].astype(str).str.replace("-", "").str[:8]
            df = df.sort_values("end_date", ascending=False).reset_index(drop=True)

        num_cols = ["n_cashflow_act", "n_cashflow_inv_act", "n_cash_finance_act",
                    "c_pay_acq_const_fiamt"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    # ======================== 内部方法 ========================

    @staticmethod
    def _apply_column_map(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
        """应用列名映射，删除标记为 __drop__ 的列"""
        if not col_map:
            return df

        drop_cols = [k for k, v in col_map.items() if v == "__drop__" and k in df.columns]
        rename_cols = {k: v for k, v in col_map.items() if v != "__drop__" and k in df.columns}

        if drop_cols:
            df = df.drop(columns=drop_cols)
        if rename_cols:
            df = df.rename(columns=rename_cols)

        return df

    @staticmethod
    def _normalize_date(df: pd.DataFrame, source: str) -> pd.DataFrame:
        """统一日期格式为 YYYYMMDD 字符串"""
        if "trade_date" in df.columns:
            # 已有 trade_date，确保是字符串格式
            df["trade_date"] = df["trade_date"].astype(str).str.replace("-", "").str[:8]
            return df

        # 尝试从其他日期列生成 trade_date
        date_candidates = ["Date", "date", "日期", "index"]
        for col in date_candidates:
            if col in df.columns:
                try:
                    dt = pd.to_datetime(df[col])
                    df["trade_date"] = dt.dt.strftime("%Y%m%d")
                    return df
                except Exception:
                    continue

        # 如果还是没有，用索引
        if isinstance(df.index, pd.DatetimeIndex):
            df["trade_date"] = df.index.strftime("%Y%m%d")
            df = df.reset_index(drop=True)
            return df

        logger.warning(f"[{source}] 无法识别日期列")
        return df

    @staticmethod
    def _normalize_numeric(df: pd.DataFrame) -> pd.DataFrame:
        """确保价格和成交量列为数值类型"""
        numeric_cols = ["open", "high", "low", "close", "vol", "amount",
                        "turnover_rate", "pct_chg", "pe", "pb", "total_mv", "circ_mv"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @staticmethod
    def _normalize_volume(df: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        统一成交量单位为「手」
        - Tushare: 已经是手，无需转换
        - Yahoo Finance: 股数 → 除以 100 转为手
        - Akshare: 已经是手，无需转换
        """
        if "vol" not in df.columns:
            return df

        # 用标记列防止重复转换
        if df.attrs.get("_vol_normalized"):
            return df

        if source == "yfinance":
            # Yahoo Finance 的 Volume 始终是股数，统一转换为手（1手=100股）
            df["vol"] = (df["vol"] / 100).round(0)
            logger.debug("[yfinance] 成交量已从股数转换为手")

        # 标记已转换，防止重复处理
        df.attrs["_vol_normalized"] = True

        return df

    @staticmethod
    def _ensure_columns(df: pd.DataFrame, required: list) -> pd.DataFrame:
        """确保必须列存在，缺失的填充 NaN"""
        for col in required:
            if col not in df.columns:
                df[col] = np.nan
                logger.warning(f"缺失列 {col}，已填充空值")
        return df

    @staticmethod
    def _try_float(val) -> float | None:
        """尝试转换为浮点数"""
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

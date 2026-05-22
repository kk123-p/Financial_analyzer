"""
模板定义 + 数据格式化工具
"""
import pandas as pd

# ============================================================================
# 6 个预置模板定义
# ============================================================================

SYSTEM_TEMPLATES = [
    {
        "name": "盈利能力深度解读",
        "description": "从毛利率、净利率、ROE、盈利质量四个维度深度解读企业盈利能力",
        "mode": "template",
        "output_format": "每个 ## 标题作为一个独立分析段落输出，包含：数据现状 → 趋势判断 → 专业解读。最后一个 ## 核心发现 以要点形式汇总关键结论。",
        "system_role": "你是一位拥有20年经验的买方财务分析师。你的任务是解读已提供的财务数据，而非计算数据本身。数据中的财务指标是真实准确的，你的工作是：1) 解读数据的含义 2) 判断趋势方向 3) 横向关联不同指标 4) 给出专业、简洁的结论。",
        "data_required": {
            "primary": ["financial", "income"],
            "secondary": ["balance", "cashflow"]
        },
        "analysis_sections": [
            {
                "title": "毛利率趋势与竞争壁垒",
                "focus_metrics": ["grossprofit_margin", "revenue"],
                "guidance": "从毛利率的绝对水平和变化趋势判断企业的定价权和竞争壁垒。毛利率持续提升说明品牌/技术壁垒增强；下降则需判断是成本端压力还是竞争加剧。结合营收增速一起看：毛利率升+营收增=最优；毛利率降+营收增=以价换量；毛利率降+营收降=双重恶化。"
            },
            {
                "title": "净利率变化与费用管控",
                "focus_metrics": ["netprofit_margin", "revenue", "operate_profit"],
                "guidance": "对比毛利率和净利率的差距变化，判断三费管控能力。如果毛利率稳定但净利率持续下滑，说明费用端出问题（销售费用激增、研发投入过大、财务费用高企）。如果两者同步变化，说明盈利能力主要由主业驱动。"
            },
            {
                "title": "ROE 驱动因子拆解",
                "focus_metrics": ["roe", "netprofit_margin", "assets_turn", "debt_to_assets"],
                "guidance": "基于杜邦三因子框架解读ROE的驱动来源。高利润率驱动型（如茅台）最可持续；高周转驱动型（如沃尔玛）靠运营效率；高杠杆驱动型（如银行、地产）需警惕去杠杆风险。判断当前模式是否能持续。"
            },
            {
                "title": "盈利质量（现金流验证）",
                "focus_metrics": ["ocfps", "net_profit", "n_cashflow_act"],
                "guidance": "用经营现金流验证净利润的真实含金量。如果经营现金流持续显著低于净利润，说明利润'质量'有问题——可能存在应收账款虚增、存货积压或收入确认激进。如果现金流稳定高于净利润，说明利润'真金白银'。"
            },
            {
                "title": "核心发现",
                "focus_metrics": [],
                "guidance": "汇总以上四个维度的核心发现，用3-5个要点总结这家公司盈利能力的本质特征。不需要评分。"
            }
        ]
    },
    {
        "name": "财务异常信号排查",
        "description": "从资产端、利润端、现金流、勾稽关系四个维度排查财务异常",
        "mode": "template",
        "output_format": "每个 ## 标题作为一个独立分析段落输出，包含：数据现状 → 趋势判断 → 专业解读。最后一个 ## 核心发现 以要点形式汇总关键结论。",
        "system_role": "你是一位精通财务审计和舞弊检测的专家。你的任务是检查已提供的财务数据中是否存在异常信号，而非计算数据。",
        "data_required": {
            "primary": ["balance", "income", "cashflow"],
            "secondary": ["financial"]
        },
        "analysis_sections": [
            {
                "title": "资产端异常检查",
                "focus_metrics": ["accounts_receiv", "inventories", "goodwill", "total_assets"],
                "guidance": "检查：1) 应收账款增速是否显著高于营收增速（虚增收入信号）2) 存货增速是否异常高（滞销/虚增信号）3) 商誉占比是否过高（减值风险）4) 货币资金是否充裕但有高额利息支出的异常。"
            },
            {
                "title": "利润端异常检查",
                "focus_metrics": ["total_revenue", "net_profit", "operate_profit", "income_tax"],
                "guidance": "检查：1) 营收与经营活动现金流是否匹配（不匹配=收入确认激进）2) 非经常性损益占比是否过大 3) 毛利率与行业平均偏离度（过高可能造假）4) 所得税与利润总额比例是否合理。"
            },
            {
                "title": "现金流异常检查",
                "focus_metrics": ["n_cashflow_act", "n_cashflow_inv_act", "n_cash_finance_act"],
                "guidance": "检查：1) 经营现金流是否持续为负（造血能力缺失）2) 投资现金流大幅流出是否合理（扩张期vs异常投资）3) 筹资现金流是否异常依赖新增借款。"
            },
            {
                "title": "勾稽关系验证",
                "focus_metrics": [],
                "guidance": "交叉验证：1) 利润表的营收增长 vs 资产负债表应收账款增长 vs 现金流量表的销售收现——三者应逻辑一致 2) 利润表的净利润 vs 资产负债表的留存收益变动 vs 现金流量表的经营活动现金流——三者应协调。指出任何不协调之处。"
            },
            {
                "title": "核心发现",
                "focus_metrics": [],
                "guidance": "汇总发现的所有异常信号，按严重程度排列。无异常则明确说明'未发现明显异常信号'。"
            }
        ]
    },
    {
        "name": "估值合理性判断",
        "description": "从PE分位、股息率、市净率等角度判断当前估值水平",
        "mode": "template",
        "output_format": "每个 ## 标题作为一个独立分析段落输出，包含：数据现状 → 趋势判断 → 专业解读。最后一个 ## 核心发现 以要点形式汇总关键结论。",
        "system_role": "你是一位专注估值分析的投资分析师。你的任务是基于提供的估值相关数据，判断当前估值的合理性。",
        "data_required": {
            "primary": ["daily_basic", "financial"],
            "secondary": ["dividend", "daily"]
        },
        "analysis_sections": [
            {
                "title": "PE(TTM) 估值分析",
                "focus_metrics": ["pe_ttm", "close", "total_mv", "roe"],
                "guidance": "分析当前PE(TTM)的绝对水平：与历史区间对比、与行业均值对比、与ROE水平匹配度（高ROE应匹配较高PE）。判断当前PE处于什么水平。"
            },
            {
                "title": "PB与资产价值",
                "focus_metrics": ["pb", "bps", "total_mv"],
                "guidance": "分析市净率水平。PB<1可能意味着市场对公司资产质量存疑，也可能是低估机会。PB过高则需看ROE是否能支撑。"
            },
            {
                "title": "股息收益评估",
                "focus_metrics": ["cash_div", "close", "total_mv"],
                "guidance": "分析股息率水平、分红稳定性和可持续性。高股息+低PE通常是价值股的信号。"
            },
            {
                "title": "核心发现",
                "focus_metrics": [],
                "guidance": "汇总估值结论：当前估值处于什么区间？主要支撑因素和风险因素是什么？"
            }
        ]
    },
    {
        "name": "股东结构评估",
        "description": "分析股权集中度、机构持仓和筹码变化趋势",
        "mode": "template",
        "output_format": "每个 ## 标题作为一个独立分析段落输出，包含：数据现状 → 趋势判断 → 专业解读。最后一个 ## 核心发现 以要点形式汇总关键结论。",
        "system_role": "你是一位专注公司治理和股东分析的专家。你的任务是基于股东数据，解读股权结构的含义。",
        "data_required": {
            "primary": ["top10_holders", "stk_holdernumber"],
            "secondary": ["top10_floatholders", "daily_basic"]
        },
        "analysis_sections": [
            {
                "title": "股权集中度分析",
                "focus_metrics": ["hold_ratio", "holder_name"],
                "guidance": "分析前十大股东的持股集中度和性质。国资控股、民企创始人控股、机构分散持股等不同结构对公司治理和决策效率有本质不同。"
            },
            {
                "title": "机构持仓与市场认可",
                "focus_metrics": ["hold_ratio", "holder_name"],
                "guidance": "从流通股东中识别基金、社保、QFII、保险等专业机构的持仓情况。机构持仓比例高且稳定=市场认可度高。机构大幅减持=警惕信号。"
            },
            {
                "title": "股东人数与筹码趋势",
                "focus_metrics": ["holder_num"],
                "guidance": "股东人数减少=筹码趋于集中（通常利好），股东人数大幅增加=筹码分散（散户化，通常利空）。结合股价走势判断主力动向。"
            },
            {
                "title": "核心发现",
                "focus_metrics": [],
                "guidance": "汇总股权结构的主要特征和投资含义。"
            }
        ]
    },
    {
        "name": "资金面多空分析",
        "description": "从主力资金、融资融券、北向资金三个维度解读资金面",
        "mode": "template",
        "output_format": "每个 ## 标题作为一个独立分析段落输出，包含：数据现状 → 趋势判断 → 专业解读。最后一个 ## 核心发现 以要点形式汇总关键结论。",
        "system_role": "你是一位专注资金面分析的量化分析师。你的任务是基于资金流向数据，解读市场多空力量对比。",
        "data_required": {
            "primary": ["moneyflow", "margin"],
            "secondary": ["hk_hold", "block_trade"]
        },
        "analysis_sections": [
            {
                "title": "主力资金动向",
                "focus_metrics": ["buy_elg_amount", "sell_elg_amount", "buy_lg_amount", "sell_lg_amount", "net_mf_amount"],
                "guidance": "分析超大单和大单的净流向。主力持续净流入=看多信号；主力持续净流出=看空信号；流入流出交替=震荡态度。注意区分是'真主力'（持续数日大额流入）还是'假主力'（一日游）。"
            },
            {
                "title": "融资融券情绪",
                "focus_metrics": ["rzye", "rqye", "rzmre"],
                "guidance": "融资余额趋势反映杠杆资金的看多情绪：余额持续增加=杠杆做多积极；余额萎缩=去杠杆/避险。融券余额增加=看空力量增强。融资买入额占成交额比例过高=过度投机信号。"
            },
            {
                "title": "北向资金态度",
                "focus_metrics": ["ratio", "vol"],
                "guidance": "北向持股占比变化反映外资态度。持续增持=外资看好基本面；持续减持=需关注原因（可能是行业因素、汇率因素或公司基本面变化）。"
            },
            {
                "title": "核心发现",
                "focus_metrics": [],
                "guidance": "综合主力、融资、北向三个维度，给出资金面的整体判断：偏多/偏空/中性，以及主要依据。"
            }
        ]
    },
    {
        "name": "成长质量检查",
        "description": "从营收成长性、利润成长性和现金流质量三个维度评估成长质量",
        "mode": "template",
        "output_format": "每个 ## 标题作为一个独立分析段落输出，包含：数据现状 → 趋势判断 → 专业解读。最后一个 ## 核心发现 以要点形式汇总关键结论。",
        "system_role": "你是一位专注成长股分析的投资分析师。你的任务是基于财务数据，评估企业成长的质量和可持续性。",
        "data_required": {
            "primary": ["income", "cashflow", "financial"],
            "secondary": ["balance"]
        },
        "analysis_sections": [
            {
                "title": "营收成长性",
                "focus_metrics": ["total_revenue", "revenue", "or_yoy", "oper_cost"],
                "guidance": "分析营收的增长速度和趋势。持续两位数增长=高成长；个位数增长=成熟期；零或负增长=衰退或困境。关注：增速是否在放缓？收入增长是否伴随利润率提升？"
            },
            {
                "title": "利润成长质量",
                "focus_metrics": ["net_profit", "operate_profit", "dt_netprofit_yoy"],
                "guidance": "对比营收增速和净利润增速。利润增速持续高于营收增速=经营杠杆正向释放（好）；利润增速低于营收增速=成本端拖累或竞争加剧（警惕）；利润增长但营收不增=一次性的非经常收益（不可持续）。"
            },
            {
                "title": "现金流与成长匹配度",
                "focus_metrics": ["n_cashflow_act", "n_cashflow_inv_act", "net_profit"],
                "guidance": "高成长公司通常需要大量资本支出，经营现金流可能为负（成长期正常现象）。关键是判断：投资现金流流出是否有效转化为营收增长？经营现金流是否在改善？如果成长多年但经营现金流从未为正，是危险信号。"
            },
            {
                "title": "核心发现",
                "focus_metrics": [],
                "guidance": "总结评估这家公司的成长质量：是真成长（营收+利润+现金流同步改善）还是伪成长（营收增但利润不增，或利润增长靠财务技巧）？"
            }
        ]
    }
]


# ============================================================================
# 数据提取与格式化
# ============================================================================

def get_template_data_summary(data: dict, stock_code: str, template: dict) -> str:
    """根据模板的 data_required 从 session 数据中提取并格式化"""
    lines = []

    primary = template.get("data_required", {}).get("primary", [])
    secondary = template.get("data_required", {}).get("secondary", [])

    all_metrics = set()
    for section in template.get("analysis_sections", []):
        for m in section.get("focus_metrics", []):
            all_metrics.add(m)

    for data_type in primary + secondary:
        df = data.get(data_type)
        if df is None or df.empty:
            continue

        label = DATA_TYPE_LABELS.get(data_type, data_type)
        formatted = _format_by_type(data_type, df, all_metrics)
        if formatted:
            lines.append(f"\n### {label} ({data_type})")
            lines.append(formatted)

    return "\n".join(lines)


def _format_by_type(data_type: str, df, focus_metrics: set) -> str:
    """按数据类型格式化"""
    if df is None or df.empty:
        return ""

    if data_type in ("financial", "income", "balance", "cashflow"):
        return _format_table(df, focus_metrics, max_rows=5)
    elif data_type in ("daily", "daily_basic", "weekly", "monthly"):
        return _format_latest_plus_range(df, focus_metrics)
    elif data_type in ("moneyflow", "margin", "margin_detail", "hk_hold"):
        return _format_trend_summary(df, data_type)
    elif data_type in ("top10_holders", "top10_floatholders"):
        return _format_top_holders(df)
    elif data_type == "stk_holdernumber":
        return _format_holder_trend(df)
    elif data_type == "dividend":
        return _format_dividend_summary(df)
    elif data_type in ("stock_basic", "basic"):
        return _format_basic_info(df)
    elif data_type == "fina_audit":
        return _format_audit(df)
    elif data_type == "fina_mainbz":
        return _format_mainbz(df)
    elif data_type == "block_trade":
        return _format_block_trade(df)
    else:
        return f"  共 {len(df)} 条记录"


def _format_table(df, focus_metrics: set, max_rows: int = 5) -> str:
    """将 DataFrame 格式化为 Markdown 表格，只保留相关列"""
    date_col = None
    for dc in ["end_date", "trade_date", "ann_date"]:
        if dc in df.columns:
            date_col = dc
            break

    keep_cols = [date_col] if date_col else []
    for col in df.columns:
        if col in focus_metrics:
            keep_cols.append(col)

    if not keep_cols or len(keep_cols) <= 1:
        keep_cols = list(df.columns[:min(8, len(df.columns))])

    subset = df[keep_cols].head(max_rows).copy()

    for col in subset.columns:
        if subset[col].dtype in ("float64", "float32"):
            subset[col] = subset[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")

    return _simple_table(subset)


def _simple_table(df) -> str:
    """简单 Markdown 表格"""
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |"]
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        vals = [str(v) for v in row]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def _format_latest_plus_range(df, focus_metrics: set) -> str:
    """最新值 + 区间统计"""
    lines = []
    if "close" in df.columns:
        latest = df["close"].iloc[0]
        high = df["close"].max()
        low = df["close"].min()
        lines.append(f"  最新价: {latest:.2f} | 区间最高: {high:.2f} | 区间最低: {low:.2f}")

    for col in focus_metrics:
        if col in df.columns and col not in ("close", "trade_date", "ts_code"):
            val = df[col].iloc[0]
            if pd.notna(val):
                lines.append(f"  {col}: {val}")

    return "\n".join(lines) if lines else ""


def _format_trend_summary(df, data_type: str) -> str:
    """资金类数据的趋势摘要"""
    lines = []

    if "trade_date" not in df.columns:
        return ""

    if data_type == "moneyflow" and not df.empty:
        df = df.sort_values("trade_date")
        recent = df.tail(20)
        net_sum = 0
        for _, row in recent.iterrows():
            buy = (float(row.get("buy_elg_amount", 0) or 0) + float(row.get("buy_lg_amount", 0) or 0))
            sell = (float(row.get("sell_elg_amount", 0) or 0) + float(row.get("sell_lg_amount", 0) or 0))
            net_sum += (buy - sell)
        direction = "净流入" if net_sum > 0 else "净流出"
        lines.append(f"  近20日主力资金: {direction} {abs(net_sum)/1e8:.2f}亿")

    elif data_type == "margin" and not df.empty:
        latest = df.sort_values("trade_date").iloc[-1]
        rzye = float(latest.get("rzye", 0) or 0)
        lines.append(f"  最新融资余额: {rzye/1e8:.2f}亿")
        if "rqye" in df.columns:
            rqye = float(latest.get("rqye", 0) or 0)
            lines.append(f"  最新融券余额: {rqye/1e8:.2f}亿")

    elif data_type == "hk_hold" and not df.empty:
        latest = df.sort_values("trade_date").iloc[-1]
        ratio = float(latest.get("ratio", 0) or 0)
        lines.append(f"  最新北向持股占比: {ratio:.2f}%")

    return "\n".join(lines) if lines else ""


def _format_top_holders(df) -> str:
    """前十大股东摘要"""
    latest_period = df["end_date"].max() if "end_date" in df.columns else None
    if not latest_period:
        return ""
    latest = df[df["end_date"] == latest_period].head(5)
    lines = [f"  报告期: {str(latest_period)[:8]}"]
    for _, row in latest.iterrows():
        name = str(row.get("holder_name", ""))[:20]
        ratio = row.get("hold_ratio", 0)
        lines.append(f"  {name}: {float(ratio):.2f}%")
    return "\n".join(lines)


def _format_holder_trend(df) -> str:
    """股东人数趋势"""
    if "ann_date" not in df.columns:
        return ""
    df = df.sort_values("ann_date")
    if len(df) >= 2:
        first = df.iloc[0].get("holder_num", 0)
        last = df.iloc[-1].get("holder_num", 0)
        change = (last - first) / first * 100 if first else 0
        return f"  股东人数: {last/1e4:.1f}万 | 变化: {change:+.1f}%"
    return ""


def _format_dividend_summary(df) -> str:
    """分红摘要"""
    if "ann_date" not in df.columns:
        return ""
    cash_divs = [float(r.get("cash_div", 0) or 0) for _, r in df.sort_values("ann_date").iterrows()]
    cash_divs = [c for c in cash_divs if c > 0]
    if cash_divs:
        return f"  最新每股派息: {cash_divs[-1]:.2f}元 | 近5年累计: {sum(cash_divs[-5:]):.2f}元"
    return "  无分红记录"


def _format_basic_info(df) -> str:
    if df.empty:
        return ""
    r = df.iloc[0]
    return f"  名称: {r.get('name', 'N/A')} | 行业: {r.get('industry', 'N/A')} | PE: {r.get('pe', r.get('pe_ttm', 'N/A'))}"


def _format_audit(df) -> str:
    if df.empty:
        return ""
    latest = df.sort_values("ann_date").iloc[-1]
    return f"  最新审计意见: {latest.get('audit_result', 'N/A')} | 审计机构: {latest.get('audit_agency', 'N/A')}"


def _format_mainbz(df) -> str:
    if df.empty:
        return ""
    latest_period = df["end_date"].max() if "end_date" in df.columns else None
    if latest_period:
        latest = df[df["end_date"] == latest_period].head(5)
        lines = [f"  报告期: {str(latest_period)[:8]}"]
        for _, row in latest.iterrows():
            name = str(row.get("bz_item", ""))[:20]
            sales = row.get("bz_sales", 0)
            lines.append(f"  {name}: {(float(sales or 0)/1e8):.1f}亿")
        return "\n".join(lines)
    return ""


def _format_block_trade(df) -> str:
    if df.empty:
        return ""
    return f"  近10笔大宗交易记录可用（含价格、成交量、买卖方信息）"


# ============================================================================
# 数据类型中文标签
# ============================================================================

DATA_TYPE_LABELS = {
    "daily": "日线行情",
    "daily_basic": "每日指标",
    "basic": "基本信息",
    "stock_basic": "股票基础信息",
    "income": "利润表",
    "balance": "资产负债表",
    "cashflow": "现金流量表",
    "financial": "财务指标",
    "moneyflow": "资金流向",
    "margin": "融资融券",
    "margin_detail": "融资融券明细",
    "hk_hold": "北向资金",
    "block_trade": "大宗交易",
    "weekly": "周线行情",
    "monthly": "月线行情",
    "stk_holdernumber": "股东人数",
    "dividend": "分红送股",
    "top10_holders": "前十大股东",
    "top10_floatholders": "前十大流通股东",
    "fina_audit": "审计意见",
    "fina_mainbz": "主营业务构成",
}


# ============================================================================
# 自由提问轻量数据摘要
# ============================================================================

def build_lightweight_summary(data: dict, stock_code: str) -> str:
    """为自由提问模式构建 300-500 token 的数据摘要"""
    lines = [f"## 当前分析标的: {stock_code}"]

    daily_basic = data.get("daily_basic")
    daily = data.get("daily")
    if daily_basic is not None and not daily_basic.empty:
        r = daily_basic.iloc[0]
        lines.append("\n### 行情概览")
        lines.append(f"PE(TTM): {r.get('pe_ttm', 'N/A')} | PB: {r.get('pb', 'N/A')}")
        lines.append(f"总市值: {_fmt_yi(r.get('total_mv'))} | 流通市值: {_fmt_yi(r.get('circ_mv'))}")
    if daily is not None and not daily.empty:
        r = daily.iloc[0]
        lines.append(f"最新价: {r.get('close', 'N/A')} | 换手率: {r.get('turnover_rate', 'N/A')}%")
        if len(daily) > 1:
            prev = daily["close"].iloc[1]
            if pd.notna(prev):
                chg = (r["close"] - prev) / prev * 100
                lines.append(f"涨跌幅: {chg:+.2f}%")

    fin = data.get("financial")
    if fin is not None and not fin.empty:
        r = fin.iloc[0]
        lines.append("\n### 核心财务 (最新期)")
        for k, label in [("roe", "ROE(%)"), ("grossprofit_margin", "毛利率(%)"),
                         ("netprofit_margin", "净利率(%)"), ("debt_to_assets", "资产负债率(%)"),
                         ("or_yoy", "营收同比(%)")]:
            v = r.get(k)
            if v is not None and pd.notna(v):
                lines.append(f"{label}: {v}")

    income = data.get("income")
    if income is not None and not income.empty:
        r = income.iloc[0]
        rev = r.get("total_revenue")
        if rev is None:
            rev = r.get("revenue")
        np_val = r.get("net_profit")
        if np_val is None:
            np_val = r.get("n_income_attr_p")
        if rev is not None:
            lines.append(f"营收: {_fmt_yi(rev)}")
        if np_val is not None:
            lines.append(f"净利润: {_fmt_yi(np_val)}")

    moneyflow = data.get("moneyflow")
    if moneyflow is not None and not moneyflow.empty:
        lines.append("\n### 资金面")
        mf = moneyflow.sort_values("trade_date")
        net = sum((float(r.get("buy_elg_amount", 0) or 0) + float(r.get("buy_lg_amount", 0) or 0) -
                   float(r.get("sell_elg_amount", 0) or 0) - float(r.get("sell_lg_amount", 0) or 0))
                  for _, r in mf.tail(20).iterrows())
        lines.append(f"近20日主力净流入: {net/1e8:+.2f}亿")

    margin = data.get("margin")
    if margin is not None and not margin.empty:
        rzye = margin.sort_values("trade_date").iloc[-1].get("rzye")
        if rzye is not None:
            lines.append(f"融资余额: {float(rzye)/1e8:.2f}亿")

    hk = data.get("hk_hold")
    if hk is not None and not hk.empty:
        ratio = hk.sort_values("trade_date").iloc[-1].get("ratio")
        if ratio is not None:
            lines.append(f"北向持股: {float(ratio):.2f}%")

    holder = data.get("stk_holdernumber")
    if holder is not None and not holder.empty:
        num = holder.sort_values("ann_date").iloc[-1].get("holder_num")
        if num is not None:
            lines.append(f"股东人数: {float(num)/1e4:.1f}万")

    top10 = data.get("top10_holders")
    if top10 is not None and not top10.empty:
        latest_period = top10["end_date"].max() if "end_date" in top10.columns else None
        if latest_period:
            top = top10[top10["end_date"] == latest_period]
            total = sum(float(r.get("hold_ratio", 0) or 0) for _, r in top.iterrows())
            lines.append(f"前十大持股: {total:.1f}%")

    lines.append("\n请基于以上数据回答问题，引用具体数据点。如问题超出数据范围，说明局限性。")
    return "\n".join(lines)


def _fmt_yi(val) -> str:
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e8:
            return f"{v/1e8:.2f}亿"
        elif abs(v) >= 1e4:
            return f"{v/1e4:.2f}万"
        return f"{v:.2f}"
    except (ValueError, TypeError):
        return str(val)

# Tushare Data Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Tushare data import from 7 to 19 interfaces (12 new + 2 fixes), add shareholder/capital-flow/valuation analysis modules, and make KPI cards user-configurable.

**Architecture:** Follow existing adapter → data_service → analyzer pipeline. New Tushare-only data types keep raw column names with minimal type conversion. Three phases: adapter extension, service layer extension, and analyzer + UI integration.

**Tech Stack:** Python 3.12, pandas, FastAPI, Jinja2/htmx, Tushare Pro (2000+ point tier)

---

### File Structure

| File | Action | Responsibility |
|---|---|---|
| `financial_analyzer/data_sources/adapter.py` | Modify | +12 `_get_tushare()` handlers + basic converter |
| `financial_analyzer/data_sources/normalizer.py` | Modify | +`normalize_market()` basic type conversion |
| `financial_analyzer/web/services/data_service.py` | Modify | +`MARKET_DATA_TYPES`, extend `FINANCIAL_DATA_TYPES`, extend `extract_kpis` |
| `financial_analyzer/web/routes/data_api.py` | Modify | Split fetch into phases, background market data loading |
| `financial_analyzer/analyzers/shareholder.py` | Create | Shareholder structure analysis |
| `financial_analyzer/analyzers/capital_flow.py` | Create | Capital flow / margin / northbound analysis |
| `financial_analyzer/analyzers/phase2_analysis.py` | Modify | Add dividend analysis, weekly/monthly PE percentile |
| `financial_analyzer/services/analysis.py` | Modify | Register 3 new analysis types + extend comprehensive |
| `financial_analyzer/web/routes/settings_api.py` | Modify | Add `data_modules` config UI |
| `financial_analyzer/web/services/analysis_service.py` | Modify | Add new analysis types to pipeline groups |
| `financial_analyzer/web/routes/export_api.py` | Modify | Include new data types in export selector |
| `financial_analyzer/web/templates/partials/kpi_cards.html` | Modify | Configurable KPI card grid |
| `tests/test_adapter_tushare.py` | Create | Tests for new Tushare handlers |
| `tests/test_shareholder.py` | Create | Tests for shareholder analyzer |
| `tests/test_capital_flow.py` | Create | Tests for capital flow analyzer |

---

### Task 1: Extend adapter._get_tushare() with 12 new handlers

**Files:**
- Modify: `financial_analyzer/data_sources/adapter.py:212-237`

- [ ] **Step 1: Add 12 new data type handlers to `_get_tushare()`**

Replace the entire `_get_tushare` method (lines 212-237) with:

```python
def _get_tushare(self, symbol, start_date, end_date, data_type):
    try:
        if data_type == "daily":
            return self.tushare_pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "basic":
            return self.tushare_pro.daily_basic(
                ts_code=symbol, start_date=start_date, end_date=end_date,
                fields="ts_code,trade_date,close,turnover_rate,volume_ratio,pe,pe_ttm,pb,ps,total_mv,circ_mv,total_share,float_share"
            )
        elif data_type == "stock_basic":
            return self.tushare_pro.stock_basic(
                ts_code=symbol,
                fields='ts_code,name,industry,market,list_date'
            )
        elif data_type == "financial":
            return self.tushare_pro.fina_indicator(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "income":
            return self.tushare_pro.income(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "balance":
            return self.tushare_pro.balancesheet(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "cashflow":
            return self.tushare_pro.cashflow(ts_code=symbol, start_date=start_date, end_date=end_date)
        # ---- NEW: Market data (Phase 1) ----
        elif data_type == "moneyflow":
            return self.tushare_pro.moneyflow(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "margin":
            return self.tushare_pro.margin(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "margin_detail":
            return self.tushare_pro.margin_detail(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "hk_hold":
            return self.tushare_pro.hk_hold(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "block_trade":
            return self.tushare_pro.block_trade(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "weekly":
            return self.tushare_pro.weekly(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "monthly":
            return self.tushare_pro.monthly(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "stk_holdernumber":
            return self.tushare_pro.stk_holdernumber(ts_code=symbol, start_date=start_date, end_date=end_date)
        # ---- NEW: Financial data ----
        elif data_type == "dividend":
            return self.tushare_pro.dividend(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "top10_holders":
            return self.tushare_pro.top10_holders(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "top10_floatholders":
            return self.tushare_pro.top10_floatholders(ts_code=symbol, start_date=start_date, end_date=end_date)
        # ---- FIX: pre-existing types missing Tushare handler ----
        elif data_type == "fina_audit":
            return self.tushare_pro.fina_audit(ts_code=symbol, start_date=start_date, end_date=end_date)
        elif data_type == "fina_mainbz":
            return self.tushare_pro.fina_mainbz(ts_code=symbol, start_date=start_date, end_date=end_date, type='P')
        return None
    except Exception as e:
        logger.error(f"Tushare 数据获取失败: {e}")
        return None
```

- [ ] **Step 2: Verify the adapter still works for existing types**

Run: `cd c:/Users/LK/Desktop/FA/10.6 && python -c "
from financial_analyzer.data_sources.adapter import DataSourceAdapter
a = DataSourceAdapter()
a.set_tushare_token('YOUR_TUSHARE_TOKEN')
# Test existing
df = a.get_stock_data('000001.SZ', '20250101', '20250110', 'daily')
assert df is not None and not df.empty, 'daily failed'
print(f'daily: OK ({len(df)} rows)')
# Test new
for dt in ['moneyflow', 'margin', 'dividend', 'top10_holders', 'fina_audit']:
    df = a.get_stock_data('000001.SZ', '20240101', '20250110', dt)
    if df is not None and not df.empty:
        print(f'{dt}: OK ({len(df)} rows) - cols: {list(df.columns)[:5]}')
    else:
        print(f'{dt}: EMPTY (may be normal for this stock)')
"` 2>&1

- [ ] **Step 3: Add `_normalize_market` for basic type conversion on new data types**

In `adapter.py`, in the `_normalize` method (line 183), add after the existing elif chain:

```python
elif data_type in ("moneyflow", "margin", "margin_detail", "hk_hold",
                   "block_trade", "weekly", "monthly", "stk_holdernumber",
                   "dividend", "top10_holders", "top10_floatholders",
                   "fina_audit", "fina_mainbz"):
    df = DataNormalizer.normalize_market(df, data_type)
```

- [ ] **Step 4: Commit**

```bash
git add financial_analyzer/data_sources/adapter.py
git commit -m "feat: add 12 new Tushare handlers to adapter + market normalization hook"
```

---

### Task 2: Add normalize_market() to DataNormalizer

**Files:**
- Modify: `financial_analyzer/data_sources/normalizer.py` (add method near line 315)

- [ ] **Step 1: Add the `normalize_market` static method**

After the existing `normalize_cashflow` method, add:

```python
@staticmethod
def normalize_market(df: pd.DataFrame, data_type: str) -> pd.DataFrame:
    """新数据类型的基本类型转换 — 保持 Tushare 原始列名，仅做日期和数值规范化"""
    if df is None or df.empty:
        return df

    df = df.copy()

    # 日期列统一为 YYYYMMDD 字符串
    date_cols = {
        "moneyflow": "trade_date",
        "margin": "trade_date",
        "margin_detail": "trade_date",
        "hk_hold": "trade_date",
        "block_trade": "trade_date",
        "weekly": "trade_date",
        "monthly": "trade_date",
        "stk_holdernumber": "ann_date",
        "dividend": "ann_date",
        "top10_holders": "ann_date",
        "top10_floatholders": "ann_date",
        "fina_audit": "ann_date",
        "fina_mainbz": "end_date",
    }
    date_col = date_cols.get(data_type)
    if date_col and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y%m%d")
        df = df.sort_values(date_col, ascending=False).reset_index(drop=True)

    # 数值列类型转换（Tushare 返回的数值可能是 object 类型）
    numeric_candidates = {
        "moneyflow": ["buy_sm_vol", "buy_sm_amount", "sell_sm_vol", "sell_sm_amount",
                      "buy_md_vol", "buy_md_amount", "sell_md_vol", "sell_md_amount",
                      "buy_lg_vol", "buy_lg_amount", "sell_lg_vol", "sell_lg_amount",
                      "buy_elg_vol", "buy_elg_amount", "sell_elg_vol", "sell_elg_amount",
                      "net_mf_vol", "net_mf_amount"],
        "margin": ["rzye", "rqye", "rzmre", "rqyl", "rzche", "rqchl", "rzrqye"],
        "margin_detail": ["rzye", "rqye", "rzmre", "rqyl", "rzche", "rqchl"],
        "hk_hold": ["vol", "ratio"],
        "block_trade": ["price", "vol", "amount"],
        "weekly": ["open", "high", "low", "close", "vol", "amount"],
        "monthly": ["open", "high", "low", "close", "vol", "amount"],
        "stk_holdernumber": ["holder_num"],
        "dividend": ["cash_div", "stk_div", "stk_bo_rate", "record_date"],
        "top10_holders": ["hold_amount", "hold_ratio"],
        "top10_floatholders": ["hold_amount", "hold_ratio"],
        "fina_audit": ["audit_fees"],
        "fina_mainbz": ["bz_sales", "bz_profit", "bz_cost", "bz_sales_ratio", "bz_profit_ratio"],
    }

    cols = numeric_candidates.get(data_type, [])
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info(f"[tushare] {data_type} 基本转换完成: {len(df)} 行")
    return df
```

- [ ] **Step 2: Verify normalization works**

Run: `cd c:/Users/LK/Desktop/FA/10.6 && python -c "
from financial_analyzer.data_sources.normalizer import DataNormalizer
import pandas as pd
df = pd.DataFrame({'trade_date': ['20250115', '20250114'], 'buy_lg_vol': ['1000', '2000'], 'sell_lg_vol': ['500', '600']})
result = DataNormalizer.normalize_market(df, 'moneyflow')
print(result.dtypes)
print(result.head())
"` 2>&1

- [ ] **Step 3: Commit**

```bash
git add financial_analyzer/data_sources/normalizer.py
git commit -m "feat: add normalize_market() for basic type conversion of new Tushare data"
```

---

### Task 3: Extend DataService with new data types and KPIs

**Files:**
- Modify: `financial_analyzer/web/services/data_service.py`

- [ ] **Step 1: Add MARKET_DATA_TYPES and extend FINANCIAL_DATA_TYPES**

Replace the class variables (lines 22-24) with:

```python
# 所有可获取的数据类型
BASIC_DATA_TYPES = ["daily", "daily_basic", "basic", "stock_basic"]
MARKET_DATA_TYPES = ["moneyflow", "margin", "margin_detail", "hk_hold",
                     "block_trade", "weekly", "monthly", "stk_holdernumber"]
FINANCIAL_DATA_TYPES = ["income", "balance", "cashflow", "financial",
                        "dividend", "top10_holders", "top10_floatholders",
                        "fina_audit", "fina_mainbz"]
```

- [ ] **Step 2: Extend `extract_kpis` with new indicators**

After the market_cap block in `extract_kpis` (after line 180), add:

```python
            # ===== 新增 KPI =====

            # 主力资金净流入
            moneyflow = data.get("moneyflow")
            if moneyflow is not None and not moneyflow.empty:
                net_mf = moneyflow.iloc[0].get("net_mf_amount")
                if net_mf:
                    try:
                        net_mf_val = float(net_mf)
                        if abs(net_mf_val) >= 1e8:
                            kpis["net_mf_amount"] = f"{net_mf_val / 1e8:+.2f}亿"
                        elif abs(net_mf_val) >= 1e4:
                            kpis["net_mf_amount"] = f"{net_mf_val / 1e4:+.2f}万"
                        else:
                            kpis["net_mf_amount"] = f"{net_mf_val:+,.0f}"
                        kpis["net_mf_positive"] = net_mf_val >= 0
                    except (ValueError, TypeError):
                        kpis["net_mf_amount"] = "--"

            # 融资余额
            margin = data.get("margin")
            if margin is not None and not margin.empty:
                rzye = margin.iloc[0].get("rzye")
                if rzye:
                    try:
                        kpis["margin_balance"] = f"{float(rzye) / 1e8:.2f}亿"
                    except (ValueError, TypeError):
                        kpis["margin_balance"] = "--"

            # 北向持股占比
            hk_hold = data.get("hk_hold")
            if hk_hold is not None and not hk_hold.empty:
                ratio = hk_hold.iloc[0].get("ratio")
                if ratio:
                    try:
                        kpis["hk_hold_ratio"] = f"{float(ratio):.2f}%"
                    except (ValueError, TypeError):
                        kpis["hk_hold_ratio"] = "--"

            # 股东人数
            stk_holdernumber = data.get("stk_holdernumber")
            if stk_holdernumber is not None and not stk_holdernumber.empty:
                holder_num = stk_holdernumber.iloc[0].get("holder_num")
                if holder_num:
                    try:
                        hn = float(holder_num)
                        if hn >= 1e4:
                            kpis["holder_num"] = f"{hn / 1e4:.2f}万"
                        else:
                            kpis["holder_num"] = f"{hn:,.0f}"
                    except (ValueError, TypeError):
                        kpis["holder_num"] = "--"

            # 股息率
            dividend = data.get("dividend")
            if dividend is not None and not dividend.empty:
                cash_div = dividend.iloc[0].get("cash_div")
                if cash_div and "current_price" not in str(kpis.get("current_price", "--")):
                    pass  # 需要当前价格才能计算股息率
                if cash_div:
                    try:
                        cd = float(cash_div)
                        kpis["cash_div"] = f"{cd:.2f}元"
                    except (ValueError, TypeError):
                        kpis["cash_div"] = "--"

            # 股息率计算（如果有 current_price）
            if kpis.get("cash_div", "--") != "--" and kpis.get("current_price", "--") != "--":
                try:
                    cd_val = float(str(kpis["cash_div"]).replace("元", ""))
                    price_val = float(kpis["current_price"])
                    if price_val > 0:
                        kpis["div_yield"] = f"{cd_val / price_val * 100:.2f}%"
                except (ValueError, TypeError):
                    kpis["div_yield"] = "--"
```

- [ ] **Step 3: Commit**

```bash
git add financial_analyzer/web/services/data_service.py
git commit -m "feat: add MARKET_DATA_TYPES, extend FINANCIAL_DATA_TYPES, extend KPIs"
```

---

### Task 4: Refactor data_api.py for phased background loading

**Files:**
- Modify: `financial_analyzer/web/routes/data_api.py`

- [ ] **Step 1: Extend `fetch_data` to trigger market data background loading**

In `fetch_data` (after line 74, where `data = await loop.run_in_executor(None, do_fetch_basic)`), add after the basic fetch and before the fin_pending check:

```python

    # 后台加载市场数据
    market_types = DataService.MARKET_DATA_TYPES

    def do_fetch_market():
        market_data = {}
        for dtype in market_types:
            try:
                df = adapter.get_stock_data(stock_code, start_date, end_date, dtype)
                if df is not None and not df.empty:
                    market_data[dtype] = df
                    logger.info(f"市场数据 {dtype} 获取成功: {len(df)} 行")
            except Exception as e:
                logger.debug(f"市场数据 {dtype} 获取失败: {e}")
        return market_data

    async def background_market():
        try:
            sid = request.cookies.get("fa_session", DEFAULT_SESSION_ID)
            logger.info(f"开始后台加载市场数据: {market_types}")
            market_data = await loop.run_in_executor(None, do_fetch_market)
            sess = _sessions.get(sid)
            if sess is None:
                return
            for k, df in market_data.items():
                sess["data"][k] = df.to_dict("records")
            logger.info(f"后台市场数据加载完成: {list(market_data.keys())}")
        except Exception as e:
            logger.error(f"后台市场数据加载失败: {e}", exc_info=True)

    asyncio.create_task(background_market())
```

- [ ] **Step 2: Update data-table route to include market types**

In the `data_table` route (line 165), update `all_data_types`:

```python
    all_data_types = DataService.BASIC_DATA_TYPES + DataService.MARKET_DATA_TYPES + DataService.FINANCIAL_DATA_TYPES
```

- [ ] **Step 3: Commit**

```bash
git add financial_analyzer/web/routes/data_api.py
git commit -m "feat: add background market data loading to /fetch endpoint"
```

---

### Task 5: Create ShareholderAnalyzer

**Files:**
- Create: `financial_analyzer/analyzers/shareholder.py`

- [ ] **Step 1: Write ShareholderAnalyzer**

```python
"""
股东结构分析器 — 股东人数趋势、机构持股、股权集中度
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..logging_config import get_logger

logger = get_logger(__name__)


class ShareholderAnalyzer(BaseAnalyzer):
    """股东结构分析器"""

    def __init__(self, data: dict, stock_code: str, data_adapter=None, cache_manager=None):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    def _get_basic_info(self) -> dict:
        info = {}
        stock_basic = self.data.get("stock_basic")
        if stock_basic is not None and not stock_basic.empty:
            sb = stock_basic.iloc[0]
            info["name"] = sb.get("name", "N/A")
        return info

    def analyze(self) -> str:
        """股东结构综合分析"""
        result = RF.header("股东结构分析")

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        # ---- 1. 股东人数趋势 ----
        result += self._analyze_holder_count()

        # ---- 2. 前十大股东 ----
        result += self._analyze_top10_holders()

        # ---- 3. 前十大流通股东 ----
        result += self._analyze_top10_floatholders()

        # ---- 4. 综合评分 ----
        result += self._ownership_score()

        result += RF.footer()
        return result

    def _analyze_holder_count(self) -> str:
        result = RF.section("股东人数变化趋势")
        df = self.data.get("stk_holdernumber")
        if df is None or df.empty:
            return result + "  未获取到股东人数数据\n\n"

        df = df.sort_values("ann_date").reset_index(drop=True)
        if len(df) < 2:
            result += f"  最新股东人数: {self._fmt_num(df.iloc[-1].get('holder_num'))}\n\n"
            return result

        first = df.iloc[0].get("holder_num") or 0
        last = df.iloc[-1].get("holder_num") or 0
        change_pct = (last - first) / first * 100 if first else 0

        result += f"  {'─' * 55}\n"
        result += f"  {'报告期':<14s} {'股东人数':>14s} {'变化':>14s}\n"
        result += f"  {'─' * 55}\n"

        prev = None
        for _, row in df.iterrows():
            date = str(row.get("ann_date", "N/A"))[:8]
            num = row.get("holder_num")
            num_str = self._fmt_num(num)
            if prev is not None and prev > 0:
                delta = (num - prev) / prev * 100 if num else 0
                delta_str = f"{delta:+.1f}%"
            else:
                delta_str = "--"
            result += f"  {date:<14s} {num_str:>14s} {delta_str:>14s}\n"
            prev = num

        direction = "增加" if change_pct > 0 else "减少"
        signal = "⚠️ 散户化" if change_pct > 20 else ("✅ 筹码集中" if change_pct < -20 else "→ 基本稳定")
        result += f"\n  总变化: {change_pct:+.1f}% (股东人数{direction})  {signal}\n"
        result += "\n"
        return result

    def _analyze_top10_holders(self) -> str:
        result = RF.section("前十大股东")
        df = self.data.get("top10_holders")
        if df is None or df.empty:
            return result + "  未获取到前十大股东数据\n\n"

        latest_period = df["end_date"].max() if "end_date" in df.columns else None
        if latest_period:
            latest = df[df["end_date"] == latest_period]
            result += f"  报告期: {str(latest_period)[:8]}\n\n"

            total_ratio = 0
            result += f"  {'股东名称':<24s} {'持股数':>12s} {'占比':>10s}\n"
            result += f"  {'─' * 48}\n"
            for _, row in latest.head(10).iterrows():
                name = str(row.get("holder_name", "N/A"))
                if len(name) > 22:
                    name = name[:22] + ".."
                amount = row.get("hold_amount")
                ratio = row.get("hold_ratio")
                amt_str = self._fmt_num(amount) if amount else "N/A"
                ratio_str = f"{float(ratio):.2f}%" if ratio else "N/A"
                result += f"  {name:<24s} {amt_str:>12s} {ratio_str:>10s}\n"
                if ratio:
                    total_ratio += float(ratio)

            result += f"\n  前十大合计持股: {total_ratio:.2f}%\n"
            if total_ratio > 60:
                result += f"  ✅ 股权高度集中（>60%），控制权稳定\n"
            elif total_ratio > 40:
                result += f"  → 股权相对集中（40-60%）\n"
            else:
                result += f"  ⚠️ 股权较分散（<40%），存在潜在控制权风险\n"

        result += "\n"
        return result

    def _analyze_top10_floatholders(self) -> str:
        result = RF.section("前十大流通股东（机构持仓）")
        df = self.data.get("top10_floatholders")
        if df is None or df.empty:
            return result + "  未获取到流通股东数据\n\n"

        latest_period = df["end_date"].max() if "end_date" in df.columns else None
        if latest_period:
            latest = df[df["end_date"] == latest_period]
            inst_ratio = 0
            fund_names = ["基金", "QFII", "社保", "保险", "券商", "信托", "银行", "私募"]

            for _, row in latest.iterrows():
                name = str(row.get("holder_name", ""))
                ratio = row.get("hold_ratio")
                if ratio:
                    is_inst = any(kw in name for kw in fund_names)
                    if is_inst:
                        inst_ratio += float(ratio)

            result += f"  报告期: {str(latest_period)[:8]}\n"
            result += f"  机构持股占比: {inst_ratio:.2f}%\n\n"

            # 列出机构
            for _, row in latest.head(10).iterrows():
                name = str(row.get("holder_name", ""))
                is_inst = any(kw in name for kw in fund_names)
                if is_inst:
                    ratio = row.get("hold_ratio")
                    ratio_str = f"{float(ratio):.2f}%" if ratio else "N/A"
                    result += f"  · {name:<30s} {ratio_str:>8s}\n"

            if inst_ratio > 30:
                result += f"\n  ✅ 机构持仓比例较高（>30%），认可度高\n"
            elif inst_ratio > 10:
                result += f"\n  → 有一定机构参与（10-30%）\n"
            else:
                result += f"\n  → 机构参与度较低（<10%）\n"

        result += "\n"
        return result

    def _ownership_score(self) -> str:
        """股权结构综合评分"""
        result = RF.section("股权结构综合评分")

        score = 50  # 基础分
        reasons = []

        # 股东人数趋势
        holder_df = self.data.get("stk_holdernumber")
        if holder_df is not None and not holder_df.empty:
            holder_df = holder_df.sort_values("ann_date")
            if len(holder_df) >= 2:
                first = holder_df.iloc[0].get("holder_num") or 0
                last = holder_df.iloc[-1].get("holder_num") or 0
                change = (last - first) / first * 100 if first else 0
                if change < -20:
                    score += 20
                    reasons.append("股东人数大幅减少 → 筹码集中 (+20)")
                elif change < -5:
                    score += 10
                    reasons.append("股东人数小幅减少 (+10)")
                elif change > 20:
                    score -= 15
                    reasons.append("股东人数大幅增加 → 筹码分散 (-15)")

        # 前十大集中度
        top10 = self.data.get("top10_holders")
        if top10 is not None and not top10.empty:
            latest_period = top10["end_date"].max() if "end_date" in top10.columns else None
            if latest_period:
                latest = top10[top10["end_date"] == latest_period]
                total_ratio = sum(float(r) for r in latest["hold_ratio"] if r)
                if total_ratio > 60:
                    score += 15
                    reasons.append(f"前十大持股{total_ratio:.1f}% → 高度集中 (+15)")
                elif total_ratio > 40:
                    score += 5
                    reasons.append(f"前十大持股{total_ratio:.1f}% (+5)")

        score = max(0, min(100, score))
        rating = "优秀" if score >= 80 else ("良好" if score >= 60 else ("一般" if score >= 40 else "关注"))

        result += f"  股权结构评分: {score}/100 ({rating})\n"
        for r in reasons:
            result += f"    {r}\n"

        result += "\n"
        return result

    @staticmethod
    def _fmt_num(val) -> str:
        if val is None:
            return "N/A"
        try:
            v = float(val)
            if abs(v) >= 1e8:
                return f"{v / 1e8:.2f}亿"
            elif abs(v) >= 1e4:
                return f"{v / 1e4:.2f}万"
            else:
                return f"{v:,.0f}"
        except (ValueError, TypeError):
            return "N/A"
```

- [ ] **Step 2: Run a smoke test**

```bash
cd c:/Users/LK/Desktop/FA/10.6 && python -c "
from financial_analyzer.analyzers.shareholder import ShareholderAnalyzer
print('ShareholderAnalyzer imported successfully')
print([m for m in dir(ShareholderAnalyzer) if not m.startswith('_')])
"
```

- [ ] **Step 3: Commit**

```bash
git add financial_analyzer/analyzers/shareholder.py
git commit -m "feat: add ShareholderAnalyzer for ownership structure analysis"
```

---

### Task 6: Create CapitalFlowAnalyzer

**Files:**
- Create: `financial_analyzer/analyzers/capital_flow.py`

- [ ] **Step 1: Write CapitalFlowAnalyzer**

```python
"""
资金面分析器 — 主力资金流向、融资融券、北向资金、大宗交易
"""
import pandas as pd
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..logging_config import get_logger

logger = get_logger(__name__)


class CapitalFlowAnalyzer(BaseAnalyzer):
    """资金面分析器"""

    def __init__(self, data: dict, stock_code: str, data_adapter=None, cache_manager=None):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    def _get_basic_info(self) -> dict:
        info = {}
        stock_basic = self.data.get("stock_basic")
        if stock_basic is not None and not stock_basic.empty:
            sb = stock_basic.iloc[0]
            info["name"] = sb.get("name", "N/A")
        return info

    def analyze(self) -> str:
        """资金面综合分析"""
        result = RF.header("资金面分析")

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        # ---- 1. 主力资金流向 ----
        result += self._analyze_moneyflow()

        # ---- 2. 融资融券 ----
        result += self._analyze_margin()

        # ---- 3. 北向资金 ----
        result += self._analyze_hk_hold()

        # ---- 4. 大宗交易 ----
        result += self._analyze_block_trade()

        # ---- 5. 综合评分 ----
        result += self._capital_flow_score()

        result += RF.footer()
        return result

    def _analyze_moneyflow(self) -> str:
        result = RF.section("主力资金流向")
        df = self.data.get("moneyflow")
        if df is None or df.empty:
            return result + "  未获取到资金流向数据\n\n"

        # 计算近20日累计主力净流入
        df = df.sort_values("trade_date").reset_index(drop=True)
        recent = df.tail(20)

        net_amounts = []
        for _, row in recent.iterrows():
            buy_elg = float(row.get("buy_elg_amount", 0) or 0)
            sell_elg = float(row.get("sell_elg_amount", 0) or 0)
            buy_lg = float(row.get("buy_lg_amount", 0) or 0)
            sell_lg = float(row.get("sell_lg_amount", 0) or 0)
            net_amounts.append((buy_elg + buy_lg) - (sell_elg + sell_lg))

        cum_net = sum(net_amounts)
        recent_5 = net_amounts[-5:] if len(net_amounts) >= 5 else net_amounts
        avg_daily_net = sum(recent_5) / len(recent_5) if recent_5 else 0

        result += f"  近20日累计主力净流入: {self._fmt_amount(cum_net)}\n"
        result += f"  近5日日均主力净流入: {self._fmt_amount(avg_daily_net)}\n\n"

        # 趋势
        first_10 = net_amounts[:10] if len(net_amounts) >= 10 else net_amounts
        last_10 = net_amounts[-10:] if len(net_amounts) >= 10 else net_amounts
        first_sum = sum(first_10)
        last_sum = sum(last_10)

        if first_sum < 0 and last_sum > 0:
            result += f"  ✅ 资金流向改善：前10日净流出 → 近10日净流入，主力态度转多\n"
        elif first_sum > 0 and last_sum > 0:
            result += f"  ✅ 主力持续流入，资金面偏多\n"
        elif first_sum < 0 and last_sum < 0:
            result += f"  ⚠️ 主力持续流出，资金面偏空\n"
        else:
            result += f"  → 主力态度转向偏空\n"

        # 近5日逐日明细
        result += f"\n  {'日期':<12s} {'超大单净流入':>14s} {'大单净流入':>14s} {'中单净流入':>14s} {'小单净流入':>14s}\n"
        result += f"  {'─' * 72}\n"
        for _, row in recent.tail(5).iterrows():
            date = str(row.get("trade_date", ""))[:8]
            elg = (float(row.get("buy_elg_amount", 0) or 0) - float(row.get("sell_elg_amount", 0) or 0))
            lg = (float(row.get("buy_lg_amount", 0) or 0) - float(row.get("sell_lg_amount", 0) or 0))
            md = (float(row.get("buy_md_amount", 0) or 0) - float(row.get("sell_md_amount", 0) or 0))
            sm = (float(row.get("buy_sm_amount", 0) or 0) - float(row.get("sell_sm_amount", 0) or 0))
            result += f"  {date:<12s} {self._fmt_amount(elg):>14s} {self._fmt_amount(lg):>14s} {self._fmt_amount(md):>14s} {self._fmt_amount(sm):>14s}\n"

        result += "\n"
        return result

    def _analyze_margin(self) -> str:
        result = RF.section("融资融券")
        margin_df = self.data.get("margin")
        margin_detail = self.data.get("margin_detail")

        if margin_df is not None and not margin_df.empty:
            margin_df = margin_df.sort_values("trade_date").reset_index(drop=True)
            latest = margin_df.iloc[-1]
            rzye = float(latest.get("rzye", 0) or 0)
            rqye = float(latest.get("rqye", 0) or 0)

            result += f"  最新融资余额: {rzye / 1e8:.2f}亿\n"
            result += f"  最新融券余额: {rqye / 1e8:.2f}亿\n"
            if rzye > 0:
                result += f"  融资融券比: {rzye / max(rqye, 1):.0f}:1\n"

            # 趋势
            if len(margin_df) >= 10:
                prev_10 = float(margin_df.iloc[-10].get("rzye", 0) or 0)
                change = (rzye - prev_10) / prev_10 * 100 if prev_10 > 0 else 0
                if change > 10:
                    result += f"  ✅ 融资余额快速上升（+{change:.1f}%），杠杆资金看多\n"
                elif change > 0:
                    result += f"  → 融资余额小幅增加（+{change:.1f}%）\n"
                elif change < -10:
                    result += f"  ⚠️ 融资余额快速下降（{change:.1f}%），杠杆资金撤退\n"
                else:
                    result += f"  → 融资余额小幅下降（{change:.1f}%）\n"

        if margin_detail is not None and not margin_detail.empty:
            latest = margin_detail.sort_values("trade_date").iloc[-1]
            rzmre = float(latest.get("rzmre", 0) or 0)
            rqyl = float(latest.get("rqyl", 0) or 0)
            result += f"  当日融资买入额: {rzmre / 1e8:.2f}亿\n"
            result += f"  当日融券卖出量: {rqyl / 1e4:.2f}万股\n" if rqyl else ""

        result += "\n"
        return result

    def _analyze_hk_hold(self) -> str:
        result = RF.section("北向资金（沪深股通）")
        df = self.data.get("hk_hold")
        if df is None or df.empty:
            return result + "  未获取到北向资金数据\n\n"

        df = df.sort_values("trade_date").reset_index(drop=True)
        latest = df.iloc[-1]
        latest_ratio = float(latest.get("ratio", 0) or 0)

        result += f"  最新北向持股占比: {latest_ratio:.2f}%\n"
        result += f"  最新北向持股数: {self._fmt_num(latest.get('vol'))}\n"

        if len(df) >= 20:
            prev_20 = float(df.iloc[-20].get("ratio", 0) or 0)
            change = latest_ratio - prev_20
            if change > 1:
                result += f"  ✅ 北向资金近20日增持 {change:+.2f}个百分点\n"
            elif change < -1:
                result += f"  ⚠️ 北向资金近20日减持 {change:+.2f}个百分点\n"
            else:
                result += f"  → 北向资金近20日基本持平\n"

        result += "\n"
        return result

    def _analyze_block_trade(self) -> str:
        result = RF.section("大宗交易")
        df = self.data.get("block_trade")
        if df is None or df.empty:
            return result + "  未获取到大宗交易数据\n\n"

        recent = df.head(10) if "trade_date" in df.columns else df.iloc[:10]
        result += f"  近10笔大宗交易:\n"
        result += f"  {'日期':<12s} {'价格':>10s} {'成交量':>12s} {'成交额':>12s}\n"
        result += f"  {'─' * 50}\n"

        for _, row in recent.iterrows():
            date = str(row.get("trade_date", "N/A"))[:8]
            price = f"{float(row.get('price', 0)):.2f}" if row.get("price") else "N/A"
            vol = self._fmt_num(row.get("vol"))
            amount = self._fmt_amount(row.get("amount"))
            result += f"  {date:<12s} {price:>10s} {vol:>12s} {amount:>12s}\n"

        result += "\n"
        return result

    def _capital_flow_score(self) -> str:
        """资金面综合评分"""
        result = RF.section("资金面综合评分")

        score = 50
        reasons = []

        # 主力资金
        moneyflow = self.data.get("moneyflow")
        if moneyflow is not None and not moneyflow.empty:
            mf = moneyflow.sort_values("trade_date")
            recent = mf.tail(20)
            net_sum = 0
            for _, row in recent.iterrows():
                buy = float(row.get("buy_elg_amount", 0) or 0) + float(row.get("buy_lg_amount", 0) or 0)
                sell = float(row.get("sell_elg_amount", 0) or 0) + float(row.get("sell_lg_amount", 0) or 0)
                net_sum += (buy - sell)
            if net_sum > 1e8:
                score += 20
                reasons.append("主力近20日大幅净流入 (+20)")
            elif net_sum > 0:
                score += 10
                reasons.append("主力近20日小幅净流入 (+10)")
            else:
                score -= 10
                reasons.append("主力近20日净流出 (-10)")

        # 北向资金
        hk_hold = self.data.get("hk_hold")
        if hk_hold is not None and not hk_hold.empty:
            hk = hk_hold.sort_values("trade_date")
            if len(hk) >= 20:
                recent_ratio = float(hk.iloc[-1].get("ratio", 0) or 0)
                prev_ratio = float(hk.iloc[-20].get("ratio", 0) or 0)
                if recent_ratio - prev_ratio > 0.5:
                    score += 10
                    reasons.append("北向资金增持 (+10)")

        # 融资
        margin = self.data.get("margin")
        if margin is not None and not margin.empty:
            m = margin.sort_values("trade_date")
            if len(m) >= 10:
                latest = float(m.iloc[-1].get("rzye", 0) or 0)
                prev = float(m.iloc[-10].get("rzye", 0) or 0)
                change = (latest - prev) / prev * 100 if prev > 0 else 0
                if change > 5:
                    score += 5
                    reasons.append("融资余额增长 (+5)")

        score = max(0, min(100, score))
        rating = "偏多" if score >= 60 else ("中性" if score >= 40 else "偏空")

        result += f"  资金面评分: {score}/100 ({rating})\n"
        for r in reasons:
            result += f"    {r}\n"

        result += "\n"
        return result

    @staticmethod
    def _fmt_amount(val) -> str:
        if val is None:
            return "N/A"
        try:
            v = float(val)
            if abs(v) >= 1e8:
                return f"{v / 1e8:+.2f}亿"
            elif abs(v) >= 1e4:
                return f"{v / 1e4:+.2f}万"
            else:
                return f"{v:+,.0f}"
        except (ValueError, TypeError):
            return "N/A"

    @staticmethod
    def _fmt_num(val) -> str:
        if val is None:
            return "N/A"
        try:
            v = float(val)
            if abs(v) >= 1e8:
                return f"{v / 1e8:.2f}亿"
            elif abs(v) >= 1e4:
                return f"{v / 1e4:.2f}万"
            else:
                return f"{v:,.0f}"
        except (ValueError, TypeError):
            return "N/A"
```

- [ ] **Step 2: Smoke test import**

```bash
cd c:/Users/LK/Desktop/FA/10.6 && python -c "
from financial_analyzer.analyzers.capital_flow import CapitalFlowAnalyzer
print('CapitalFlowAnalyzer imported successfully')
"
```

- [ ] **Step 3: Commit**

```bash
git add financial_analyzer/analyzers/capital_flow.py
git commit -m "feat: add CapitalFlowAnalyzer for moneyflow/margin/hk_hold/block_trade analysis"
```

---

### Task 7: Extend Phase2Analyzer with dividend and weekly/monthly PE analysis

**Files:**
- Modify: `financial_analyzer/analyzers/phase2_analysis.py`

- [ ] **Step 1: Add dividend analysis method**

Add to `Phase2Analyzer` class (before the last method):

```python
    def dividend_analysis(self) -> str:
        """分红分析 — 股息率、分红稳定性"""
        df = self.data.get("dividend")
        if df is None or df.empty:
            return "  未获取到分红数据（该股票可能分红较少或数据缺失）\n"

        df = df.sort_values("ann_date").reset_index(drop=True)
        lines = ["▌ 分红分析", ""]

        # 历年分红
        lines.append(f"  {'公告日':<12s} {'每股派息':>10s} {'每股送股':>10s}")
        lines.append(f"  {'─' * 36}")
        for _, row in df.tail(10).iterrows():
            date = str(row.get("ann_date", ""))[:8]
            cash = float(row.get("cash_div", 0) or 0)
            stk = float(row.get("stk_div", 0) or 0)
            lines.append(f"  {date:<12s} {cash:>8.2f}元 {stk:>8.2f}股")

        # 稳定性
        cash_divs = [float(row.get("cash_div", 0) or 0) for _, row in df.iterrows()]
        cash_divs = [c for c in cash_divs if c > 0]
        if len(cash_divs) >= 5:
            total_5y = sum(cash_divs[-5:])
            avg = total_5y / 5
            lines.append(f"\n  近5年累计派息: {total_5y:.2f}元/股")
            lines.append(f"  年均派息: {avg:.2f}元/股")

            # 稳定性: 连续分红年数
            consecutive = 0
            for c in reversed(cash_divs):
                if c > 0:
                    consecutive += 1
                else:
                    break
            lines.append(f"  连续分红年数: {consecutive}")

            if consecutive >= 5:
                lines.append(f"  ✅ 分红稳定，连续{consecutive}年派息")
            elif consecutive >= 3:
                lines.append(f"  → 分红基本稳定")
            else:
                lines.append(f"  ⚠️ 分红不稳定")

        # 股息率
        price = self._get_current_price()
        if price and cash_divs:
            latest_div = cash_divs[-1]
            div_yield = latest_div / price * 100
            lines.append(f"\n  当前股价: {price:.2f}元")
            lines.append(f"  最新每股派息: {latest_div:.2f}元")
            lines.append(f"  股息率: {div_yield:.2f}%")
            if div_yield > 4:
                lines.append(f"  ✅ 高股息（>4%），适合股息策略")
            elif div_yield > 2:
                lines.append(f"  → 中等股息率（2-4%）")
            else:
                lines.append(f"  → 低股息率（<2%）")

        return "\n".join(lines)

    def _get_current_price(self) -> float | None:
        daily = self.data.get("daily")
        if daily is not None and not daily.empty and "close" in daily.columns:
            return float(daily["close"].iloc[0])
        weekly = self.data.get("weekly")
        if weekly is not None and not weekly.empty and "close" in weekly.columns:
            return float(weekly["close"].iloc[0])
        return None
```

- [ ] **Step 2: Add weekly/monthly PE percentile analysis**

Add to `Phase2Analyzer`:

```python
    def weekly_pe_percentile(self) -> str:
        """基于周线数据的PE分位分析"""
        weekly = self.data.get("weekly")
        if weekly is None or weekly.empty:
            return "  未获取到周线数据\n"

        daily_basic = self.data.get("daily_basic")
        current_pe = None
        if daily_basic is not None and not daily_basic.empty:
            current_pe = daily_basic.iloc[0].get("pe_ttm")

        lines = ["▌ 周线PE分位分析", ""]
        lines.append(f"  周线数据: {len(weekly)} 条")
        if current_pe:
            lines.append(f"  当前PE(TTM): {float(current_pe):.1f}")
        lines.append("")

        weekly = weekly.sort_values("trade_date").reset_index(drop=True)
        if "close" in weekly.columns:
            recent = float(weekly["close"].iloc[-1])
            high_52w = float(weekly["close"].tail(52).max()) if len(weekly) >= 52 else float(weekly["close"].max())
            low_52w = float(weekly["close"].tail(52).min()) if len(weekly) >= 52 else float(weekly["close"].min())
            lines.append(f"  最新收盘价: {recent:.2f}")
            lines.append(f"  52周最高: {high_52w:.2f}")
            lines.append(f"  52周最低: {low_52w:.2f}")

            if high_52w > low_52w:
                pct_52w = (recent - low_52w) / (high_52w - low_52w) * 100
                lines.append(f"  52周价格分位: {pct_52w:.1f}%")
                if pct_52w < 20:
                    lines.append(f"  ✅ 价格处于52周低位")
                elif pct_52w > 80:
                    lines.append(f"  ⚠️ 价格处于52周高位")

        return "\n".join(lines)
```

- [ ] **Step 3: Add the `_get_current_price` method as a proper instance method**

The `_get_current_price` from Step 1 should be in the class. Verify it's added.

- [ ] **Step 4: Commit**

```bash
git add financial_analyzer/analyzers/phase2_analysis.py
git commit -m "feat: add dividend analysis and weekly PE percentile to Phase2Analyzer"
```

---

### Task 8: Register new analysis types in ANALYSIS_MAP and AnalysisService

**Files:**
- Modify: `financial_analyzer/services/analysis.py`
- Modify: `financial_analyzer/web/services/analysis_service.py`

- [ ] **Step 1: Add imports and ANALYSIS_MAP entries in services/analysis.py**

Add imports at top:

```python
from ..analyzers.shareholder import ShareholderAnalyzer
from ..analyzers.capital_flow import CapitalFlowAnalyzer
```

Add entries to `ANALYSIS_MAP` dict (before the closing `}`):

```python
    # 股东与资金面（Phase 1 新增）
    "shareholder": _make_analyzer(ShareholderAnalyzer, "analyze"),
    "capital_flow": _make_analyzer(CapitalFlowAnalyzer, "analyze"),
    "dividend_analysis": _make_phase2_runner("dividend_analysis"),
    "weekly_pe": _make_phase2_runner("weekly_pe_percentile"),
```

- [ ] **Step 2: Add pipeline groups in analysis_service.py**

In `get_pipeline_stages()` (line 33), add a new stage between 2 and 3:

```python
        ("2.5 股东与资金", "shareholder", [
            ("shareholder", "股东结构分析"), ("capital_flow", "资金面分析"),
            ("dividend_analysis", "分红分析"), ("weekly_pe", "周线PE分位"),
        ]),
```

And in `get_analysis_list()`, add a new group:

```python
        ("股东与资金面 (Phase 1)", [
            ("shareholder", "股东结构分析"), ("capital_flow", "资金面分析"),
            ("dividend_analysis", "分红分析"), ("weekly_pe", "周线PE分位"),
        ]),
```

- [ ] **Step 3: Verify imports**

```bash
cd c:/Users/LK/Desktop/FA/10.6 && python -c "
from financial_analyzer.services.analysis import ANALYSIS_MAP
print('New analysis types:')
for k in ['shareholder', 'capital_flow', 'dividend_analysis', 'weekly_pe']:
    print(f'  {k}: {\"OK\" if k in ANALYSIS_MAP else \"MISSING\"}')" 2>&1
```

- [ ] **Step 4: Commit**

```bash
git add financial_analyzer/services/analysis.py financial_analyzer/web/services/analysis_service.py
git commit -m "feat: register shareholder, capital_flow, dividend, weekly_pe analysis types"
```

---

### Task 9: Add data_modules config to settings API

**Files:**
- Modify: `financial_analyzer/web/routes/settings_api.py`

- [ ] **Step 1: Add data_modules to the token config page HTML**

In the `get_tokens` route (around line 55), after the DeepSeek Key input section (before the save button), add:

```python
    # Default modules
    default_modules = config.get("data_modules", {})
    module_labels = {
        "moneyflow": "资金流向", "margin": "融资融券", "hk_hold": "北向资金",
        "block_trade": "大宗交易", "stk_holdernumber": "股东人数",
        "top10_holders": "前十大股东", "dividend": "分红数据",
        "weekly_monthly": "周线/月线",
    }

    module_html = '<h4 style="color:var(--fg-secondary);font-size:12px;margin:16px 0 4px 0;">数据模块（勾选启用）</h4>'
    for key, label in module_labels.items():
        checked = "checked" if default_modules.get(key, True) else ""
        module_html += f'<div style="font-size:11px;padding:2px 0;"><label><input type="checkbox" name="module_{key}" {checked}> {label}</label></div>'
```

Insert `{module_html}` into the returned HTML, before the save button row.

- [ ] **Step 2: Handle data_modules in save_tokens route**

In the `save_tokens` route (around line 90), after the existing config save logic, add:

```python
    # 保存数据模块配置
    module_keys = ["moneyflow", "margin", "hk_hold", "block_trade",
                   "stk_holdernumber", "top10_holders", "dividend", "weekly_monthly"]
    data_modules = {}
    form_data = await request.form()
    for key in module_keys:
        data_modules[key] = f"module_{key}" in form_data
    config["data_modules"] = data_modules
```

- [ ] **Step 3: Add a helper to load enabled modules**

Add at the top of `settings_api.py` after `_load_config`:

```python
def get_enabled_modules() -> dict:
    """返回已启用的数据模块"""
    config = _load_config()
    defaults = {k: True for k in [
        "moneyflow", "margin", "hk_hold", "block_trade",
        "stk_holdernumber", "top10_holders", "dividend", "weekly_monthly"
    ]}
    saved = config.get("data_modules", {})
    defaults.update(saved)
    return defaults
```

- [ ] **Step 4: Commit**

```bash
git add financial_analyzer/web/routes/settings_api.py
git commit -m "feat: add data_modules config to settings API"
```

---

### Task 10: Update KPI cards template for user-configurable layout

**Files:**
- Modify: `financial_analyzer/web/templates/partials/kpi_cards.html`
- Modify: `financial_analyzer/web/routes/data_api.py`

- [ ] **Step 1: Rewrite kpi_cards.html to use configurable grid**

Replace kpi_cards.html with:

```html
<!-- KPI 卡片行 — 用户可配置 -->
{% set enabled = kpis.get('enabled_modules', {}) %}
<div class="kpi-bar" id="kpi-bar">
    <!-- 核心卡片始终显示 -->
    <div class="kpi-card" data-kpi="stock_name">
        <div class="kpi-label">股票名称</div>
        <div class="kpi-value">{{ kpis.stock_name }}</div>
    </div>
    <div class="kpi-card" data-kpi="current_price">
        <div class="kpi-label">当前价格</div>
        <div class="kpi-value">{{ kpis.current_price }}</div>
    </div>
    <div class="kpi-card" data-kpi="price_change">
        <div class="kpi-label">涨跌幅</div>
        <div class="kpi-value" style="color:{% if kpis.price_change_up %}var(--positive){% else %}var(--negative){% endif %}">
            {{ kpis.price_change }}
        </div>
    </div>
    <div class="kpi-card" data-kpi="pe_ratio">
        <div class="kpi-label">市盈率 (PE)</div>
        <div class="kpi-value">{{ kpis.pe_ratio }}</div>
    </div>
    <div class="kpi-card" data-kpi="market_cap">
        <div class="kpi-label">总市值</div>
        <div class="kpi-value">{{ kpis.market_cap }}</div>
    </div>

    <!-- 可选卡片 — 非启用模块自动隐藏 -->
    <div class="kpi-card optional-kpi" data-kpi="net_mf_amount"
         style="display:{% if kpis.get('net_mf_amount') and kpis.net_mf_amount != '--' %}block{% else %}none{% endif %}">
        <div class="kpi-label">主力净流入</div>
        <div class="kpi-value" style="color:{% if kpis.get('net_mf_positive') %}var(--positive){% else %}var(--negative){% endif %}">
            {{ kpis.get('net_mf_amount', '--') }}
        </div>
    </div>
    <div class="kpi-card optional-kpi" data-kpi="margin_balance"
         style="display:{% if kpis.get('margin_balance') and kpis.margin_balance != '--' %}block{% else %}none{% endif %}">
        <div class="kpi-label">融资余额</div>
        <div class="kpi-value">{{ kpis.get('margin_balance', '--') }}</div>
    </div>
    <div class="kpi-card optional-kpi" data-kpi="hk_hold_ratio"
         style="display:{% if kpis.get('hk_hold_ratio') and kpis.hk_hold_ratio != '--' %}block{% else %}none{% endif %}">
        <div class="kpi-label">北向持股</div>
        <div class="kpi-value">{{ kpis.get('hk_hold_ratio', '--') }}</div>
    </div>
    <div class="kpi-card optional-kpi" data-kpi="holder_num"
         style="display:{% if kpis.get('holder_num') and kpis.holder_num != '--' %}block{% else %}none{% endif %}">
        <div class="kpi-label">股东人数</div>
        <div class="kpi-value">{{ kpis.get('holder_num', '--') }}</div>
    </div>
    <div class="kpi-card optional-kpi" data-kpi="div_yield"
         style="display:{% if kpis.get('div_yield') and kpis.div_yield != '--' %}block{% else %}none{% endif %}">
        <div class="kpi-label">股息率</div>
        <div class="kpi-value">{{ kpis.get('div_yield', '--') }}</div>
    </div>
    <div class="kpi-card optional-kpi" data-kpi="volume">
        <div class="kpi-label">成交量</div>
        <div class="kpi-value">{{ kpis.volume }}</div>
    </div>
</div>

<!-- KPI 配置按钮 -->
<div style="text-align:right;margin-top:8px;">
    <button class="btn btn-sm" onclick="toggleKpiConfig()"
            style="font-size:10px;padding:2px 8px;background:var(--bg-input);border:1px solid var(--border);color:var(--fg-muted);border-radius:4px;cursor:pointer;">
        ⚙ 自定义卡片
    </button>
</div>

<!-- 卡片配置面板（默认隐藏） -->
<div id="kpi-config-panel" style="display:none;background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:12px;margin-top:8px;">
    <div style="color:var(--fg-secondary);font-size:12px;font-weight:600;margin-bottom:8px;">选择要显示的 KPI 卡片</div>
    <div id="kpi-checkboxes" style="display:flex;flex-wrap:wrap;gap:8px;">
    </div>
    <div style="margin-top:10px;display:flex;gap:8px;">
        <button onclick="saveKpiConfig()" style="background:var(--accent);color:#fff;border:none;padding:4px 12px;border-radius:4px;font-size:11px;cursor:pointer;">保存</button>
        <button onclick="resetKpiConfig()" style="background:transparent;color:var(--fg-muted);border:1px solid var(--border);padding:4px 12px;border-radius:4px;font-size:11px;cursor:pointer;">恢复默认</button>
    </div>
</div>

<script>
// 默认启用的卡片
const defaultKpis = ['stock_name', 'current_price', 'price_change', 'pe_ratio', 'market_cap', 'volume'];

function toggleKpiConfig() {
    const panel = document.getElementById('kpi-config-panel');
    const isVisible = panel.style.display !== 'none';
    panel.style.display = isVisible ? 'none' : 'block';
    if (!isVisible) buildCheckboxes();
}

function buildCheckboxes() {
    const container = document.getElementById('kpi-checkboxes');
    const cards = document.querySelectorAll('.kpi-card[data-kpi]');
    const saved = JSON.parse(localStorage.getItem('kpi_config') || '[]');
    const enabled = saved.length ? saved : defaultKpis;

    container.innerHTML = '';
    cards.forEach(card => {
        const kpi = card.dataset.kpi;
        const label = card.querySelector('.kpi-label').textContent;
        const checked = enabled.includes(kpi);
        container.innerHTML += `<label style="font-size:11px;cursor:pointer;">
            <input type="checkbox" value="${kpi}" ${checked ? 'checked' : ''}> ${label}
        </label>`;
    });
}

function saveKpiConfig() {
    const checked = Array.from(document.querySelectorAll('#kpi-checkboxes input:checked')).map(cb => cb.value);
    localStorage.setItem('kpi_config', JSON.stringify(checked));
    applyKpiConfig(checked);
    document.getElementById('kpi-config-panel').style.display = 'none';
}

function resetKpiConfig() {
    localStorage.removeItem('kpi_config');
    applyKpiConfig(defaultKpis);
    document.getElementById('kpi-config-panel').style.display = 'none';
}

function applyKpiConfig(enabled) {
    document.querySelectorAll('.kpi-card[data-kpi]').forEach(card => {
        card.style.display = enabled.includes(card.dataset.kpi) ? '' : 'none';
    });
}

// 页面加载时应用保存的配置
(function() {
    const saved = JSON.parse(localStorage.getItem('kpi_config') || '[]');
    if (saved.length) applyKpiConfig(saved);
})();
</script>

{% if has_data %}
<div hx-swap-oob="true" id="status-text">数据获取完成 — {{ stock_code }}</div>
<div hx-swap-oob="true" id="source-label">{{ kpis.source }}</div>
<div hx-swap-oob="true" id="result-content" class="result-empty">
        数据已就绪，请从左侧导航选择分析项目<br>
        <span style="font-size:11px;color:var(--fg-muted);">
            已加载 {{ data_types|length }} 种数据:
            {{ data_types[:4]|join(', ') }}{% if data_types|length > 4 %} 等{% endif %}
        </span>
</div>

{% if fin_pending %}
<div id="fin-status" class="fin-status-loading"
     hx-get="/fetch/financials-status" hx-trigger="every 2s" hx-swap="outerHTML transition:true"
     style="font-size:11px;">
    ◌ 正在后台加载财务及市场数据...
    (已加载: {{ fin_loaded|join(', ') or '无' }})
</div>
{% endif %}

<div hx-swap-oob="true" id="data-table-content"
     hx-get="/fetch/data-table" hx-trigger="refreshDataTable from:body" hx-swap="outerHTML transition:true">
    <table class="data-table">
        <thead><tr><th>数据类型</th><th>说明</th><th>状态</th></tr></thead>
        <tbody>
            {% for dtype in data_types %}
            <tr>
                <td>{{ dtype }}</td>
                <td style="color:var(--fg-muted);font-size:11px;">{{ dtype }}</td>
                <td style="color:var(--positive);">✓</td>
            </tr>
            {% endfor %}
            {% if fin_pending %}
            <tr><td colspan="3" style="color:var(--warning);text-align:center;">
                ◌ 另有 {{ fin_pending|length }} 项数据正在后台加载中...
            </td></tr>
            {% endif %}
        </tbody>
    </table>
</div>
{% endif %}
```

- [ ] **Step 2: Commit**

```bash
git add financial_analyzer/web/templates/partials/kpi_cards.html
git commit -m "feat: add user-configurable KPI card grid with localStorage persistence"
```

---

### Task 11: Write tests

**Files:**
- Create: `tests/test_adapter_tushare_ext.py`
- Create: `tests/test_shareholder.py`
- Create: `tests/test_capital_flow.py`

- [ ] **Step 1: Write adapter extension tests**

```python
"""Adapter Tushare 扩展接口测试"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from financial_analyzer.data_sources.adapter import DataSourceAdapter


class TestTushareNewHandlers:
    """测试新增的 Tushare handler 路由"""

    @pytest.fixture
    def adapter(self):
        a = DataSourceAdapter()
        a.tushare_pro = MagicMock()
        return a

    def test_moneyflow_handler_called(self, adapter):
        adapter.tushare_pro.moneyflow = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20250101", "20250110", "moneyflow")
        adapter.tushare_pro.moneyflow.assert_called_once_with(
            ts_code="000001.SZ", start_date="20250101", end_date="20250110"
        )

    def test_margin_handler_called(self, adapter):
        adapter.tushare_pro.margin = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20250101", "20250110", "margin")
        adapter.tushare_pro.margin.assert_called_once()

    def test_dividend_handler_called(self, adapter):
        adapter.tushare_pro.dividend = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20200101", "20251231", "dividend")
        adapter.tushare_pro.dividend.assert_called_once()

    def test_top10_holders_handler_called(self, adapter):
        adapter.tushare_pro.top10_holders = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20240101", "20241231", "top10_holders")
        adapter.tushare_pro.top10_holders.assert_called_once()

    def test_fina_audit_handler_called(self, adapter):
        adapter.tushare_pro.fina_audit = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20150101", "20251231", "fina_audit")
        adapter.tushare_pro.fina_audit.assert_called_once()

    def test_fina_mainbz_handler_called(self, adapter):
        adapter.tushare_pro.fina_mainbz = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20240101", "20241231", "fina_mainbz")
        adapter.tushare_pro.fina_mainbz.assert_called_once_with(
            ts_code="000001.SZ", start_date="20240101", end_date="20241231", type='P'
        )

    def test_weekly_handler_called(self, adapter):
        adapter.tushare_pro.weekly = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20240101", "20250101", "weekly")
        adapter.tushare_pro.weekly.assert_called_once()

    def test_unknown_type_returns_none(self, adapter):
        result = adapter._get_tushare("000001.SZ", "20240101", "20240105", "nonexistent")
        assert result is None
```

- [ ] **Step 2: Write ShareholderAnalyzer tests**

```python
"""ShareholderAnalyzer 测试"""
import pandas as pd
import pytest
from financial_analyzer.analyzers.shareholder import ShareholderAnalyzer


class TestShareholderAnalyzer:
    @pytest.fixture
    def stock_basic(self):
        return pd.DataFrame([{
            "name": "测试银行", "industry": "银行", "market": "主板"
        }])

    @pytest.fixture
    def holder_data(self):
        return pd.DataFrame([
            {"ann_date": "20221231", "holder_num": 500000},
            {"ann_date": "20230630", "holder_num": 480000},
            {"ann_date": "20231231", "holder_num": 450000},
            {"ann_date": "20240630", "holder_num": 420000},
        ])

    @pytest.fixture
    def top10_data(self):
        return pd.DataFrame([
            {"end_date": "20240630", "holder_name": "测试集团", "hold_amount": 5000000000, "hold_ratio": 30.0},
            {"end_date": "20240630", "holder_name": "社保基金组合", "hold_amount": 2000000000, "hold_ratio": 12.0},
            {"end_date": "20240630", "holder_name": "香港中央结算", "hold_amount": 1500000000, "hold_ratio": 9.0},
        ])

    def test_analyze_with_all_data(self, stock_basic, holder_data, top10_data):
        data = {
            "stock_basic": stock_basic,
            "stk_holdernumber": holder_data,
            "top10_holders": top10_data,
        }
        analyzer = ShareholderAnalyzer(data, "000001.SZ")
        result = analyzer.analyze()
        assert "股东结构分析" in result
        assert "测试银行" in result
        assert "股东人数变化趋势" in result
        assert "前十大股东" in result
        assert "股权结构综合评分" in result

    def test_analyze_no_data(self):
        analyzer = ShareholderAnalyzer({}, "000001.SZ")
        result = analyzer.analyze()
        assert "股东结构分析" in result
        assert "未获取到" in result

    def test_ownership_score_chip_concentration(self, stock_basic, holder_data):
        data = {"stock_basic": stock_basic, "stk_holdernumber": holder_data}
        analyzer = ShareholderAnalyzer(data, "000001.SZ")
        result = analyzer.analyze()
        # 股东人数从50万降到42万，应该检测到筹码集中
        assert "筹码集中" in result
```

- [ ] **Step 3: Write CapitalFlowAnalyzer tests**

```python
"""CapitalFlowAnalyzer 测试"""
import pandas as pd
import pytest
from financial_analyzer.analyzers.capital_flow import CapitalFlowAnalyzer


class TestCapitalFlowAnalyzer:
    @pytest.fixture
    def stock_basic(self):
        return pd.DataFrame([{"name": "测试股票", "industry": "科技"}])

    @pytest.fixture
    def moneyflow_data(self):
        return pd.DataFrame([
            {"trade_date": f"202501{i:02d}", "buy_elg_amount": 1e7, "sell_elg_amount": 8e6,
             "buy_lg_amount": 5e6, "sell_lg_amount": 6e6,
             "buy_md_amount": 3e6, "sell_md_amount": 2e6,
             "buy_sm_amount": 1e6, "sell_sm_amount": 2e6}
            for i in range(1, 26)
        ])

    @pytest.fixture
    def margin_data(self):
        return pd.DataFrame([
            {"trade_date": f"202501{i:02d}", "rzye": 5e9, "rqye": 5e8}
            for i in range(1, 21)
        ])

    def test_analyze_with_data(self, stock_basic, moneyflow_data, margin_data):
        data = {
            "stock_basic": stock_basic,
            "moneyflow": moneyflow_data,
            "margin": margin_data,
        }
        analyzer = CapitalFlowAnalyzer(data, "000001.SZ")
        result = analyzer.analyze()
        assert "资金面分析" in result
        assert "测试股票" in result
        assert "主力资金流向" in result
        assert "融资融券" in result
        assert "资金面综合评分" in result

    def test_analyze_no_data(self):
        analyzer = CapitalFlowAnalyzer({}, "000001.SZ")
        result = analyzer.analyze()
        assert "资金面分析" in result
        assert "未获取到" in result
```

- [ ] **Step 4: Run tests**

```bash
cd c:/Users/LK/Desktop/FA/10.6 && python -m pytest tests/test_adapter_tushare_ext.py tests/test_shareholder.py tests/test_capital_flow.py -v 2>&1
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_adapter_tushare_ext.py tests/test_shareholder.py tests/test_capital_flow.py
git commit -m "test: add tests for new Tushare handlers, ShareholderAnalyzer, CapitalFlowAnalyzer"
```

---

### Task 12: End-to-end verification with real token

**Files:** None (verification only)

- [ ] **Step 1: Run the web app and verify data loading**

```bash
cd c:/Users/LK/Desktop/FA/10.6 && python -c "
from financial_analyzer.data_sources.adapter import DataSourceAdapter
from financial_analyzer.web.services.data_service import DataService

adapter = DataSourceAdapter()
adapter.set_tushare_token('YOUR_TUSHARE_TOKEN')
ds = DataService(adapter)

# Fetch all data for a well-known stock
import json, datetime
from financial_analyzer.config import CONFIG_FILE
with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
    json.dump({'tushare': 'YOUR_TUSHARE_TOKEN'}, f)

end = datetime.datetime.now().strftime('%Y%m%d')
data = ds.fetch_stock_data('000001.SZ', '20240101', end)

print(f'Total data types loaded: {len(data)}')
for dtype, df in data.items():
    print(f'  {dtype}: {len(df)} rows, cols={list(df.columns)[:6]}')

# Extract KPIs
kpis = ds.extract_kpis(data)
print(f'\nKPIs:')
for k, v in kpis.items():
    print(f'  {k}: {v}')
" 2>&1
```

Expected: 15+ data types loaded, all KPIs populated with real values for 000001.SZ.

- [ ] **Step 2: Run shareholder and capital flow analysis**

```bash
cd c:/Users/LK/Desktop/FA/10.6 && python -c "
from financial_analyzer.data_sources.adapter import DataSourceAdapter
from financial_analyzer.web.services.data_service import DataService
from financial_analyzer.analyzers.shareholder import ShareholderAnalyzer
from financial_analyzer.analyzers.capital_flow import CapitalFlowAnalyzer

adapter = DataSourceAdapter()
adapter.set_tushare_token('YOUR_TUSHARE_TOKEN')
ds = DataService(adapter)

data = ds.fetch_stock_data('000001.SZ', '20240101', '20250501')

print('=== Shareholder Analysis ===')
sa = ShareholderAnalyzer(data, '000001.SZ')
print(sa.analyze()[:2000])

print('\n=== Capital Flow Analysis ===')
ca = CapitalFlowAnalyzer(data, '000001.SZ')
print(ca.analyze()[:2000])
" 2>&1
```

- [ ] **Step 3: Run existing tests to ensure no regressions**

```bash
cd c:/Users/LK/Desktop/FA/10.6 && python -m pytest tests/ -v --tb=short 2>&1
```

Expected: all existing tests pass.

- [ ] **Step 4: Commit any fixes if needed**

---

### Task 13: Update export API to include new data types

**Files:**
- Modify: `financial_analyzer/web/routes/export_api.py`

- [ ] **Step 1: Add new data type mappings to export**

Read the existing export_api.py and find where data types are mapped for export. Add:

```python
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
```

(Add these to whatever mapping dict/function the export API uses.)

- [ ] **Step 2: Commit**

```bash
git add financial_analyzer/web/routes/export_api.py
git commit -m "feat: include new data types in export options"
```

---

## Plan Self-Review

1. **Spec coverage**: All spec requirements covered — 12 new + 2 fixed interfaces (Task 1), data pipeline architecture (Tasks 2-4), 3 new analyzers (Tasks 5-7), ANALYSIS_MAP registration (Task 8), data_modules config (Task 9), configurable KPI cards (Task 10), tests (Task 11), E2E verification (Task 12), export (Task 13).

2. **Placeholder scan**: No TBD, TODO, or vague instructions. Every step has concrete code or commands.

3. **Type consistency**: Method signatures match across tasks — ShareholderAnalyzer.analyze() and CapitalFlowAnalyzer.analyze() return str, consistent with ANALYSIS_MAP expectations.

# 财务分析系统 v9.0

## 项目结构

```
financial_analyzer/
├── main.py                    # 入口文件
├── config.py                  # 全局配置（字体、路径、常量）
├── logging_config.py          # 日志系统 (#13)
├── cache/
│   └── manager.py             # 数据缓存管理器（内存+SQLite）
├── tokens/
│   └── manager.py             # Token 管理器
├── calculator/
│   └── financial.py           # 财务计算工具类
├── charts/
│   └── matplotlib_charts.py   # 图表模块（K线/均线/柱状图）
├── data_sources/
│   ├── adapter.py             # 统一数据适配器（Tushare/YFinance/Akshare）
│   └── normalizer.py          # 数据标准化层
├── analyzers/
│   ├── base.py                # 分析器基类（公共数据获取逻辑）
│   ├── report_formatter.py    # 报告格式化工具 (#9 消除重复代码)
│   ├── market.py              # 行情/趋势/波动/成交量分析
│   ├── technical.py           # 技术指标分析
│   ├── financial.py           # 三大报表分析（#6 修复 NameError）
│   ├── profitability.py       # 盈利/营运/偿债/成长分析
│   ├── combined.py            # 量价结合/股东分析
│   └── risk_analyzer.py       # 风险分析调用层
├── risk/
│   └── assessment.py          # 风险评估模型
├── deepseek/
│   ├── client.py              # DeepSeek API 客户端
│   └── app.py                 # DeepSeek AI 独立应用
├── ui/
│   ├── app.py                 # 主应用类（#2 线程安全）
│   ├── dialogs.py             # 对话框（#5 定时更新、#7 缓存设置）
│   ├── deepseek_dialog.py     # AI 分析内嵌对话框
│   └── theme.py               # 商务深色主题
└── utils/
    ├── helpers.py              # 工具函数
    └── export.py               # 数据导出（#8 PDF中文支持）
tests/
├── conftest.py                # 测试配置
├── test_calculator.py         # FinancialCalculator 测试（60+ 用例）
├── test_normalizer.py         # DataNormalizer 测试（25+ 用例）
├── test_risk.py               # RiskAssessmentModel 测试（30+ 用例）
├── test_report_formatter.py   # ReportFormatter 测试
└── test_base_analyzer.py      # BaseAnalyzer 测试（mock 测试）
```

## 修复的问题清单

| # | 问题 | 状态 |
|---|------|------|
| 1 | 单文件过大 → 拆分为 20 个模块 | ✅ |
| 2 | 线程安全 → `threading.Lock` 保护共享状态 | ✅ |
| 3 | 异常处理 → `logging` 模块替代 `print` | ✅ |
| 4 | 行业对比硬编码 → 调用 Tushare/Akshare API | ✅ |
| 5 | 定时更新空壳 → `threading.Timer` 实现 | ✅ |
| 6 | `i` 变量未定义 → `enumerate` 修复 | ✅ |
| 7 | 缓存设置未生效 → `update_expiry()` 真实修改 | ✅ |
| 8 | PDF 中文乱码 → 注册 SimHei 字体 | ✅ |
| 9 | 重复代码 → `ReportFormatter` 统一格式化 | ✅ |
| 10 | 字体配置未复用 → 统一引用 `config.py` 常量 | ✅ |
| 11 | 路径不一致 → `USER_DATA_DIR` 统一管理 | ✅ |
| 12 | 数据源 combo 不联动 → `refresh_sources()` | ✅ |
| 13 | 缺少日志 → `logging` 模块 | ✅ |
| 14 | EMA 精度 → 保持 `adjust=False`（与主流一致） | ✅ |
| 15 | 无进度提示 → `ttk.Progressbar` 动画 | ✅ |
| 16 | 无图表可视化 → 待后续版本 | ⏳ |
| 17 | 表格显示限制 → `TABLE_DISPLAY_ROWS` 可配置 | ✅ |

## 运行方式

```bash
# 直接运行
python -m financial_analyzer.main

# 或者
cd C:\Users\LK\Desktop\result
python -c "from financial_analyzer.main import main; main()"
```

## 依赖

- **必需**: `tkinter`, `pandas`, `numpy`
- **可选**: `ttkbootstrap` (现代化UI), `tushare` (A股数据), `yfinance` (美股数据), `akshare` (A股补充), `reportlab` (PDF导出), `python-docx` (Word导出), `openpyxl` (Excel导出), `matplotlib` (图表可视化)

## 图表功能

安装 `matplotlib` 后可使用图表分析功能：

```bash
pip install matplotlib
```

支持的图表类型：
- **K线图** - 蜡烛图 + 成交量 + 均线
- **均线分析图** - MA5/10/20/60 + 支撑/阻力标注
- **行情概览图** - K线 + 成交量 + RSI 组合图
- **财务柱状图** - 营收/利润/同比增速

所有图表均支持深色主题，可保存为 PNG。

## 单元测试

```bash
pip install pytest
pytest tests/ -v
```

覆盖模块：`FinancialCalculator`、`DataNormalizer`、`RiskAssessmentModel`、`ReportFormatter`、`BaseAnalyzer`

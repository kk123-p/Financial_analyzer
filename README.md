# Financial Analyzer Pro — 财务自动化分析系统

> 基于 FastAPI + DeepSeek AI 的上市公司财务分析与多因子量化交易平台。浏览器即用，覆盖「数据获取 → 财务体检 → 深度诊断 → AI 投研 → 量化回测 → 模拟交易」完整闭环。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)

---

## ✨ 核心特性

### 📊 财务分析引擎（6 阶段 34 项递进式分析管线）

1. **数据概览** — 行情概览、价格趋势、量价结合
2. **财务体检** — 资产负债表 / 利润表 / 现金流量表分析、财务比率、趋势评分
3. **股东与资金** — 股东结构、资金面、分红分析、周线 PE 分位
4. **深度诊断** — 杜邦分析（含 ROIC）、现金流分析、护城河评估、综合深度报告
5. **风险审查** — 综合审计、ML 舞弊检测、四大审计信号、Z/F/M-score、风险评估
6. **估值评级** — 综合投资评级、PE 估值与历史分位、PB-ROE、EV/EBITDA、股东回报

### 🤖 DeepSeek AI 投研助手

- **快速问答**：对持仓或关注标的即时提问
- **深度分析**（`/deep`）：基于财务数据 + 哈佛分析框架的多维度剖析
- **三方辩论**（`/debate`）：格雷厄姆价值派 × 费雪成长派 × 塔勒布风控派三轮交锋，产出共识与情景概率
- **工具调用**：AI 可实时调用数据查询工具获取真实财务数据并交叉验证
- **Prompt 实验室**：可视化编辑 / 导入导出 / 预览分析模板
- 支持推理模式（thinking mode）、流式输出、多轮追问

### 📈 多因子量化交易

- **7 大类因子**：价值 / 质量 / 成长 / 动量 / 情绪 / 低波 / 风险（30+ 因子）
- **选股信号**：覆盖沪深300 / 中证500 / 中证800 / 创业板指 / 科创50，每月末自动调仓
- **因子分析**：IC/IR 排名、因子衰减、相关性矩阵、综合评分
- **回测引擎**：累计收益、年化、夏普、最大回撤、胜率、波动率、Calmar、月度热力图、基准对比、滚动 Alpha/Beta
- **敏感性分析** / **自动权重优化**（训练/测试期分离防过拟合）/ **批量回测对比**
- **模拟交易**：账户初始化、信号执行、盈亏曲线、持仓分布、交易台账

### 🔌 多数据源

Tushare Pro · Akshare · 新浪财经 · Yahoo Finance，统一适配器 + 标准化层，支持缓存（内存 + SQLite）。

### 📤 数据导出

Excel (.xlsx) · CSV · JSON · PDF · Word · Markdown · HTML。

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows / macOS / Linux

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/kk123-p/Financial_analyzer.git
cd Financial_analyzer

# 2. 创建并激活虚拟环境（推荐）
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-web.txt
```

### 运行

```bash
# 方式一：模块入口
python -m financial_analyzer

# 方式二：启动脚本（Windows 双击 run_web.bat）
python run_web.py

# 方式三：桌面启动器（自动打开浏览器）
python launcher.py
```

启动后访问 **http://127.0.0.1:8000**

### 配置

首次使用点击左下角 **「Token 配置」**：

| 配置项 | 说明 | 获取地址 |
| --- | --- | --- |
| Tushare Pro Token | A 股行情与财务数据（必需） | <https://tushare.pro> |
| DeepSeek API Key | AI 投研问答（可选） | <https://platform.deepseek.com> |

配置保存在 `~/.financialanalyzer/config.json`。

---

## 🧭 项目结构

```text
financial_analyzer/
├── web/                    # FastAPI Web 应用
│   ├── main.py             # 应用工厂 + 生命周期管理
│   ├── routes/             # 路由（数据/分析/图表/AI/量化/回测/模拟交易/导出/设置）
│   ├── services/           # Web 层服务
│   ├── templates/          # Jinja2 模板
│   └── static/             # CSS / JS / ECharts 图表
├── analyzers/              # 财务分析器（三表/比率/杜邦/审计/股东/资金）
├── calculator/             # 财务计算（DCF/评分/情景/审计引擎）
├── quant/                  # 量化交易引擎
│   ├── factors/            # 7 大类因子
│   ├── engine/             # 信号/排序/打分/优化/仓位
│   ├── backtest/           # 回测引擎 + 绩效归因
│   └── paper_trading/      # 模拟交易（组合/盈亏/台账）
├── ai/                     # AI 编排（调度/辩论/提示词/工具/输出解析）
├── deepseek/               # DeepSeek API 客户端
├── pipeline/textbook/      # 教科书算法（Ch5-Ch13：比率/趋势/杜邦/舞弊ML）
├── risk/                   # 风险评估模型
├── data_sources/           # 多数据源适配器 + 标准化
├── cache/                  # 缓存管理（内存 + SQLite）
├── charts/                 # matplotlib 图表（K线/均线/柱状）
├── utils/                  # 工具函数（导出 PDF/Word/Excel）
└── config.py               # 全局配置
```

---

## 🧪 测试

```bash
pip install pytest
pytest tests/ -v
```

覆盖 50+ 模块：财务计算、数据标准化、风险评估、量化因子、回测指标、AI 编排、输出解析、提示词框架等。

---

## 📦 打包为可执行文件

```bash
# Windows 下使用 PyInstaller 打包
build.bat
```

产出 `dist/FinancialAnalyzerPro/` 目录及 `FinancialAnalyzerPro.zip`，解压后双击 `FinancialAnalyzerPro.exe` 即可运行。

---

## ⚠️ 免责声明

本项目仅供学习与技术研究使用，不构成任何投资建议。量化回测结果基于历史数据，不代表未来表现。使用者应自行承担投资决策的全部风险与责任。

---

## 📄 License

[MIT License](LICENSE) © 2026 KK123-P and contributors

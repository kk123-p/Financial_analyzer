# 版本 10.6 改动说明

## 改动日期
2026-05-14 23:14

## 改动内容

### 1. 行业对比/估值等结果排版修复
- **问题**：返回结果中的 `\n` 变成了字面量，没有实际换行
- **根因**：`_format_dict_result` 不认识 Phase2Analyzer 的返回格式，用 `json.dumps` 序列化导致换行符被转义
- **修复**：新增对 Phase2Analyzer 返回格式的识别，直接拼接字符串而非 JSON 序列化

### 2. 估值分析数据源修复
- **问题**：估值分析使用 `basic` 表获取股价，但 tushare 的 `basic` 是财务指标表，不含股价
- **修复**：
  - 新增 `_get_price_data()` 方法，优先从 `daily` 表获取股价数据，退而从 `basic` 获取
  - 所有需要股价/股本的方法改用 `_get_price_data()`
  - 补充 `basic_eps`、`total_share_y` 等 tushare 实际列名的别名映射

## 修改文件
- `financial_analyzer/ui/app.py`
- `financial_analyzer/analyzers/phase2_analysis.py`

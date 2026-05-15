# 版本 10.4 改动说明

## 改动日期
2026-05-14 22:44

## 改动内容

### 1. Phase2Analyzer 估值计算修复与输出美化
- **问题**：PE/PB/EV_EBITDA 计算为0，数据单位不匹配（万元vs元）；输出为原始JSON可读性差
- **修改**：
  - 修复单位换算问题
  - 输出改为结构化文本（带分析结论），而非原始JSON
  - 行业对比改为基于财务指标的横向自我评估
  - 财报质量增加实质性分析

### 2. 数据标签页新增审计意见和主营业务构成
- **修改**：在数据标签页的下拉菜单中新增 audit_opinion（审计意见）和 main_business（主营业务构成）数据类型

## 修改文件
- `financial_analyzer/analyzers/phase2_analysis.py`
- `financial_analyzer/ui/app.py`

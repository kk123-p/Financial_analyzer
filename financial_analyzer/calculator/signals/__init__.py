"""
审计信号包 - 导入所有信号模块以触发注册
==========================================
使用时只需 import signals 即可自动注册全部信号。
"""
from ..audit_engine import (
    Signal, SignalLevel, SignalCategory, SignalCategory as SC,
    SignalRegistry, AuditEngine, AuditResult, DimensionScore,
    AuditThresholds, DEFAULT_THRESHOLDS,
    CATEGORY_NAMES, CATEGORY_ICONS, LEVEL_ICONS,
)

# 导入所有信号模块 → 触发 @SignalRegistry.register 装饰器
from . import signals_asset       # 资产端 8个信号
from . import signals_profit      # 利润端 4个信号
from . import signals_cashflow    # 现金流 4个信号
from . import signals_cross       # 勾稽验证 5个信号
from . import signals_governance  # 治理与披露 5个信号
from . import signals_model       # 模型预警 6个信号

__all__ = [
    "Signal", "SignalLevel", "SignalCategory",
    "SignalRegistry", "AuditEngine", "AuditResult", "DimensionScore",
    "AuditThresholds", "DEFAULT_THRESHOLDS",
    "CATEGORY_NAMES", "CATEGORY_ICONS", "LEVEL_ICONS",
]

"""
审计引擎核心框架 - 插件式信号注册系统
=============================================
提供 Signal 基类、SignalRegistry 注册表、AuditEngine 引擎。
所有审计信号以函数形式注册，返回 Signal 对象或 None。
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
from ..logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

class SignalLevel(str, Enum):
    """信号风险等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SignalCategory(str, Enum):
    """信号分类维度"""
    ASSET = "asset"                        # 资产端
    PROFIT = "profit"                      # 利润端
    CASHFLOW = "cashflow"                  # 现金流
    CROSS_VALIDATION = "cross_validation"  # 勾稽验证
    GOVERNANCE = "governance"              # 治理与披露
    MODEL = "model"                        # 模型信号(M-score/Z-score等)


# 分类中文名映射
CATEGORY_NAMES = {
    SignalCategory.ASSET: "资产端信号",
    SignalCategory.PROFIT: "利润端信号",
    SignalCategory.CASHFLOW: "现金流信号",
    SignalCategory.CROSS_VALIDATION: "勾稽验证信号",
    SignalCategory.GOVERNANCE: "治理与披露信号",
    SignalCategory.MODEL: "模型预警信号",
}

CATEGORY_ICONS = {
    SignalCategory.ASSET: "📦",
    SignalCategory.PROFIT: "💰",
    SignalCategory.CASHFLOW: "💸",
    SignalCategory.CROSS_VALIDATION: "🔗",
    SignalCategory.GOVERNANCE: "🏛️",
    SignalCategory.MODEL: "🧮",
}

LEVEL_ICONS = {
    SignalLevel.HIGH: "🔴",
    SignalLevel.MEDIUM: "🟡",
    SignalLevel.LOW: "🟢",
    SignalLevel.INFO: "ℹ️",
}

LEVEL_WEIGHTS = {
    SignalLevel.HIGH: 10,
    SignalLevel.MEDIUM: 5,
    SignalLevel.LOW: 2,
    SignalLevel.INFO: 0,
}


@dataclass
class Signal:
    """单个审计信号"""
    id: str                                 # 唯一标识
    name: str                               # 信号名称
    category: SignalCategory                # 所属分类
    level: SignalLevel                      # 风险等级
    value: str                              # 当前值描述
    threshold: str                          # 阈值/标准描述
    conclusion: str                         # 结论
    detail: str = ""                        # 补充说明
    raw_value: Optional[float] = None       # 原始数值(用于可视化)
    threshold_value: Optional[float] = None # 阈值数值(用于可视化)


@dataclass
class DimensionScore:
    """单维度评分"""
    category: SignalCategory
    score: float          # 0-100
    signals: list         # 该维度下的信号列表
    details: list = field(default_factory=list)   # 检测数据明细


@dataclass
class AuditResult:
    """审计总结果"""
    total_score: float                          # 综合得分 0-100
    risk_level: str                             # 风险等级
    risk_icon: str                              # 风险图标
    all_signals: list[Signal]                   # 所有触发的信号
    dimensions: dict[str, DimensionScore]       # 各维度评分
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    recommendations: list[str] = field(default_factory=list)

    # 可视化数据
    radar_data: dict = field(default_factory=dict)     # 雷达图数据
    heatmap_data: list = field(default_factory=list)   # 热力图数据


# ============================================================================
# 信号函数类型
# ============================================================================

# SignalFunc: 接收 (current, previous, context) 返回 Signal 或 None
# current: 当前期数据 dict
# previous: 上期数据 dict (可能为 None)
# context: 额外上下文 {"stock_code", "basic_info", "zscore", "mscore", ...}
SignalFunc = Callable[[dict, Optional[dict], dict], Optional[Signal]]


# ============================================================================
# 信号注册表
# ============================================================================

class SignalRegistry:
    """信号注册表 - 管理所有审计信号"""

    _signals: dict[str, SignalFunc] = {}
    _metadata: dict[str, dict] = {}

    @classmethod
    def register(cls, signal_id: str, category: SignalCategory,
                 name: str, description: str = ""):
        """
        装饰器：注册一个信号函数

        用法:
            @SignalRegistry.register("my_signal", SignalCategory.ASSET, "我的信号")
            def check_something(current, previous, context):
                ...
                return Signal(...) or None
        """
        def decorator(func: SignalFunc) -> SignalFunc:
            cls._signals[signal_id] = func
            cls._metadata[signal_id] = {
                "id": signal_id,
                "category": category,
                "name": name,
                "description": description,
            }
            return func
        return decorator

    @classmethod
    def get_all(cls) -> dict[str, SignalFunc]:
        return cls._signals.copy()

    @classmethod
    def get_by_category(cls, category: SignalCategory) -> dict[str, SignalFunc]:
        return {
            sid: func for sid, func in cls._signals.items()
            if cls._metadata.get(sid, {}).get("category") == category
        }

    @classmethod
    def get_metadata(cls, signal_id: str) -> dict:
        return cls._metadata.get(signal_id, {})

    @classmethod
    def list_signals(cls) -> list[dict]:
        return list(cls._metadata.values())

    @classmethod
    def clear(cls):
        """清空注册表（测试用）"""
        cls._signals.clear()
        cls._metadata.clear()


# ============================================================================
# 阈值配置
# ============================================================================

@dataclass
class AuditThresholds:
    """审计信号阈值配置 - 用户可自定义"""
    # 资产端
    cash_debt_cash_ratio: float = 0.20        # 存贷双高：现金/总资产
    cash_debt_debt_ratio: float = 0.30        # 存贷双高：有息负债/总资产
    ar_revenue_gap: float = 0.20              # 应收异常：应收增速-营收增速
    inventory_cost_gap: float = 0.30          # 存货异常：存货增速-成本增速
    goodwill_equity_ratio: float = 0.30       # 商誉/净资产
    cip_asset_ratio: float = 0.15             # 在建工程/总资产
    cip_growth: float = 0.30                  # 在建工程增速
    prepayment_asset_ratio: float = 0.10      # 预付/总资产

    # 利润端
    profit_cf_ratio: float = 0.50             # 经营CF/净利润(3年均值)
    gross_margin_high: float = 0.60           # 异常高毛利率
    non_recurring_profit_ratio: float = 0.50  # 非经常性损益/净利润

    # 现金流
    revenue_cash_receipt: float = 0.70        # 销售回款/营收

    # 勾稽验证
    rev_growth_threshold: float = 0.30        # 收入增速触发阈值
    asset_growth_low: float = 0.05            # 资产增速过低
    tax_rate_low: float = 0.10                # 有效税率过低

    # 新增信号阈值
    interest_income_rate: float = 0.02        # 利息收入/货币资金(低于此为异常)
    ar_aging_high_ratio: float = 0.30         # 长账龄应收占比
    cf_structure_years: int = 5               # 现金流结构分析年数
    vat_burden_low: float = 0.03              # 增值税税负率过低

    @classmethod
    def from_dict(cls, d: dict) -> "AuditThresholds":
        """从字典加载，忽略未知键"""
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in valid})

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in self.__dataclass_fields__.values()}


# 全局默认阈值实例
DEFAULT_THRESHOLDS = AuditThresholds()


# ============================================================================
# 审计引擎
# ============================================================================

class AuditEngine:
    """
    审计引擎 - 运行所有注册信号，计算评分，生成结果

    用法:
        engine = AuditEngine(current_period, previous_period, context)
        result = engine.run()
    """

    # 各维度权重(总和=1.0)
    DIMENSION_WEIGHTS = {
        SignalCategory.ASSET: 0.25,
        SignalCategory.PROFIT: 0.25,
        SignalCategory.CASHFLOW: 0.15,
        SignalCategory.CROSS_VALIDATION: 0.15,
        SignalCategory.GOVERNANCE: 0.10,
        SignalCategory.MODEL: 0.10,
    }

    def __init__(self, current: dict, previous: dict | None = None,
                 context: dict | None = None,
                 thresholds: AuditThresholds | None = None):
        """
        Args:
            current: 当前期财务数据 dict
            previous: 上期财务数据 dict (可选)
            context: 额外上下文 {"stock_code", "basic_info", "zscore", "mscore", ...}
            thresholds: 用户自定义阈值
        """
        self.current = current or {}
        self.previous = previous or {}
        self.context = context or {}
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def run(self) -> AuditResult:
        """运行全部信号检测，返回审计结果"""
        all_signals: list[Signal] = []
        dimension_signals: dict[str, list[Signal]] = {
            cat.value: [] for cat in SignalCategory
        }
        # 记录所有被检查但未触发的信号
        checked_normal: dict[str, list[str]] = {cat.value: [] for cat in SignalCategory}

        # 注入阈值到context
        ctx = {**self.context, "thresholds": self.thresholds}

        # 依次运行所有注册信号
        for signal_id, func in SignalRegistry.get_all().items():
            meta = SignalRegistry.get_metadata(signal_id)
            cat_val = meta.get("category", SignalCategory.CROSS_VALIDATION).value
            sig_name = meta.get("name", signal_id)
            try:
                sig = func(self.current, self.previous, ctx)
                if sig is not None:
                    all_signals.append(sig)
                    dimension_signals[sig.category.value].append(sig)
                else:
                    checked_normal[cat_val].append(sig_name)
            except Exception as e:
                logger.warning(f"信号 {signal_id} 检测异常: {e}")
                checked_normal[cat_val].append(f"{sig_name}(检测异常)")

        # 计算各维度评分
        dimensions = {}
        for cat in SignalCategory:
            sigs = dimension_signals[cat.value]
            normal_list = checked_normal[cat.value]
            score = self._calc_dimension_score(sigs)
            details = self._build_dimension_details(sigs, normal_list)
            dimensions[cat.value] = DimensionScore(
                category=cat, score=score, signals=sigs, details=details
            )

        # 计算综合得分
        total_score = self._calc_total_score(dimensions)

        # 统计
        high_count = sum(1 for s in all_signals if s.level == SignalLevel.HIGH)
        medium_count = sum(1 for s in all_signals if s.level == SignalLevel.MEDIUM)
        low_count = sum(1 for s in all_signals if s.level == SignalLevel.LOW)

        # 风险等级
        risk_level, risk_icon = self._calc_risk_level(total_score, high_count, medium_count)

        # 生成建议
        recommendations = self._build_recommendations(all_signals, high_count, medium_count)

        # 构建可视化数据
        radar_data = self._build_radar_data(dimensions)
        heatmap_data = self._build_heatmap_data(all_signals)

        return AuditResult(
            total_score=total_score,
            risk_level=risk_level,
            risk_icon=risk_icon,
            all_signals=all_signals,
            dimensions=dimensions,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            recommendations=recommendations,
            radar_data=radar_data,
            heatmap_data=heatmap_data,
        )

    def _calc_dimension_score(self, signals: list[Signal]) -> float:
        """
        计算单维度得分：满分100，每个信号按等级扣分
        - HIGH: 扣20分
        - MEDIUM: 扣10分
        - LOW: 扣4分
        无信号=满分
        """
        score = 100.0
        for sig in signals:
            if sig.level == SignalLevel.HIGH:
                score -= 20
            elif sig.level == SignalLevel.MEDIUM:
                score -= 10
            elif sig.level == SignalLevel.LOW:
                score -= 4
        return max(0.0, score)

    def _calc_total_score(self, dimensions: dict[str, DimensionScore]) -> float:
        """加权计算综合得分"""
        total = 0.0
        for cat_str, dim in dimensions.items():
            try:
                cat = SignalCategory(cat_str)
                weight = self.DIMENSION_WEIGHTS.get(cat, 0)
                total += dim.score * weight
            except ValueError:
                continue
        return round(total, 1)

    def _calc_risk_level(self, score: float, high: int, medium: int) -> tuple[str, str]:
        """综合风险等级判定"""
        if high >= 3 or score < 30:
            return "高风险", "🔴"
        elif high >= 1 or medium >= 3 or score < 50:
            return "较高风险", "🟠"
        elif medium >= 1 or score < 70:
            return "中风险", "🟡"
        else:
            return "低风险", "🟢"

    def _build_dimension_details(self, signals: list[Signal], normal_checks: list[str] = None) -> list[str]:
        """构建维度明细数据 - 包括异常信号和正常检测项"""
        details = []
        for sig in signals:
            icon = LEVEL_ICONS.get(sig.level, "⚪")
            details.append(f"{icon} {sig.name}: {sig.value} (标准: {sig.threshold})")
        if normal_checks:
            for name in normal_checks:
                details.append(f"✅ {name}: 检测通过")
        if not details:
            details.append("⚠️ 该维度无可用检测项（数据不足）")
        return details

    def _build_recommendations(self, signals: list[Signal],
                               high: int, medium: int) -> list[str]:
        """生成排查建议"""
        recs = []
        if high > 0:
            recs.append("⚠️ 存在高风险信号，建议重点核查以下方面：")
            seen_categories = set()
            for sig in signals:
                if sig.level == SignalLevel.HIGH and sig.category not in seen_categories:
                    seen_categories.add(sig.category)
                    recs.append(f"  · [{CATEGORY_NAMES[sig.category]}] {sig.name}")
            recs.append("  · 建议对比同行业公司指标，审查关联交易和非经常性损益")
        elif medium > 0:
            recs.append("○ 存在中等风险信号，建议持续关注相关指标变化趋势")
        else:
            total_checked = len(SignalRegistry.list_signals())
            recs.append(f"✓ 共执行 {total_checked} 个检测项，各项指标均正常，未发现明显财务异常")
        return recs

    def _build_radar_data(self, dimensions: dict[str, DimensionScore]) -> dict:
        """构建雷达图数据"""
        data = {}
        for cat in SignalCategory:
            dim = dimensions.get(cat.value)
            if dim:
                data[CATEGORY_NAMES[cat]] = dim.score
        return data

    def _build_heatmap_data(self, signals: list[Signal]) -> list[dict]:
        """构建热力图数据"""
        data = []
        for sig in signals:
            data.append({
                "id": sig.id,
                "name": sig.name,
                "category": CATEGORY_NAMES.get(sig.category, sig.category.value),
                "level": sig.level.value,
                "weight": LEVEL_WEIGHTS.get(sig.level, 0),
            })
        return data

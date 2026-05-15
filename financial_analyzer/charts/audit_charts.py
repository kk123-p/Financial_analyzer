"""
审计可视化模块
================
生成雷达图、信号热力图等可视化图表。
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path
from ..logging_config import get_logger

logger = get_logger(__name__)

# 中文字体
_CN_FONTS = ['Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC']


def _get_cn_font():
    for name in _CN_FONTS:
        if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
            return name
    return 'sans-serif'


def _setup_plt():
    plt.rcParams['font.sans-serif'] = [_get_cn_font()]
    plt.rcParams['axes.unicode_minus'] = False


def generate_radar_chart(radar_data: dict, title: str = "审计风险雷达图",
                         save_path: str = None) -> str:
    """
    生成雷达图

    Args:
        radar_data: {维度名: 分数} dict
        title: 图表标题
        save_path: 保存路径（None则自动生成）

    Returns:
        保存的文件路径
    """
    _setup_plt()

    if not radar_data:
        return None

    categories = list(radar_data.keys())
    values = list(radar_data.values())
    N = len(categories)

    if N < 3:
        return None

    # 计算角度
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values_plot = values + [values[0]]  # 闭合
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')

    # 绘制雷达区域
    ax.fill(angles, values_plot, alpha=0.25, color='#00d4ff')
    ax.plot(angles, values_plot, 'o-', linewidth=2, color='#00d4ff', markersize=8)

    # 设置标签
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, size=11, color='#e0e0e0')

    # 设置径向范围
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], size=8, color='#888')
    ax.yaxis.grid(True, color='#333', linestyle='--', alpha=0.5)
    ax.xaxis.grid(True, color='#333', linestyle='--', alpha=0.5)

    # 添加阈值线 (60分 = 中风险)
    threshold_vals = [60] * N + [60]
    ax.plot(angles, threshold_vals, '--', linewidth=1, color='#ff6b6b', alpha=0.6, label='风险阈值(60)')

    # 标注分数
    for angle, value, cat in zip(angles[:-1], values, categories):
        color = '#4CAF50' if value >= 70 else '#FF9800' if value >= 50 else '#F44336'
        ax.annotate(f'{value:.0f}', xy=(angle, value), fontsize=10,
                    fontweight='bold', color=color, ha='center', va='bottom',
                    xytext=(0, 10), textcoords='offset points')

    ax.set_title(title, size=16, color='#e0e0e0', pad=20, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9,
              facecolor='#1a1a2e', edgecolor='#333', labelcolor='#e0e0e0')

    # 隐藏外圈
    ax.spines['polar'].set_visible(False)

    if save_path is None:
        save_path = str(Path.home() / ".financialanalyzer" / "cache" / "audit_radar.png")

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    logger.info(f"雷达图已保存: {save_path}")
    return save_path


def generate_heatmap(heatmap_data: list, title: str = "信号风险热力图",
                     save_path: str = None) -> str:
    """
    生成信号热力图

    Args:
        heatmap_data: [{"name", "category", "level", "weight"}]
        title: 图表标题
        save_path: 保存路径

    Returns:
        保存的文件路径
    """
    _setup_plt()

    if not heatmap_data:
        return None

    # 按分类分组
    from ..calculator.signals import SignalCategory, CATEGORY_NAMES
    categories_order = [SignalCategory.ASSET, SignalCategory.PROFIT,
                        SignalCategory.CASHFLOW, SignalCategory.CROSS_VALIDATION,
                        SignalCategory.GOVERNANCE, SignalCategory.MODEL]

    level_colors = {
        "high": "#F44336",
        "medium": "#FF9800",
        "low": "#4CAF50",
        "info": "#2196F3",
    }

    # 按分类排序
    sorted_data = sorted(heatmap_data,
                         key=lambda x: (categories_order.index(SignalCategory(x["category_en"])) if "category_en" in x else 0))

    # 如果没有 category_en，尝试从 category 中文名反推
    cat_name_to_enum = {v: k for k, v in CATEGORY_NAMES.items()}
    sorted_data = sorted(heatmap_data,
                         key=lambda x: next(
                             (i for i, cat in enumerate(categories_order)
                              if cat_name_to_enum.get(x.get("category", "")) == cat), 99))

    fig, ax = plt.subplots(figsize=(12, max(4, len(heatmap_data) * 0.5 + 2)))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')

    y_pos = 0
    y_ticks = []
    y_labels = []
    prev_cat = None

    for i, item in enumerate(sorted_data):
        cat = item.get("category", "")
        level = item.get("level", "info")
        name = item.get("name", f"Signal_{i}")
        weight = item.get("weight", 0)

        # 分类分隔
        if cat != prev_cat:
            if prev_cat is not None:
                y_pos += 0.3  # 分类间距
            prev_cat = cat

        color = level_colors.get(level, "#666")
        # 画色块
        rect_width = min(weight / 10.0, 1.0)
        ax.barh(y_pos, rect_width, height=0.6, color=color, alpha=0.85,
                edgecolor='#333', linewidth=0.5)

        # 标注
        ax.text(rect_width + 0.02, y_pos, f"{name} ({weight})", va='center',
                fontsize=9, color='#e0e0e0')

        y_ticks.append(y_pos)
        y_labels.append(cat if cat != prev_cat else "")
        y_pos += 1

    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, fontsize=9, color='#e0e0e0')
    ax.set_xlim(0, 1.8)
    ax.set_xlabel("风险权重", fontsize=10, color='#e0e0e0')
    ax.set_title(title, fontsize=14, color='#e0e0e0', pad=15, fontweight='bold')

    # 图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#F44336", label="高风险"),
        Patch(facecolor="#FF9800", label="中风险"),
        Patch(facecolor="#4CAF50", label="低风险"),
        Patch(facecolor="#2196F3", label="信息"),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9,
              facecolor='#1a1a2e', edgecolor='#333', labelcolor='#e0e0e0')

    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#333')
    ax.spines['left'].set_color('#333')
    ax.tick_params(colors='#888')

    if save_path is None:
        save_path = str(Path.home() / ".financialanalyzer" / "cache" / "audit_heatmap.png")

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    logger.info(f"热力图已保存: {save_path}")
    return save_path

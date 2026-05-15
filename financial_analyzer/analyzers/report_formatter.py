"""
报告格式化工具 - 消除重复的格式化代码
"""
from ..config import SEPARATOR_HEAVY, SEPARATOR_LIGHT, SEPARATOR_DASH
from ..calculator.financial import FinancialCalculator as FC


class ReportFormatter:
    """报告格式化工具"""

    @staticmethod
    def header(title: str) -> str:
        """生成报告标题"""
        return f"{SEPARATOR_HEAVY}\n{title:^40}\n{SEPARATOR_HEAVY}\n\n"

    @staticmethod
    def section(title: str) -> str:
        """生成段落标题"""
        return f"【{title}】\n{SEPARATOR_LIGHT}\n"

    @staticmethod
    def table_header(*columns) -> str:
        """生成表格头"""
        header_line = "".join(f"{col}" for col in columns)
        return f"{header_line}\n{SEPARATOR_LIGHT}\n"

    @staticmethod
    def format_row(*values) -> str:
        """格式化表格行"""
        return "".join(str(v) for v in values) + "\n"

    @staticmethod
    def conclusion(label: str, value, thresholds: dict = None) -> str:
        """生成结论行"""
        if thresholds is None:
            return f"  {label}: {value}\n"
        for symbol, (min_val, max_val), text in thresholds:
            if min_val is not None and max_val is not None:
                if min_val <= value <= max_val:
                    return f"  {symbol} {label} {value:.1f}%，{text}\n"
            elif min_val is not None and value > min_val:
                return f"  {symbol} {label} {value:.1f}%，{text}\n"
            elif max_val is not None and value <= max_val:
                return f"  {symbol} {label} {value:.1f}%，{text}\n"
        return f"  {label}: {value}\n"

    @staticmethod
    def footer() -> str:
        """生成报告尾部"""
        return f"\n{SEPARATOR_HEAVY}\n"

    @staticmethod
    def full_report(title: str, sections: list[str]) -> str:
        """组装完整报告"""
        result = ReportFormatter.header(title)
        for section in sections:
            result += section
        result += ReportFormatter.footer()
        return result

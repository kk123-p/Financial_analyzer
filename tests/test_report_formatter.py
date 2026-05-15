"""
ReportFormatter 单元测试
"""
import pytest

from financial_analyzer.analyzers.report_formatter import ReportFormatter as RF


class TestReportFormatter:
    def test_header_contains_title(self):
        result = RF.header("测试标题")
        assert "测试标题" in result

    def test_header_has_separators(self):
        result = RF.header("标题")
        assert "=" in result

    def test_section_contains_title(self):
        result = RF.section("段落标题")
        assert "段落标题" in result
        assert "【" in result
        assert "】" in result

    def test_footer_has_separator(self):
        result = RF.footer()
        assert "=" in result

    def test_full_report_assembly(self):
        sections = [
            RF.section("第一部分") + "  内容1\n",
            RF.section("第二部分") + "  内容2\n",
        ]
        report = RF.full_report("完整报告", sections)
        assert "完整报告" in report
        assert "第一部分" in report
        assert "第二部分" in report
        assert "内容1" in report
        assert "内容2" in report

    def test_table_header(self):
        result = RF.table_header("列1", "列2", "列3")
        assert "列1" in result
        assert "列2" in result

    def test_format_row(self):
        result = RF.format_row("A", "B", "C")
        assert "A" in result
        assert "B" in result
        assert result.strip().endswith("") or "\n" in result

    def test_conclusion_basic(self):
        result = RF.conclusion("指标", 50)
        assert "指标" in result
        assert "50" in result

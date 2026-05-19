"""分析结果 HTML 格式化器 — 将纯文本报告转为高亮 HTML"""
import re
from html import escape


class ResultFormatter:
    """纯文本 → 富 HTML 结果格式化"""

    # 标题分隔符模式
    _TITLE_SEP = re.compile(r'^(?:═+|===+)$')
    _INLINE_TITLE = re.compile(r'^[═=]{3,}\s*(.+?)\s*[═=]{3,}$')
    _LIGHT_SEP = re.compile(r'^(?:─+|---+|－+)$')
    _SECTION_PAT = re.compile(r'^【(.+)】$')
    _SUB_HEADING = re.compile(r'^▌\s*(.+)$')

    @staticmethod
    def format(text: str) -> str:
        """主入口：将分析器输出的纯文本转为 HTML"""
        lines = text.split("\n")
        result = []
        in_table = False

        for line in lines:
            stripped = line.strip()

            # 跳过空行
            if not stripped:
                if in_table:
                    in_table = False
                    result.append('</table>')
                result.append('<div class="r-spacer"></div>')
                continue

            # 内联标题 ═══ 标题 ═══
            title_match = ResultFormatter._INLINE_TITLE.match(stripped)
            if title_match:
                if in_table:
                    in_table = False
                    result.append('</table>')
                result.append(f'<h1 class="r-title">{escape(title_match.group(1))}</h1>')
                continue

            # 纯分隔符
            if ResultFormatter._TITLE_SEP.match(stripped):
                if in_table:
                    in_table = False
                    result.append('</table>')
                continue

            # 轻分隔符 ───
            if ResultFormatter._LIGHT_SEP.match(stripped):
                if not in_table:
                    result.append('<hr class="r-divider">')
                continue

            # 章节标题 【...】
            section_match = ResultFormatter._SECTION_PAT.match(stripped)
            if section_match:
                if in_table:
                    in_table = False
                    result.append('</table>')
                result.append(f'<h2 class="r-section">{escape(section_match.group(1))}</h2>')
                continue

            # 子标题 ▌...
            sub_match = ResultFormatter._SUB_HEADING.match(stripped)
            if sub_match:
                if in_table:
                    in_table = False
                    result.append('</table>')
                result.append(f'<h3 class="r-subheading">{escape(sub_match.group(1))}</h3>')
                continue

            # 检测表格行
            if ResultFormatter._is_table_row(stripped):
                if not in_table:
                    in_table = True
                    result.append('<table class="r-table">')
                result.append(ResultFormatter._format_table_row(stripped))
                continue
            elif in_table:
                in_table = False
                result.append('</table>')

            # 普通行
            formatted = ResultFormatter._format_line(stripped)
            result.append(f'<p class="r-line">{formatted}</p>')

        if in_table:
            result.append('</table>')

        return "\n".join(result)

    @staticmethod
    def _is_table_row(line: str) -> bool:
        """判断是否为表格行（含多个对齐列）"""
        # 包含多个双空格分隔的列，且不含中文标点标题
        parts = line.split("  ")
        if len(parts) >= 3:
            # 检查是否有典型数值列
            num_count = sum(1 for p in parts if ResultFormatter._has_number(p))
            return num_count >= 2
        return False

    @staticmethod
    def _has_number(text: str) -> bool:
        return bool(re.search(r'[\d.]+', text))

    @staticmethod
    def _format_table_row(line: str) -> str:
        """格式化表格行"""
        parts = [p.strip() for p in line.split("  ") if p.strip()]
        cells = "".join(
            f'<td class="r-td">{ResultFormatter._format_line(p, is_cell=True)}</td>'
            for p in parts
        )
        return f'<tr class="r-tr">{cells}</tr>'

    @staticmethod
    def _format_line(text: str, is_cell: bool = False) -> str:
        """格式化单行文本，高亮数字和关键词"""
        text = escape(text)

        # 高亮正数百分比和加号值
        text = re.sub(
            r'(\+[\d,.]+%?)',
            r'<span class="r-up">\1</span>',
            text,
        )
        # 高亮负数百分比和减号值
        text = re.sub(
            r'(-[\d,.]+%?)',
            r'<span class="r-down">\1</span>',
            text,
        )
        # 高亮重要标记（结论符号）
        text = re.sub(r'(✓|✅|✔)', r'<span class="r-success">\1</span>', text)
        text = re.sub(r'(⚠|⚠️|⚡|❗)', r'<span class="r-warning-text">\1</span>', text)
        text = re.sub(r'(✗|❌|✘)', r'<span class="r-danger-text">\1</span>', text)

        # 高亮评级标签
        text = re.sub(
            r'(优秀|良好|健康|安全|强劲|充裕|合理)',
            r'<span class="r-tag-good">\1</span>',
            text,
        )
        text = re.sub(
            r'(风险|危险|警告|异常|亏损|恶化|疲弱|操纵|危机|严重)',
            r'<span class="r-tag-bad">\1</span>',
            text,
        )
        text = re.sub(
            r'(中等|一般|关注|注意|谨慎|波动|不确定)',
            r'<span class="r-tag-warn">\1</span>',
            text,
        )

        # 高亮数字（整数/小数/百分比/亿元等）
        text = re.sub(
            r'(?<![>/\w])(\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:亿|万|%|倍|元)?)(?![<>\w])',
            r'<span class="r-num">\1</span>',
            text,
        )

        # 高亮 key: value 格式的 key
        text = re.sub(
            r'(?:^|(?<= ))([一-鿿\w]+)[：:]',
            r'<span class="r-key">\1</span>: ',
            text,
        )

        return text

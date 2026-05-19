"""分析结果 HTML 格式化器 — 将纯文本报告转为高亮 HTML"""
import re
from html import escape


class ResultFormatter:
    """纯文本 → 富 HTML 结果格式化"""

    _SEP_CHARS = re.compile(r'^[\s═=─－\-]+$')
    _SECTION_PAT = re.compile(r'^【(.+)】$')
    _SUB_HEADING = re.compile(r'^▌\s*(.+)$')

    @staticmethod
    def format(text: str) -> str:
        """主入口：将分析器输出的纯文本转为 HTML"""
        lines = text.split("\n")

        # Pass 1: 分类每一行
        classified = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                classified.append(('empty', ''))
            elif ResultFormatter._SEP_CHARS.match(stripped):
                classified.append(('sep', stripped))
            elif ResultFormatter._SECTION_PAT.match(stripped):
                classified.append(('section', stripped))
            elif ResultFormatter._SUB_HEADING.match(stripped):
                classified.append(('subheading', stripped))
            elif ResultFormatter._is_table_row(stripped):
                classified.append(('table', stripped))
            else:
                classified.append(('text', stripped))

        # Pass 2: 合并分隔符-标题-分隔符 → 标题
        merged = []
        i = 0
        while i < len(classified):
            kind, content = classified[i]
            if kind == 'sep':
                # 检查是否是 sep - text - sep 模式
                if (i + 2 < len(classified) and
                    classified[i + 1][0] == 'text' and
                    classified[i + 2][0] == 'sep'):
                    merged.append(('title', classified[i + 1][1]))
                    i += 3
                    continue
                # 检查是否是 sep - text (结尾无分隔符)
                elif (i + 1 < len(classified) and
                      classified[i + 1][0] == 'text' and
                      (i + 2 >= len(classified) or classified[i + 2][0] != 'sep')):
                    # 单行分隔符后的文本 → 可能是标题
                    i += 1
                    continue
                else:
                    # 独立分隔符 → 跳过
                    i += 1
                    continue
            merged.append((kind, content))
            i += 1

        # Pass 3: 渲染 HTML
        result = []
        in_table = False

        for kind, content in merged:
            if kind == 'empty':
                if in_table:
                    in_table = False
                    result.append('</table>')
                result.append('<div class="r-spacer"></div>')

            elif kind == 'title':
                if in_table:
                    in_table = False
                    result.append('</table>')
                result.append(f'<h1 class="r-title">{escape(content)}</h1>')

            elif kind == 'section':
                if in_table:
                    in_table = False
                    result.append('</table>')
                m = ResultFormatter._SECTION_PAT.match(content)
                result.append(f'<h2 class="r-section">{escape(m.group(1))}</h2>')

            elif kind == 'subheading':
                if in_table:
                    in_table = False
                    result.append('</table>')
                m = ResultFormatter._SUB_HEADING.match(content)
                result.append(f'<h3 class="r-subheading">{escape(m.group(1))}</h3>')

            elif kind == 'table':
                if not in_table:
                    in_table = True
                    result.append('<table class="r-table">')
                result.append(ResultFormatter._format_table_row(content))

            elif kind == 'text':
                if in_table:
                    in_table = False
                    result.append('</table>')
                result.append(f'<p class="r-line">{ResultFormatter._format_line(content)}</p>')

        if in_table:
            result.append('</table>')

        return "\n".join(result)

    @staticmethod
    def _is_table_row(line: str) -> bool:
        """判断是否为表格行"""
        parts = [p for p in line.split("  ") if p.strip()]
        if len(parts) < 3:
            return False
        num_count = sum(1 for p in parts if re.search(r'[\d.]+', p.strip()))
        return num_count >= 2

    @staticmethod
    def _format_table_row(line: str) -> str:
        parts = [p.strip() for p in line.split("  ") if p.strip()]
        cells = "".join(
            f'<td class="r-td">{ResultFormatter._format_line(p)}</td>'
            for p in parts
        )
        return f'<tr class="r-tr">{cells}</tr>'

    @staticmethod
    def _format_line(text: str) -> str:
        """格式化单行文本：高亮数字、符号、关键词"""
        text = escape(text)

        # 正/负百分比
        text = re.sub(r'(\+[\d,.]+%?)', r'<span class="r-up">\1</span>', text)
        text = re.sub(r'(-[\d,.]+%?)', r'<span class="r-down">\1</span>', text)

        # 标记符号
        text = re.sub(r'(✓|✅|✔)', r'<span class="r-success">\1</span>', text)
        text = re.sub(r'(⚠|⚠️|⚡|❗|📌)', r'<span class="r-warning-text">\1</span>', text)
        text = re.sub(r'(✗|❌|✘|📉)', r'<span class="r-danger-text">\1</span>', text)
        text = re.sub(r'(📈)', r'<span class="r-success">\1</span>', text)

        # 关键词标签
        text = re.sub(
            r'(优秀|良好|健康|安全|强劲|充裕|合理|低估|增长)',
            r'<span class="r-tag-good">\1</span>', text
        )
        text = re.sub(
            r'(风险|危险|警告|异常|亏损|恶化|疲弱|操纵|危机|严重|高估)',
            r'<span class="r-tag-bad">\1</span>', text
        )
        text = re.sub(
            r'(中等|一般|关注|注意|谨慎|波动|不确定)',
            r'<span class="r-tag-warn">\1</span>', text
        )

        # 数字高亮
        text = re.sub(
            r'(?<![>/\w])(\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:亿|万|%|倍|元|次|pp)?)(?![<>\w])',
            r'<span class="r-num">\1</span>', text
        )

        # key: value 的 key 部分
        text = re.sub(
            r'(?:^|(?<= ))([一-鿿\w]{2,8})[：:]',
            r'<span class="r-key">\1</span>: ',
            text,
        )

        return text

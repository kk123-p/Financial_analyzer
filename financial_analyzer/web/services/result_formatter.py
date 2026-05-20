"""分析结果 HTML 格式化器 — 将纯文本报告转为高亮 HTML"""
import re
from html import escape


class ResultFormatter:
    """纯文本 → 富 HTML 结果格式化"""

    _SEP_CHARS = re.compile(r'^[\s═=─－\-━]+$')
    _TITLE_LINE = re.compile(r'^[\s═=─\-━]+(.+?)[\s═=─\-━]+$')
    _SECTION_PAT = re.compile(r'^【(.+)】$')
    _SUB_HEADING = re.compile(r'^▸?\s*▌\s*(.+)$')
    _BULLET_HEADING = re.compile(r'^▸\s+(.+)$')

    @classmethod
    def format(cls, text: str) -> str:
        """主入口：将分析器输出的纯文本转为 HTML"""
        lines = text.split("\n")

        # Pass 1: 分类每一行
        classified = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                classified.append({'kind': 'empty', 'text': ''})
                continue

            # 纯分隔线优先检测
            if cls._SEP_CHARS.match(stripped):
                classified.append({'kind': 'sep', 'text': stripped})
                continue

            # 内嵌标题: ═══ text ═══ (需要至少包含一个非分隔符字符)
            title_m = cls._TITLE_LINE.match(stripped)
            if title_m:
                inner = title_m.group(1).strip()
                if inner and not cls._SEP_CHARS.match(inner):
                    classified.append({'kind': 'title', 'text': inner})
                    continue

            if cls._SECTION_PAT.match(stripped):
                classified.append({'kind': 'section', 'text': stripped})
            elif cls._SUB_HEADING.match(stripped):
                classified.append({'kind': 'subheading', 'text': stripped})
            elif cls._BULLET_HEADING.match(stripped):
                classified.append({'kind': 'bullet_heading', 'text': stripped})
            else:
                classified.append({'kind': 'text', 'text': stripped})

        # Pass 2: 合并 — 检测标题、表格
        groups = []
        i = 0
        while i < len(classified):
            item = classified[i]

            # 表格检测: text(表头) + sep + text*(数据行)
            if item['kind'] == 'text':
                if (i + 2 < len(classified) and
                        classified[i + 1]['kind'] == 'sep' and
                        classified[i + 2]['kind'] == 'text'):

                    header_parts = cls._split_cols(item['text'])
                    if len(header_parts) >= 3:
                        # 确认是表格 — 收集数据行直到非 text 或列数不匹配
                        data_rows = []
                        j = i + 2
                        while j < len(classified) and classified[j]['kind'] == 'text':
                            row_parts = cls._split_cols(classified[j]['text'])
                            if len(row_parts) < 2:
                                break
                            data_rows.append(classified[j]['text'])
                            j += 1

                        if data_rows:
                            groups.append({
                                'kind': 'table',
                                'header': item['text'],
                                'data': data_rows,
                            })
                            i = j
                            continue

                # 可能是独立的键值行，检测是否有连续的键值格式
                if cls._is_kv_line(item['text']):
                    kv_lines = [item['text']]
                    j = i + 1
                    while (j < len(classified) and
                           classified[j]['kind'] == 'text' and
                           cls._is_kv_line(classified[j]['text'])):
                        kv_lines.append(classified[j]['text'])
                        j += 1
                    if len(kv_lines) >= 2:
                        groups.append({'kind': 'kv_block', 'lines': kv_lines})
                        i = j
                        continue

                groups.append(item)
                i += 1
                continue

            # 独立分隔符 → 分隔线
            if item['kind'] == 'sep':
                groups.append({'kind': 'divider'})
                i += 1
                continue

            groups.append(item)
            i += 1

        # Pass 3: 渲染 HTML
        result = []
        for g in groups:
            kind = g['kind']

            if kind == 'empty':
                result.append('<div class="r-spacer"></div>')

            elif kind == 'divider':
                result.append('<hr class="r-divider">')

            elif kind == 'title':
                result.append(f'<h1 class="r-title">{escape(g["text"])}</h1>')

            elif kind == 'section':
                m = cls._SECTION_PAT.match(g['text'])
                result.append(f'<h2 class="r-section">{escape(m.group(1))}</h2>')

            elif kind == 'subheading':
                m = cls._SUB_HEADING.match(g['text'])
                result.append(f'<h3 class="r-subheading">{escape(m.group(1))}</h3>')

            elif kind == 'bullet_heading':
                m = cls._BULLET_HEADING.match(g['text'])
                result.append(
                    f'<div class="r-bullet-heading">{escape(m.group(1))}</div>'
                )

            elif kind == 'table':
                result.append(cls._render_table(g['header'], g['data']))

            elif kind == 'kv_block':
                result.append(cls._render_kv_block(g['lines']))

            elif kind == 'text':
                result.append(f'<p class="r-line">{cls._format_line(g["text"])}</p>')

        return "\n".join(result)

    # ========================================================================
    # 列提取
    # ========================================================================

    @staticmethod
    def _split_cols(line: str) -> list[str]:
        """按 2+ 空格分割列"""
        return [p.strip() for p in re.split(r'\s{2,}', line.strip()) if p.strip()]

    @staticmethod
    def _is_kv_line(line: str) -> bool:
        """判断是否键值对行（如 '  毛利率: 45.23%'）"""
        return bool(re.match(r'^\s{2,}[\w一-鿿]{2,12}[：:]\s', line))

    # ========================================================================
    # 表格渲染
    # ========================================================================

    @classmethod
    def _render_table(cls, header: str, data: list[str]) -> str:
        """渲染完整表格 — 表头 + 数据行，列自动对齐"""
        header_cols = cls._split_cols(header)
        data_cols_list = [cls._split_cols(row) for row in data]

        n_cols = max(len(header_cols),
                     max((len(r) for r in data_cols_list), default=0))

        parts = ['<div class="r-table-wrapper"><table class="r-table">']

        # thead
        parts.append('<thead><tr class="r-tr-head">')
        for col in header_cols:
            parts.append(f'<th class="r-th">{escape(col)}</th>')
        for _ in range(n_cols - len(header_cols)):
            parts.append('<th class="r-th"></th>')
        parts.append('</tr></thead>')

        # tbody
        parts.append('<tbody>')
        for row_cols in data_cols_list:
            alt = len(parts) % 2 == 0
            row_cls = 'r-tr r-tr-alt' if alt else 'r-tr'
            parts.append(f'<tr class="{row_cls}">')
            for i, col in enumerate(row_cols):
                parts.append(f'<td class="r-td">{cls._format_line(col)}</td>')
            for _ in range(n_cols - len(row_cols)):
                parts.append('<td class="r-td"></td>')
            parts.append('</tr>')
        parts.append('</tbody>')

        parts.append('</table></div>')
        return "\n".join(parts)

    # ========================================================================
    # 键值块渲染
    # ========================================================================

    @classmethod
    def _render_kv_block(cls, lines: list[str]) -> str:
        """渲染连续的键值对行"""
        parts = ['<div class="r-kv-block">']
        for line in lines:
            # 分割 key: value
            m = re.match(r'^(\s*)([\w一-鿿\s]{2,12})[：:]\s*(.*)$', line)
            if m:
                key = m.group(2).strip()
                val = m.group(3)
                parts.append(
                    f'<div class="r-kv-row">'
                    f'<span class="r-key">{escape(key)}</span>'
                    f'<span class="r-kv-sep">: </span>'
                    f'<span class="r-val">{cls._format_line(val)}</span>'
                    f'</div>'
                )
            else:
                parts.append(f'<p class="r-line">{cls._format_line(line)}</p>')
        parts.append('</div>')
        return "\n".join(parts)

    # ========================================================================
    # 单行格式化
    # ========================================================================

    @staticmethod
    def _format_line(text: str) -> str:
        """格式化单行文本：高亮数字、符号、关键词"""
        text = escape(text)

        # 正/负百分号 (先处理，避免被数字高亮覆盖)
        text = re.sub(r'(\+[\d,.]+%?)', r'<span class="r-up">\1</span>', text)
        text = re.sub(r'(-[\d,.]+%?)', r'<span class="r-down">\1</span>', text)

        # 数字 + 单位
        text = re.sub(
            r'(?<![>/\w#])(\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:亿|万|%|倍|元|次|pp|个百分点)?)',
            r'<span class="r-num">\1</span>', text
        )

        # 方块字符 (█░)
        text = re.sub(
            r'(█+)',
            r'<span class="r-bar-fill">\1</span>', text
        )
        text = re.sub(
            r'(░+)',
            r'<span class="r-bar-empty">\1</span>', text
        )

        # emoji / 标记
        text = re.sub(r'(✅|✔|✓|📈)', r'<span class="r-success">\1</span>', text)
        text = re.sub(r'(⚠|⚠️|⚡|❗|📌)', r'<span class="r-warning-text">\1</span>', text)
        text = re.sub(r'(❌|✗|✘|📉)', r'<span class="r-danger-text">\1</span>', text)

        # 正向关键词
        text = re.sub(
            r'(优秀|良好|健康|安全|强劲|充裕|合理|低估|增长|稳健|领先|改善|持续改善|总体向好|高度稳定|基本稳定)',
            r'<span class="r-tag-good">\1</span>', text
        )
        # 负向关键词
        text = re.sub(
            r'(风险|危险|警告|异常|亏损|恶化|疲弱|操纵|危机|严重|高估|落后|趋势走弱|持续恶化|趋势恶化|波动较大)',
            r'<span class="r-tag-bad">\1</span>', text
        )
        # 中性关键词
        text = re.sub(
            r'(中等|一般|关注|注意|谨慎|波动|不确定|观望|波动持平)',
            r'<span class="r-tag-warn">\1</span>', text
        )

        return text

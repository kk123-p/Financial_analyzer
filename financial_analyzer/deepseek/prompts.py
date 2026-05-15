"""
DeepSeek 提示词模块 - 财务分析 AI 提示词体系
包含：基础分析、深度投研、三方辩论、矛盾信号检测等提示词
"""
import json
from pathlib import Path
from ..logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# 配置管理
# ============================================================================
_CONFIG_PATH = Path.home() / ".financialanalyzer" / "ai_config.json"

_DEFAULT_CONFIG = {
    "analyst_weights": {
        "value": 0.34,
        "growth": 0.33,
        "risk": 0.33
    },
    "debate_rounds": 3,
    "max_tokens": 4096,
    "temperature": 0.3
}


def _load_config() -> dict:
    """加载 AI 配置"""
    try:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"加载 AI 配置失败: {e}")
    return _DEFAULT_CONFIG.copy()


def _save_config(config: dict):
    """保存 AI 配置"""
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存 AI 配置失败: {e}")


def reload_config() -> dict:
    """重新加载配置"""
    return _load_config()


# ============================================================================
# 分析师角色定义
# ============================================================================
ANALYST_ROLES = {
    "value": {
        "name": "格雷厄姆式价值分析师",
        "emoji": "📊",
        "focus": "资产、安全边际与清算价值",
        "core_question": "我现在付的钱买到了什么硬资产？",
        "motto": "我现在付的钱买到了什么硬资产",
        "tasks": [
            "计算净运营资本减去总负债的清算价值折扣",
            "审视静态市盈率与历史/行业分位",
            "评估股息率的可持续性",
        ],
        "system_prompt": (
            "你是一位拥有20年经验的格雷厄姆式价值分析师。"
            "你只关注资产安全边际、清算价值和估值回归。"
            "你对任何高估值都保持警惕，偏好低市净率、高股息、强现金流的标的。"
            "分析时必须基于提供的数据，严禁臆测。"
        ),
    },
    "growth": {
        "name": "费雪式成长分析师",
        "emoji": "🚀",
        "focus": "市场空间（TAM）、单位经济模型、研发强度",
        "core_question": "未来能赚多少？",
        "motto": "未来能赚多少",
        "tasks": [
            "定性评估产品是否有'尖叫点'",
            "分析研发费用资本化是否激进",
            "计算客户终身价值与获客成本之比",
        ],
        "system_prompt": (
            "你是一位费雪式成长分析师，专注于成长股投资。"
            "你关注市场空间、渗透率、研发投入和竞争壁垒。"
            "你愿意为高质量成长支付溢价，但要求成长具有可持续性。"
            "分析时必须基于提供的数据，严禁臆测。"
        ),
    },
    "risk": {
        "name": "塔勒布式风控师",
        "emoji": "🛡️",
        "focus": "脆弱性、尾部风险与反身性",
        "core_question": "什么会让我永久性损失？",
        "motto": "什么会让我永久性损失",
        "tasks": [
            "计算即时偿付能力：(现金+经营现金流)/一年内到期有息负债",
            "识别股权质押比例、关联交易等隐性风险",
            "评估股价下跌→融资困难→基本面恶化的反身性螺旋",
        ],
        "system_prompt": (
            "你是一位塔勒布式风控师，专注于尾部风险和反脆弱性。"
            "你对任何看似美好的数据都保持怀疑，擅长发现隐藏的脆弱点。"
            "你关注杠杆风险、流动性风险、治理风险和反身性风险。"
            "分析时必须基于提供的数据，严禁臆测。"
        ),
    },
}


def get_analyst_roles() -> dict:
    """获取分析师角色定义"""
    return ANALYST_ROLES


# ============================================================================
# 基础深度分析提示词（兼容旧版 client.py 接口）
# ============================================================================
DEEP_ANALYSIS_SYSTEM_PROMPT = """你是一位专业的财务分析师，拥有丰富的A股、港股和美股分析经验。
你的任务是根据用户提供的财务数据和技术指标，生成专业、客观、有深度的财务分析报告。

要求：
1. 使用中文输出
2. 报告结构清晰，包含摘要、详细分析、风险提示、投资建议
3. 数据引用准确，结论有理有据
4. 语言专业但易懂，避免过度使用术语
5. 必须基于提供的数据进行分析，严禁臆测未提供的数据
"""


def get_analysis_prompt(structured_prompt: str, analysis_focus: str = "comprehensive",
                        perspective: str = "multi") -> str:
    """
    构建深度分析提示词（兼容旧版接口）

    Args:
        structured_prompt: 结构化数据提示词
        analysis_focus: 分析焦点 (dupont/zscore/fscore/mscore/fcf/quadrant/moat/comprehensive)
        perspective: 分析视角 (value/growth/risk/multi)
    """
    focus_map = {
        "dupont": "请重点进行杜邦分析，拆解ROE的驱动因素",
        "zscore": "请重点分析Altman Z-Score，评估破产风险",
        "fscore": "请重点分析Piotroski F-Score，评估财务健康度",
        "mscore": "请重点分析Beneish M-Score，识别盈余操纵风险",
        "fcf": "请重点分析自由现金流，评估企业内在价值",
        "quadrant": "请重点分析企业所处的财务象限（成长/衰退/改善/恶化）",
        "moat": "请重点分析企业的竞争壁垒和护城河",
        "comprehensive": "请进行全方位综合分析",
    }
    focus_instruction = focus_map.get(analysis_focus, focus_map["comprehensive"])

    perspective_map = {
        "value": ANALYST_ROLES["value"]["system_prompt"],
        "growth": ANALYST_ROLES["growth"]["system_prompt"],
        "risk": ANALYST_ROLES["risk"]["system_prompt"],
        "multi": DEEP_ANALYSIS_SYSTEM_PROMPT,
    }
    role_prompt = perspective_map.get(perspective, DEEP_ANALYSIS_SYSTEM_PROMPT)

    return f"""{role_prompt}

{focus_instruction}

以下是公司的结构化财务数据：
{structured_prompt}

请基于以上数据，输出一份结构化的深度分析报告。"""


def build_multi_perspective_prompt(structured_prompt: str,
                                    weights: dict = None) -> str:
    """
    构建多视角分析提示词

    Args:
        structured_prompt: 结构化数据
        weights: 各视角权重 {"value": 0.34, "growth": 0.33, "risk": 0.33}
    """
    if weights is None:
        config = _load_config()
        weights = config.get("analyst_weights", _DEFAULT_CONFIG["analyst_weights"])

    roles_text = ""
    for key, role in ANALYST_ROLES.items():
        w = weights.get(key, 0.33)
        roles_text += f"\n### {role['emoji']} {role['name']}（权重: {w:.0%}）\n"
        roles_text += f"关注点：{role['focus']}\n"
        roles_text += f"核心问题：{role['motto']}\n"
        roles_text += "专属任务：\n"
        for task in role["tasks"]:
            roles_text += f"  - {task}\n"

    return f"""{DEEP_ANALYSIS_SYSTEM_PROMPT}

你将同时扮演三位不同视角的分析师，对以下公司进行多维度分析：

{roles_text}

以下是公司的结构化财务数据：
{structured_prompt}

请按以下格式输出：
1. 首先分别从三个视角给出独立分析
2. 然后指出三个视角之间的共识与分歧
3. 最后给出综合评估和情景概率矩阵
"""


# ============================================================================
# 辩论系统提示词
# ============================================================================
DEBATE_SYSTEM_PROMPT = """你是一个AI深度投研分析系统的核心协调员。

你的任务是协调三位不同视角的分析师（价值、成长、风控）进行结构化辩论，
最终形成一份多维度的深度投研报告。

核心原则：
1. 不让AI直接写结论，而是模拟专家思考流程
2. 强制自我质疑，寻找数据间的矛盾
3. 输出结构化报告，而非简单推荐
4. 所有结论必须基于提供的数据，严禁臆测

辩论流程：
- 第一轮：各分析师独立陈述观点
- 第二轮：交叉质询，找出分歧
- 第三轮：形成共识地图和情景概率矩阵
"""


def get_debate_system_prompt() -> str:
    """获取辩论系统提示词"""
    return DEBATE_SYSTEM_PROMPT


# ============================================================================
# 辩论流程提示词
# ============================================================================
DEBATE_ROUND1_PROMPT = """## 第一轮：独立视角陈述

你是 {role_name}。

{system_prompt}

以下是公司的结构化财务数据：
{structured_prompt}

请从你的专业视角出发，完成以下分析：

### 专属任务
{tasks}

### 分析要求
1. 给出你的核心判断（看多/看空/中性）
2. 列出支撑你判断的3-5个关键数据点
3. 指出你最担忧的1-2个风险点
4. 给出你的估值区间判断

请用结构化的格式输出，确保每个论点都有数据支撑。
"""


def build_debate_round1(structured_prompt: str, company_name: str = "",
                       stock_code: str = "", role_key: str = "") -> str:
    """构建辩论第一轮提示词

    Args:
        structured_prompt: 结构化数据文本
        company_name: 公司名称
        stock_code: 股票代码
        role_key: 分析师角色key (value/growth/risk)，如果为空则返回通用提示词
    """
    if role_key:
        role = ANALYST_ROLES.get(role_key, ANALYST_ROLES["value"])
        tasks = "\n".join(f"{i+1}. {t}" for i, t in enumerate(role["tasks"]))
        return DEBATE_ROUND1_PROMPT.format(
            role_name=role["name"],
            system_prompt=role["system_prompt"],
            structured_prompt=structured_prompt,
            tasks=tasks,
        )
    else:
        # 通用版本（debate_engine会自己加role信息）
        return f"以下是公司的结构化财务数据：\n\n{structured_prompt}\n\n请从你的专业视角出发，进行独立分析。"


DEBATE_ROUND2_PROMPT = """## 第二轮：交叉质询

你是 {role_name}。

以下是三位分析师在第一轮的独立分析：

{all_analyses}

### 你的任务
1. 找出其他两位分析师观点中与你判断**最矛盾**的地方
2. 用数据进行质疑和反驳
3. 如果对方的论点有道理，承认并调整你的判断
4. 指出你认为被其他分析师**忽略**的重要风险或机会

### 重点质询方向
{质询方向}

请保持专业和客观，所有质疑必须有数据依据。
"""


def build_debate_round2(round1_statements) -> str:
    """构建辩论第二轮提示词

    Args:
        round1_statements: dict {analyst_id: statement_text} 或 str
    """
    if isinstance(round1_statements, dict):
        parts = []
        roles = get_analyst_roles()
        for aid, stmt in round1_statements.items():
            role = roles.get(aid, {})
            parts.append(f"\n### {role.get('emoji', '')} {role.get('name', aid)}:")
            parts.append(stmt)
        all_analyses = "\n".join(parts)
    else:
        all_analyses = str(round1_statements)

    return f"## 第二轮：交叉质询\n\n以下是三位分析师在第一轮的独立分析：\n\n{all_analyses}\n\n请从你的专业视角出发，找出其他分析师观点中与你判断最矛盾的地方，用数据进行质疑和反驳。\n如果对方的论点有道理，承认并调整你的判断。\n指出你认为被其他分析师忽略的重要风险或机会。"


DEBATE_ROUND3_PROMPT = """## 第三轮：形成共识地图

你是投研系统协调员。

以下是三轮辩论的完整记录：
{debate_history}

### 任务
请综合三位分析师的观点，输出以下内容：

1. **共识区域**：三位分析师都认同的结论
2. **分歧区域**：存在争议的关键点
3. **情景概率矩阵**：

| 情景 | 价值分析师观点 | 成长分析师观点 | 风控师关注点 | 综合概率 | 潜在回报/风险 |
|------|--------------|--------------|------------|---------|-------------|
| 乐观 | ... | ... | ... | XX% | +XX% |
| 中性 | ... | ... | ... | XX% | +XX% |
| 悲观 | ... | ... | ... | XX% | -XX% |

4. **最终摘要**：包含所有必要警示的综合评估（不超过200字）
5. **关键风险提示**：必须明确指出可能导致永久性损失的因素
"""


def build_debate_round3(debate_history: str) -> str:
    """构建辩论第三轮提示词"""
    return DEBATE_ROUND3_PROMPT.format(debate_history=debate_history)


# ============================================================================
# 用户追问提示词
# ============================================================================
USER_FOLLOWUP_PROMPT = """## 用户追问

用户提出了以下问题：
{question}

以下是之前的分析上下文：
{context}

请基于已有分析数据，结合用户的问题，给出专业、简洁的回答。
如果问题超出了已有数据的范围，请明确说明并建议需要补充哪些数据。
"""


def build_user_followup(question: str, context: str) -> str:
    """构建用户追问提示词"""
    return USER_FOLLOWUP_PROMPT.format(question=question, context=context)


# ============================================================================
# 权重调整提示词
# ============================================================================
WEIGHT_ADJUSTMENT_PROMPT = """## 分析权重调整

用户调整了三位分析师的权重：
- 价值分析师：{value_weight:.0%}
- 成长分析师：{growth_weight:.0%}
- 风控师：{risk_weight:.0%}

之前的分析结论：
{previous_conclusion}

请根据新的权重，重新评估并输出调整后的综合结论。
重点突出权重增加的视角，适当弱化权重降低的视角。
"""


def build_weight_adjustment(value_weight: float, growth_weight: float,
                             risk_weight: float, previous_conclusion: str) -> str:
    """构建权重调整提示词"""
    return WEIGHT_ADJUSTMENT_PROMPT.format(
        value_weight=value_weight,
        growth_weight=growth_weight,
        risk_weight=risk_weight,
        previous_conclusion=previous_conclusion,
    )


# ============================================================================
# 矛盾信号检测提示词
# ============================================================================
SIGNAL_DETECTION_PROMPT = """## 财务矛盾信号检测

你是财务异常检测专家。请基于以下财务数据，检测可能存在的矛盾信号。

### 检测维度

**1. 利润含金量**
- 对比净利润增速与经营现金流增速
- 若利润大增但经营现金流转负 → "盈利质量黄色预警"

**2. 增长可持续性**
- 拆解营收增长 = 销量增长 × 价格增长 + 并购贡献
- 若增长主要靠提价而销量持平 → "增长可持续性预警"

**3. ROE质量**
- 杜邦拆解ROE
- 若高ROE完全由超高杠杆驱动 → "高杠杆脆弱性风险"

**4. 资产质量**
- 应收账款增速 vs 营收增速
- 存货周转天数变化
- 商誉占净资产比重

**5. 现金流健康度**
- 经营活动现金流是否持续为正
- 投资活动现金流是否合理
- 筹资活动是否过度依赖外部融资

### 财务数据
{financial_data}

### 输出格式
对每个检测到的信号，输出：
- 信号名称
- 严重程度（红/黄/绿）
- 具体数据依据
- 可能的原因分析
- 建议关注点
"""


def build_signal_detection_prompt(financial_data: str) -> str:
    """构建矛盾信号检测提示词"""
    return SIGNAL_DETECTION_PROMPT.format(financial_data=financial_data)


# ============================================================================
# 体检报告构建提示词
# ============================================================================
HEALTH_REPORT_PROMPT = """## 公司财务体检报告

请基于以下结构化数据，生成一份简洁的公司财务体检报告。

### 数据
{structured_data}

### 报告结构

1. **公司快照**：市值、行业、上市板块

2. **财务健康仪表盘**
   - 盈利质量：毛利率、净利率、ROE（杜邦三因子）、经营现金流/净利润比率
   - 成长动能：营收/利润/现金流三年CAGR、研发投入占比
   - 资产效率：总资产周转率、存货/应收周转天数
   - 风险标尺：Z-Score、F-Score、M-Score
   - 估值坐标：PE/PB历史分位、DCF估值区间

3. **异常信号汇总**
   列出所有检测到的异常信号

4. **一句话总结**
   用一句话概括公司的财务健康状况
"""


def build_health_report_prompt(structured_data: str) -> str:
    """构建体检报告提示词"""
    return HEALTH_REPORT_PROMPT.format(structured_data=structured_data)


# ============================================================================
# 简报生成提示词
# ============================================================================
BRIEFING_PROMPT = """## 三维投研简报

基于以下公司数据，生成三个维度的投研简报。

### 公司数据
{company_data}

### 输出格式

**📊 价值视角简报**
- 核心估值判断
- 安全边际评估
- 关键风险点

**🚀 成长视角简报**
- 增长驱动因素
- 市场空间评估
- 可持续性判断

**🛡️ 风控视角简报**
- 脆弱性评估
- 尾部风险识别
- 反身性风险

**⚖️ 综合建议**
- 情景概率分布
- 建议操作区间
"""


def build_briefing_prompt(company_data: str) -> str:
    """构建简报提示词"""
    return BRIEFING_PROMPT.format(company_data=company_data)

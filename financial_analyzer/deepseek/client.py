"""
DeepSeek API 客户端 - 调用 DeepSeek 进行财务智能分析
支持 OpenAI 兼容格式（DeepSeek API）
"""
import json
import time
from dataclasses import dataclass, field

from ..logging_config import get_logger

logger = get_logger(__name__)

# 条件导入
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


_VALID_REASONING_EFFORTS = {"low", "medium", "high"}


@dataclass
class DeepSeekConfig:
    """DeepSeek 配置"""
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    max_tokens: int = 8192
    temperature: float = 0.3
    timeout: int = 120
    thinking_enabled: bool = True
    reasoning_effort: str = "high"

    def __post_init__(self):
        if self.reasoning_effort not in _VALID_REASONING_EFFORTS:
            self.reasoning_effort = "medium"


@dataclass
class AnalysisReport:
    """分析报告"""
    title: str = ""
    summary: str = ""
    content: str = ""
    reasoning_content: str = ""
    timestamp: str = ""
    model: str = ""
    tokens_used: int = 0
    success: bool = False
    error: str = ""
    tool_calls_log: list = field(default_factory=list)


class DeepSeekClient:
    """DeepSeek API 客户端"""

    # 系统提示词：定义 AI 角色
    SYSTEM_PROMPT = """你是一位专业的财务分析师，拥有丰富的A股、港股和美股分析经验。
你的任务是根据用户提供的财务数据和技术指标，生成专业、客观、有深度的财务分析报告。

要求：
1. 使用中文输出
2. 报告结构清晰，包含摘要、详细分析、风险提示、投资建议
3. 数据引用准确，结论有理有据
4. 语言专业但易懂，避免过度使用术语
5. 必须包含风险提示，不构成投资建议的声明
6. 使用 Markdown 格式输出"""

    # 预设分析模板
    ANALYSIS_TEMPLATES = {
        "综合分析": "请对以下财务数据进行综合分析，包括基本面、技术面、估值水平和风险评估：\n\n{data}",
        "盈利能力": "请重点分析以下公司的盈利能力，包括毛利率、净利率、ROE的趋势和可持续性：\n\n{data}",
        "偿债风险": "请重点分析以下公司的偿债能力和财务风险，包括流动性、杠杆水平和现金流状况：\n\n{data}",
        "成长潜力": "请重点分析以下公司的成长潜力，包括营收增长、利润增长和行业发展前景：\n\n{data}",
        "估值分析": "请对以下公司进行估值分析，包括PE、PB、PEG等指标的横向和纵向对比：\n\n{data}",
        "行业对比": "请将以下公司与其所在行业进行对比分析，评估竞争地位和行业前景：\n\n{data}",
        "自定义": "{data}",
    }

    def __init__(self, config: DeepSeekConfig = None):
        self.config = config or DeepSeekConfig()
        self._validated = False

    def set_api_key(self, api_key: str):
        """设置 API Key"""
        self.config.api_key = api_key.strip()
        self._validated = False

    def set_base_url(self, base_url: str):
        """设置 API 地址"""
        self.config.base_url = base_url.rstrip("/")

    def set_model(self, model: str):
        """设置模型"""
        self.config.model = model

    def _apply_thinking_config(self, payload: dict):
        """如果 thinking 启用，修改 payload：移除 temperature，添加 thinking 参数"""
        if self.config.thinking_enabled:
            payload.pop("temperature", None)
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = self.config.reasoning_effort

    def validate_key(self) -> tuple[bool, str]:
        """验证 API Key 是否有效"""
        if not self.config.api_key:
            return False, "API Key 未设置"

        if not HAS_REQUESTS:
            return False, "requests 库未安装，请运行: pip install requests"

        try:
            response = self._call_api(
                user_message="你好，请回复'连接成功'四个字。",
                max_tokens=20,
                system_prompt="你是一个测试助手，只需按要求回复。"
            )
            if response.success:
                self._validated = True
                return True, "API Key 验证成功"
            else:
                return False, f"验证失败: {response.error}"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def generate_report(self, data: str, template: str = "综合分析",
                        custom_prompt: str = None) -> AnalysisReport:
        """
        生成分析报告

        Args:
            data: 财务数据文本
            template: 分析模板名称
            custom_prompt: 自定义提示词（template="自定义"时使用）

        Returns:
            AnalysisReport 对象
        """
        if not self.config.api_key:
            return AnalysisReport(error="API Key 未设置", success=False)

        if not HAS_REQUESTS:
            return AnalysisReport(error="requests 库未安装", success=False)

        # 构建用户消息
        if template == "自定义" and custom_prompt:
            user_message = f"{custom_prompt}\n\n{data}"
        else:
            tpl = self.ANALYSIS_TEMPLATES.get(template, self.ANALYSIS_TEMPLATES["综合分析"])
            user_message = tpl.format(data=data)

        # 调用 API
        report = self._call_api(user_message)
        return report

    def _call_api(self, user_message: str, max_tokens: int = None,
                  system_prompt: str = None) -> AnalysisReport:
        """调用 DeepSeek API"""
        url = f"{self.config.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt or self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": False,
        }

        self._apply_thinking_config(payload)

        report = AnalysisReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            model=self.config.model,
        )

        try:
            logger.info(f"调用 DeepSeek API: {self.config.model}")
            resp = requests.post(url, headers=headers, json=payload,
                                 timeout=self.config.timeout)

            if resp.status_code == 200:
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                report.content = message.get("content", "")
                report.reasoning_content = message.get("reasoning_content", "")
                report.summary = report.content[:200] + "..." if len(report.content) > 200 else report.content
                report.tokens_used = data.get("usage", {}).get("total_tokens", 0)
                report.success = True
                logger.info(f"API 调用成功，消耗 {report.tokens_used} tokens")
            elif resp.status_code == 401:
                report.error = "API Key 无效，请检查"
                logger.error(f"API 认证失败: {resp.text}")
            elif resp.status_code == 429:
                report.error = "API 调用频率超限，请稍后重试"
                logger.error(f"API 限流: {resp.text}")
            elif resp.status_code == 402:
                report.error = "API 余额不足，请充值"
                logger.error(f"API 余额不足: {resp.text}")
            else:
                report.error = f"API 返回错误 ({resp.status_code}): {resp.text[:100]}"
                logger.error(f"API 错误: {resp.status_code} {resp.text}")

        except requests.exceptions.Timeout:
            report.error = f"API 调用超时（{self.config.timeout}秒）"
            logger.error("API 调用超时")
        except requests.exceptions.ConnectionError:
            report.error = "无法连接到 DeepSeek API，请检查网络"
            logger.error("API 连接失败")
        except Exception as e:
            report.error = f"未知错误: {str(e)}"
            logger.error(f"API 调用异常: {e}")

        return report


    def generate_deep_analysis(self, structured_prompt: str,
                               analysis_focus: str = None,
                               perspective: str = None) -> AnalysisReport:
        """
        生成深度分析报告（使用结构化 prompt）

        Args:
            structured_prompt: 结构化数据 prompt（由 prompts.py 构建）
            analysis_focus: 分析重点（dupont/zscore/fscore/mscore/fcf/quadrant/moat）
            perspective: 分析视角（value/growth/risk/multi）
        """
        if not self.config.api_key:
            return AnalysisReport(error="API Key 未设置", success=False)

        if not HAS_REQUESTS:
            return AnalysisReport(error="requests 库未安装", success=False)

        from .prompts import (
            DEEP_ANALYSIS_SYSTEM_PROMPT, get_analysis_prompt,
            build_multi_perspective_prompt, ANALYST_ROLES,
        )

        perspective_map = {
            "value": ANALYST_ROLES["value"]["system_prompt"],
            "growth": ANALYST_ROLES["growth"]["system_prompt"],
            "risk": ANALYST_ROLES["risk"]["system_prompt"],
        }
        system_prompt = perspective_map.get(perspective, DEEP_ANALYSIS_SYSTEM_PROMPT)
        user_message = structured_prompt

        if perspective == "multi":
            user_message = build_multi_perspective_prompt(structured_prompt)
        elif analysis_focus:
            user_message = get_analysis_prompt(structured_prompt, analysis_focus)

        report = self._call_api(user_message, system_prompt=system_prompt)
        return report

    def generate_deep_analysis_stream(self, structured_prompt: str,
                                     analysis_focus: str = None,
                                     perspective: str = None,
                                     callback=None,
                                     system_prompt: str = None,
                                     cancel_event=None) -> AnalysisReport:
        """
        流式生成深度分析报告

        Args:
            cancel_event: threading.Event，设置后中止流式读取
        """
        if not self.config.api_key:
            return AnalysisReport(error="API Key 未设置", success=False)

        if not HAS_REQUESTS:
            return AnalysisReport(error="requests 库未安装", success=False)

        from .prompts import (
            DEEP_ANALYSIS_SYSTEM_PROMPT, get_analysis_prompt,
            build_multi_perspective_prompt, ANALYST_ROLES,
        )

        if system_prompt is None:
            perspective_map = {
                "value": ANALYST_ROLES["value"]["system_prompt"],
                "growth": ANALYST_ROLES["growth"]["system_prompt"],
                "risk": ANALYST_ROLES["risk"]["system_prompt"],
            }
            system_prompt = perspective_map.get(perspective, DEEP_ANALYSIS_SYSTEM_PROMPT)
        user_message = structured_prompt

        if perspective == "multi":
            user_message = build_multi_perspective_prompt(structured_prompt)
        elif analysis_focus:
            user_message = get_analysis_prompt(structured_prompt, analysis_focus)

        url = f"{self.config.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }

        self._apply_thinking_config(payload)

        report = AnalysisReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            model=self.config.model,
        )

        try:
            resp = requests.post(url, headers=headers, json=payload,
                                 timeout=self.config.timeout, stream=True)
            if resp.status_code != 200:
                report.error = f"API 返回错误 ({resp.status_code})"
                return report

            full_content = ""
            full_reasoning = ""
            for line in resp.iter_lines():
                if cancel_event and cancel_event.is_set():
                    resp.close()
                    if callback:
                        callback("", True, reasoning="")
                    break
                if not line:
                    continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]":
                    if callback:
                        callback("", True, reasoning="")
                    break
                try:
                    chunk = json.loads(line)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    reasoning = delta.get("reasoning_content", "")
                    if reasoning:
                        full_reasoning += reasoning
                    if content or reasoning:
                        full_content += content
                        if callback:
                            callback(content, False, reasoning=reasoning)
                except json.JSONDecodeError:
                    continue

            report.content = full_content
            report.reasoning_content = full_reasoning
            report.success = True
        except Exception as e:
            report.error = f"流式调用失败: {str(e)}"

        return report

    def generate_with_tools(self, messages: list, tools: list, tool_executor,
                            system_prompt: str = None, max_tool_rounds: int = 3,
                            tool_callback=None) -> AnalysisReport:
        """支持工具调用的生成方法（非流式）"""
        url = f"{self.config.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        report = AnalysisReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            model=self.config.model,
        )
        tool_calls_log = []

        for round_num in range(max_tool_rounds):
            payload = {
                "model": self.config.model,
                "messages": all_messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "tools": tools,
                "tool_choice": "auto",
                "stream": False,
            }
            self._apply_thinking_config(payload)

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout)
                if resp.status_code != 200:
                    report.error = f"API 返回错误 ({resp.status_code})"
                    return report

                data = resp.json()
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                finish_reason = choice.get("finish_reason", "")

                # 如果有 tool_calls，执行工具并继续
                if finish_reason == "tool_calls" and message.get("tool_calls"):
                    all_messages.append(message)

                    for tc in message["tool_calls"]:
                        func = tc.get("function", {})
                        func_name = func.get("name", "")
                        func_args = json.loads(func.get("arguments", "{}"))

                        if tool_callback:
                            tool_callback(func_name)
                        result = tool_executor.execute(func_name, func_args)
                        tool_calls_log.append({"tool": func_name, "args": func_args, "result": result[:200]})

                        all_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        })
                    continue

                # 纯文本响应，完成
                report.content = message.get("content", "")
                report.reasoning_content = message.get("reasoning_content", "")
                report.success = True
                report.tool_calls_log = tool_calls_log
                return report

            except Exception as e:
                report.error = f"工具调用失败: {str(e)}"
                return report

        report.error = "超过最大工具调用轮数"
        return report


class DeepSeekStreamClient(DeepSeekClient):
    """支持流式输出的 DeepSeek 客户端"""

    def generate_report_stream(self, data: str, template: str = "综合分析",
                                custom_prompt: str = None, callback=None):
        """
        流式生成分析报告

        Args:
            data: 财务数据文本
            template: 分析模板名称
            custom_prompt: 自定义提示词
            callback: 回调函数 callback(chunk_text: str, is_done: bool)

        Returns:
            AnalysisReport 对象
        """
        if not self.config.api_key:
            return AnalysisReport(error="API Key 未设置", success=False)

        if not HAS_REQUESTS:
            return AnalysisReport(error="requests 库未安装", success=False)

        if template == "自定义" and custom_prompt:
            user_message = f"{custom_prompt}\n\n{data}"
        else:
            tpl = self.ANALYSIS_TEMPLATES.get(template, self.ANALYSIS_TEMPLATES["综合分析"])
            user_message = tpl.format(data=data)

        url = f"{self.config.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }

        self._apply_thinking_config(payload)

        report = AnalysisReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            model=self.config.model,
        )

        try:
            logger.info(f"流式调用 DeepSeek API: {self.config.model}")
            resp = requests.post(url, headers=headers, json=payload,
                                 timeout=self.config.timeout, stream=True)

            if resp.status_code != 200:
                report.error = f"API 返回错误 ({resp.status_code})"
                return report

            full_content = ""
            full_reasoning = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]":
                    if callback:
                        callback("", True, reasoning="")
                    break
                try:
                    chunk = json.loads(line)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    reasoning = delta.get("reasoning_content", "")
                    if reasoning:
                        full_reasoning += reasoning
                    if content or reasoning:
                        full_content += content
                        if callback:
                            callback(content, False, reasoning=reasoning)
                except json.JSONDecodeError:
                    continue

            report.content = full_content
            report.reasoning_content = full_reasoning
            report.summary = full_content[:200] + "..." if len(full_content) > 200 else full_content
            report.success = True
            logger.info("流式 API 调用完成")

        except Exception as e:
            report.error = f"流式调用失败: {str(e)}"
            logger.error(f"流式 API 异常: {e}")

        return report

    def chat_stream(self, message: str, system_prompt: str = None):
        """
        通用流式对话接口（供 DeepSeekPanel 使用）

        Args:
            message: 用户消息
            system_prompt: 系统提示词（可选）

        Yields:
            dict: {"type": "reasoning"|"content"|"error", "content": str}
        """
        if not self.config.api_key:
            yield {"type": "error", "content": "API Key 未设置"}
            return

        url = f"{self.config.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        sys_msg = system_prompt or self.SYSTEM_PROMPT
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": message},
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }

        self._apply_thinking_config(payload)

        try:
            resp = requests.post(url, headers=headers, json=payload,
                                 timeout=self.config.timeout, stream=True)
            if resp.status_code != 200:
                yield {"type": "error", "content": f"API 返回错误 ({resp.status_code})"}
                return

            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(line)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    reasoning = delta.get("reasoning_content", "")
                    if reasoning:
                        yield {"type": "reasoning", "content": reasoning}
                    if content:
                        yield {"type": "content", "content": content}
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            yield {"type": "error", "content": f"请求失败: {str(e)}"}

"""
Prompt 模板持久化存储

JSON 文件存储于 ~/.financialanalyzer/prompts/
系统预置模板不可删除，用户模板可自由 CRUD。
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from ..config import USER_DATA_DIR
from .prompt_framework import (
    HARVARD_FRAMEWORK,
    CROSSCHECK_FRAMEWORK,
    LIFECYCLE_FRAMEWORK,
    WARNING_SIGNALS_FRAMEWORK,
    OUTPUT_FORMAT_STRUCTURED,
)

PROMPTS_DIR = USER_DATA_DIR / "prompts"

# 系统预置模板名称集合（不可删除/覆盖）
_DEFAULT_NAMES = {"深度分析-默认", "快速问答-默认"}

# 系统预置模板定义
_DEFAULT_DEEP = {
    "name": "深度分析-默认",
    "description": "包含哈佛分析、三表联动、生命周期、预警清单的完整深度分析框架",
    "mode": "deep",
    "system_role": "你是一位拥有20年经验的高级财务分析师，精通A股、港股和美股市场。你的分析以严谨、深刻和富有洞察力著称。请基于提供的财务数据和分析框架，进行深入、系统的分析。",
    "frameworks": {
        "harvard": HARVARD_FRAMEWORK.strip(),
        "crosscheck": CROSSCHECK_FRAMEWORK.strip(),
        "lifecycle": LIFECYCLE_FRAMEWORK.strip(),
        "warnings": WARNING_SIGNALS_FRAMEWORK.strip(),
    },
    "output_format": OUTPUT_FORMAT_STRUCTURED.strip(),
}

_DEFAULT_QUICK = {
    "name": "快速问答-默认",
    "description": "轻量快速问答，仅注入数据不加载分析框架",
    "mode": "quick",
    "system_role": "你是一位专业的财务分析师，请基于提供的财务数据，用简洁、专业的中文回答问题。",
    "frameworks": {},
    "output_format": OUTPUT_FORMAT_STRUCTURED.strip(),
}


class PromptsStore:
    """Prompt 模板 CRUD 管理器"""

    def __init__(self, prompts_dir: Path | None = None):
        self._dir = Path(prompts_dir) if prompts_dir else PROMPTS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self):
        """确保系统预置模板存在"""
        for template in [_DEFAULT_DEEP, _DEFAULT_QUICK]:
            fpath = self._dir / f"{template['name']}.json"
            if not fpath.exists():
                data = dict(template)
                data["created_at"] = datetime.now(timezone.utc).isoformat()
                data["updated_at"] = data["created_at"]
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    def _is_default(self, name: str) -> bool:
        """系统预置模板不可删除/覆盖"""
        return name in _DEFAULT_NAMES

    def _file_path(self, name: str) -> Path:
        safe = name.replace("/", "_").replace("\\", "_")
        return self._dir / f"{safe}.json"

    def list_templates(self) -> list[dict]:
        """列出所有模板（摘要：name + description + mode）"""
        result = []
        for fpath in sorted(self._dir.glob("*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result.append({
                    "name": data.get("name", fpath.stem),
                    "description": data.get("description", ""),
                    "mode": data.get("mode", "deep"),
                    "is_default": data.get("name", "") in _DEFAULT_NAMES,
                })
            except Exception:
                pass
        return result

    def get_template(self, name: str) -> dict | None:
        """获取单个模板完整内容"""
        fpath = self._file_path(name)
        if not fpath.exists():
            return None
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_template(self, name: str, data: dict) -> bool:
        """创建或更新模板"""
        if self._is_default(name):
            return False
        data["name"] = name
        now = datetime.now(timezone.utc).isoformat()
        if "created_at" not in data:
            data["created_at"] = now
        data["updated_at"] = now
        fpath = self._file_path(name)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def delete_template(self, name: str) -> bool:
        """删除模板（系统预置不可删）"""
        if self._is_default(name):
            return False
        fpath = self._file_path(name)
        if not fpath.exists():
            return False
        try:
            fpath.unlink()
            return True
        except Exception:
            return False

    def duplicate_template(self, source_name: str, new_name: str) -> bool:
        """复制模板"""
        if self._is_default(new_name):
            return False
        source = self.get_template(source_name)
        if source is None:
            return False
        new_data = dict(source)
        return self.save_template(new_name, new_data)

    def export_template(self, name: str) -> str | None:
        """导出模板为 JSON 字符串"""
        data = self.get_template(name)
        if data is None:
            return None
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_template(self, json_str: str) -> bool:
        """从 JSON 字符串导入模板"""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return False
        name = data.get("name", "")
        if not name:
            return False
        return self.save_template(name, data)

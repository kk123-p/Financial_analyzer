# AI 财务分析模块 UX 优化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 Prompt 工程实验室（可编辑/保存/切换模板）、增加财务数据与 Prompt 查看按钮、辩论 UI 重布局为四区域（三列+总结+追问+导出）。

**Architecture:** 后端新增 `PromptStore` 管理 JSON 文件模板存储，`PromptBuilder` 支持从模板 dict 动态加载框架；前端 AI Tab 增加工具栏按钮和模态弹窗，辩论 Tab 重写为三列独立滚动布局。

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, vanilla JS, Precision Glass CSS tokens

---

## 文件结构

```
financial_analyzer/ai/
├── prompt_framework.py     # MODIFY: PromptBuilder 支持 with_template()
└── prompt_store.py         # NEW: PromptsStore CRUD + 文件存储

financial_analyzer/web/
├── routes/ai_api.py        # MODIFY: 新增 /ai/prompts/*, /ai/report, /ai/debate/export
├── static/css/chat.css     # MODIFY: 追加辩论四区域、模态弹窗样式
├── static/css/prompt-lab.css  # NEW: Prompt 编辑器 modal 专用样式
├── static/js/app.js        # MODIFY: 工具栏按钮、模板选择器、辩论布局重写、导出
└── templates/base.html     # MODIFY: AI Tab 工具栏、辩论 Tab 四区域 HTML

tests/
└── test_prompt_store.py    # NEW: PromptsStore 单元测试
```

---

## Task 1: PromptsStore — 模板存储引擎

**Files:**
- Create: `financial_analyzer/ai/prompt_store.py`
- Create: `tests/test_prompt_store.py`

- [ ] **Step 1: 编写 PromptsStore 测试**

```python
# tests/test_prompt_store.py
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import tempfile
import os

# 用临时目录隔离测试
TEST_PROMTS_DIR = Path(tempfile.mkdtemp()) / "prompts"


def _make_store():
    from financial_analyzer.ai.prompt_store import PromptsStore
    return PromptsStore(prompts_dir=TEST_PROMTS_DIR)


def _put_template(store, name, **overrides):
    data = {
        "name": name,
        "description": "测试模板",
        "mode": "deep",
        "system_role": "你是一位财务分析师。",
        "frameworks": {
            "harvard": "哈佛分析框架内容",
            "crosscheck": "三表联动验证内容",
            "lifecycle": "生命周期定位内容",
            "warnings": "利润质量预警内容"
        },
        "output_format": "输出格式要求内容"
    }
    data.update(overrides)
    store.save_template(name, data)


class TestPromptsStoreList:
    def test_list_empty_returns_defaults(self):
        store = _make_store()
        names = [t["name"] for t in store.list_templates()]
        assert "深度分析-默认" in names
        assert "快速问答-默认" in names

    def test_list_includes_custom(self):
        store = _make_store()
        _put_template(store, "我的自定义模板")
        names = [t["name"] for t in store.list_templates()]
        assert "我的自定义模板" in names


class TestPromptsStoreGet:
    def test_get_default_deep_template(self):
        store = _make_store()
        t = store.get_template("深度分析-默认")
        assert t is not None
        assert t["mode"] == "deep"
        assert "harvard" in t["frameworks"]
        assert t["system_role"]

    def test_get_nonexistent_returns_none(self):
        store = _make_store()
        assert store.get_template("不存在的模板") is None


class TestPromptsStoreSave:
    def test_save_and_retrieve_custom_template(self):
        store = _make_store()
        data = {
            "name": "测试模板",
            "description": "desc",
            "mode": "deep",
            "system_role": "test role",
            "frameworks": {"harvard": "test hf"},
            "output_format": "test fmt"
        }
        store.save_template("测试模板", data)
        t = store.get_template("测试模板")
        assert t["name"] == "测试模板"
        assert t["frameworks"]["harvard"] == "test hf"

    def test_save_updates_existing(self):
        store = _make_store()
        _put_template(store, "测试模板")
        store.save_template("测试模板", {"name": "测试模板", "mode": "quick", "system_role": "updated", "frameworks": {}, "output_format": ""})
        t = store.get_template("测试模板")
        assert t["mode"] == "quick"


class TestPromptsStoreDelete:
    def test_delete_custom_template(self):
        store = _make_store()
        _put_template(store, "可删除模板")
        assert store.delete_template("可删除模板") is True
        assert store.get_template("可删除模板") is None

    def test_delete_default_template_fails(self):
        store = _make_store()
        assert store.delete_template("深度分析-默认") is False

    def test_delete_nonexistent_fails(self):
        store = _make_store()
        assert store.delete_template("不存在的") is False


class TestPromptsStoreDuplicate:
    def test_duplicate_creates_copy(self):
        store = _make_store()
        assert store.duplicate_template("深度分析-默认", "我的副本") is True
        t = store.get_template("我的副本")
        assert t is not None
        assert t["mode"] == "deep"

    def test_duplicate_nonexistent_fails(self):
        store = _make_store()
        assert store.duplicate_template("不存在的", "副本") is False


class TestPromptsStoreExportImport:
    def test_export_returns_json_string(self):
        store = _make_store()
        json_str = store.export_template("深度分析-默认")
        assert json_str is not None
        data = json.loads(json_str)
        assert data["name"] == "深度分析-默认"

    def test_import_creates_template(self):
        store = _make_store()
        json_str = json.dumps({
            "name": "导入的模板",
            "description": "imported",
            "mode": "deep",
            "system_role": "role",
            "frameworks": {"harvard": "content"},
            "output_format": "fmt"
        })
        assert store.import_template(json_str) is True
        t = store.get_template("导入的模板")
        assert t is not None

    def test_import_invalid_json_fails(self):
        store = _make_store()
        assert store.import_template("not json") is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_prompt_store.py -v
```
Expected: all FAIL (module not found)

- [ ] **Step 3: 实现 PromptsStore**

```python
# financial_analyzer/ai/prompt_store.py
"""
Prompt 模板持久化存储

JSON 文件存储于 ~/.financialanalyzer/prompts/
系统预置模板 (_ 前缀) 不可删除，用户模板可自由 CRUD。
"""
from __future__ import annotations
import json
import shutil
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
            fname = f"_{template['name']}.json"
            fpath = self._dir / fname
            if not fpath.exists():
                data = dict(template)
                data["created_at"] = datetime.now(timezone.utc).isoformat()
                data["updated_at"] = data["created_at"]
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    def _is_default(self, name: str) -> bool:
        """系统预置模板以 _ 开头"""
        return name.startswith("_")

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
                    "is_default": fpath.name.startswith("_"),
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_prompt_store.py -v
```
Expected: all PASS

- [ ] **Step 5: 提交**

```bash
git add financial_analyzer/ai/prompt_store.py tests/test_prompt_store.py
git commit -m "feat: add PromptsStore for editable prompt template management

JSON file storage under ~/.financialanalyzer/prompts/. System defaults
(_ prefix) are protected from deletion. Supports CRUD, duplicate,
export, and import of prompt templates.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: PromptBuilder 集成 — 支持动态模板

**Files:**
- Modify: `financial_analyzer/ai/prompt_framework.py:138-228`

- [ ] **Step 1: 添加 with_template() 方法并改造 build()**

在 `PromptBuilder` 类中新增 `with_template()` 方法，修改 `build()` 使框架优先从模板加载。

修改 `financial_analyzer/ai/prompt_framework.py` 中 `PromptBuilder` 类：

```python
class PromptBuilder:
    """可组合的提示词构建器"""

    FRAMEWORKS = {
        "harvard": ("哈佛分析框架", HARVARD_FRAMEWORK),
        "crosscheck": ("三表联动验证", CROSSCHECK_FRAMEWORK),
        "lifecycle": ("生命周期定位", LIFECYCLE_FRAMEWORK),
        "warnings": ("利润质量预警清单", WARNING_SIGNALS_FRAMEWORK),
    }

    def __init__(self, company_name: str = ""):
        self._company_name = company_name
        self._data: dict | None = None
        self._frameworks: list[str] = []
        self._signals: list | None = None
        self._output_format: str | None = None
        self._mode: str = "quick"
        self._context: str | None = None
        self._question: str = ""
        self._template: dict | None = None  # 新增：用户选择的模板

    # ... with_data, with_framework, with_signals, with_output_format,
    #     with_mode, with_context, with_question 保持不变 ...

    def with_template(self, template: dict) -> "PromptBuilder":
        """从 Prompt 模板加载配置（优先级高于硬编码默认值）"""
        self._template = template
        if template:
            # 模板的 mode 覆盖当前 mode
            if template.get("mode"):
                self._mode = template["mode"]
            # 模板的 frameworks 加载为用户选择的框架
            if template.get("frameworks"):
                self._frameworks = list(template["frameworks"].keys())
        return self

    def build(self) -> str:
        parts = []
        parts.append(self._build_role())

        if self._data:
            parts.append(self._format_data(self._data))

        if self._question and self._mode != "quick":
            parts.append(f"## 用户问题\n{self._question}")

        if self._mode == "followup" and self._context:
            parts.append(f"## 之前的分析\n{self._context}")
            parts.append("请基于上述分析，回答以下追问：")

        # 深度/辩论模式：加载框架
        if self._mode in ("deep", "debate"):
            for fw_key in self._frameworks:
                template_content = self._get_framework_content(fw_key)
                if template_content:
                    parts.append(f"---\n{template_content}")

        if self._signals and self._mode in ("deep", "debate"):
            parts.append(self._format_signals(self._signals))

        # 输出格式：优先模板，其次参数，最后默认
        fmt = None
        if self._template and self._template.get("output_format"):
            fmt = self._template["output_format"]
        elif self._output_format:
            fmt = None  # 使用 OUTPUT_FORMAT_STRUCTURED
        if self._mode in ("quick", "deep", "followup"):
            parts.append(fmt if fmt else OUTPUT_FORMAT_STRUCTURED)

        if self._mode == "debate":
            parts.append("\n请启动三视角辩论流程。")
        elif self._mode == "deep":
            parts.append("\n请基于以上框架和数据进行全面深度分析。")
        elif self._mode == "quick":
            if self._question:
                parts.append(f"\n## 用户问题\n{self._question}")
            parts.append("\n请基于数据给出简洁、专业的回答。")

        return "\n\n".join(parts)

    def _get_framework_content(self, fw_key: str) -> str | None:
        """获取框架内容：优先模板，fallback 硬编码"""
        if self._template and self._template.get("frameworks", {}).get(fw_key):
            return self._template["frameworks"][fw_key]
        _, template = self.FRAMEWORKS.get(fw_key, ("", ""))
        return template if template else None

    def _build_role(self) -> str:
        # 优先使用模板中的 system_role
        if self._template and self._template.get("system_role"):
            role = self._template["system_role"]
        else:
            mode_roles = {
                "quick": "你是一位专业的财务分析师，请基于提供的财务数据，用简洁、专业的中文回答问题。",
                "deep": "你是一位拥有20年经验的高级财务分析师，精通A股、港股和美股市场。你的分析以严谨、深刻和富有洞察力著称。请基于提供的财务数据和分析框架，进行深入、系统的分析。",
                "debate": "你将同时扮演三位不同视角的资深分析师（格雷厄姆式价值分析师、费雪式成长分析师、塔勒布式风控师），对以下公司进行多维度辩论分析。",
                "followup": "你是一位专业的财务分析师，请基于之前的分析上下文和数据，回答用户的追问。",
            }
            role = mode_roles.get(self._mode, mode_roles["quick"])

        if self._mode == "quick" and self._company_name:
            return f"{role}\n\n**分析对象：{self._company_name}**\n\n请给出快速分析："
        if self._company_name:
            return f"{role}\n\n**分析对象：{self._company_name}**"
        return role
```

- [ ] **Step 2: 验证 PromptBuilder 向后兼容**

```bash
python -c "
from financial_analyzer.ai.prompt_framework import PromptBuilder
# 不使用模板时的行为应不变
builder = PromptBuilder('测试公司')
builder.with_mode('deep')
builder.with_framework('harvard')
builder.with_framework('crosscheck')
builder.with_output_format('structured')
prompt = builder.build()
assert '哈佛分析框架' in prompt
assert '三表联动验证' in prompt
assert '测试公司' in prompt
print('Backward compatibility OK')

# 使用模板时应加载模板内容
template = {
    'name': '测试', 'mode': 'deep',
    'system_role': '自定义角色：你是金融专家。',
    'frameworks': {'harvard': '自定义哈佛框架内容'},
    'output_format': '自定义输出格式'
}
builder2 = PromptBuilder('测试公司')
builder2.with_template(template)
prompt2 = builder2.build()
assert '自定义角色' in prompt2
assert '自定义哈佛框架内容' in prompt2
assert '自定义输出格式' in prompt2
print('Template loading OK')
"
```

Expected: "Backward compatibility OK" + "Template loading OK"

- [ ] **Step 3: 提交**

```bash
git add financial_analyzer/ai/prompt_framework.py
git commit -m "feat: add with_template() to PromptBuilder for dynamic template loading

PromptBuilder now accepts a template dict via with_template(). Framework
content, system role, and output format are loaded from the template
when available, falling back to hardcoded defaults for backward
compatibility.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: Prompt 管理 API

**Files:**
- Modify: `financial_analyzer/web/routes/ai_api.py` (追加 endpoint)

- [ ] **Step 1: 在 ai_api.py 末尾追加 Prompt 管理 REST API**

```python
# 追加到 financial_analyzer/web/routes/ai_api.py 末尾

# ============================================================================
# Phase 2 UX: Prompt 模板管理 API
# ============================================================================

from fastapi.responses import PlainTextResponse
from fastapi import UploadFile


@router.get("/prompts")
async def list_prompts():
    """列出所有 Prompt 模板"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    store = PromptsStore()
    return store.list_templates()


@router.get("/prompts/{name:path}")
async def get_prompt(name: str):
    """获取单个 Prompt 模板完整内容"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    store = PromptsStore()
    template = store.get_template(name)
    if template is None:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "模板不存在"}, status_code=404)
    return template


@router.put("/prompts/{name:path}")
async def save_prompt(name: str, request: Request):
    """保存/更新 Prompt 模板"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    data = await request.json()
    store = PromptsStore()
    ok = store.save_template(name, data)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "不能覆盖系统预置模板"}, status_code=403)
    return {"status": "ok"}


@router.delete("/prompts/{name:path}")
async def delete_prompt(name: str):
    """删除 Prompt 模板"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    store = PromptsStore()
    ok = store.delete_template(name)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "模板不存在或为系统预置"}, status_code=403)
    return {"status": "ok"}


@router.post("/prompts/{name:path}/duplicate")
async def duplicate_prompt(name: str, request: Request):
    """复制 Prompt 模板"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    body = await request.json()
    new_name = body.get("new_name", name + " - 副本")
    store = PromptsStore()
    ok = store.duplicate_template(name, new_name)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "复制失败"}, status_code=400)
    return {"status": "ok", "new_name": new_name}


@router.get("/prompts/{name:path}/export")
async def export_prompt(name: str):
    """导出 Prompt 模板为 JSON 文件下载"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    store = PromptsStore()
    json_str = store.export_template(name)
    if json_str is None:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "模板不存在"}, status_code=404)
    safe_name = name.replace("/", "_").replace("\\", "_")
    return PlainTextResponse(
        json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.json"'}
    )


@router.post("/prompts/import")
async def import_prompt(file: UploadFile):
    """导入 Prompt 模板（上传 JSON 文件）"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    try:
        content = await file.read()
        json_str = content.decode("utf-8")
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "文件读取失败"}, status_code=400)
    store = PromptsStore()
    ok = store.import_template(json_str)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "导入失败，JSON 格式不正确"}, status_code=400)
    return {"status": "ok"}
```

- [ ] **Step 2: 验证 API 端点已注册**

```bash
python -c "
from financial_analyzer.web.routes.ai_api import router
paths = [r.path for r in router.routes]
assert '/ai/prompts' in paths
assert '/ai/prompts/{name:path}' in paths
assert '/ai/prompts/{name:path}/export' in paths
assert '/ai/prompts/import' in paths
print('All prompt API routes registered')
print(paths)
"
```

Expected: All prompt API routes registered

- [ ] **Step 3: 提交**

```bash
git add financial_analyzer/web/routes/ai_api.py
git commit -m "feat: add /ai/prompts REST API for template CRUD

Endpoints for list, get, save, delete, duplicate, export (JSON download),
and import (file upload) of prompt templates. System defaults protected.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: 财务数据报告 API

**Files:**
- Modify: `financial_analyzer/web/routes/ai_api.py` (追加 endpoint)

- [ ] **Step 1: 新增 `/ai/report` 和 `/ai/report/export` 端点**

将 ReportBuilder 输出缓存到 session 中，通过 API 获取。

```python
# 追加到 financial_analyzer/web/routes/ai_api.py


@router.get("/report")
async def get_financial_report(request: Request):
    """获取当前 session 的财务体检报告"""
    session = _get_session(request)
    data_raw = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data_raw or not stock_code:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "请先获取财务数据"}, status_code=400)

    # 优先返回缓存的 report
    cached = session.get("ai_report")
    if cached:
        return cached

    # 按需构建
    try:
        from financial_analyzer.ai.report_builder import ReportBuilder
        import pandas as pd
        data = {k: pd.DataFrame(v) for k, v in data_raw.items()}
        report = ReportBuilder.build(data, stock_code)
        session["ai_report"] = report
        return report
    except Exception as e:
        logger.error(f"Report build error: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/report/export")
async def export_financial_report(request: Request):
    """导出财务体检报告为 JSON 文件"""
    session = _get_session(request)
    data_raw = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data_raw or not stock_code:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "请先获取财务数据"}, status_code=400)

    try:
        from financial_analyzer.ai.report_builder import ReportBuilder
        import pandas as pd
        import json
        data = {k: pd.DataFrame(v) for k, v in data_raw.items()}
        report = ReportBuilder.build(data, stock_code)
        session["ai_report"] = report
        json_str = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        safe_name = stock_code.replace("/", "_").replace("\\", "_")
        return PlainTextResponse(
            json_str,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="report_{safe_name}.json"'}
        )
    except Exception as e:
        logger.error(f"Report export error: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": str(e)}, status_code=500)
```

- [ ] **Step 2: 验证端点**

```bash
python -c "
from financial_analyzer.web.routes.ai_api import router
paths = [r.path for r in router.routes]
assert '/ai/report' in paths
assert '/ai/report/export' in paths
print('Report API routes registered')
"
```

Expected: "Report API routes registered"

- [ ] **Step 3: 提交**

```bash
git add financial_analyzer/web/routes/ai_api.py
git commit -m "feat: add /ai/report and /ai/report/export endpoints

GET /ai/report returns the structured financial health report for current
session. GET /ai/report/export downloads it as JSON. Report is cached in
session after first build.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: 辩论导出 API

**Files:**
- Modify: `financial_analyzer/web/routes/ai_api.py` (追加 endpoint)

- [ ] **Step 1: 新增 `/ai/debate/export/{format}` 端点**

辩论内容通过 session 或请求体传递（前端收集已完成的辩论文本）。

```python
# 追加到 financial_analyzer/web/routes/ai_api.py


@router.post("/debate/export/{fmt}")
async def export_debate_result(fmt: str, request: Request):
    """
    导出辩论结果为 Markdown 或 HTML

    Args:
        fmt: "md" 或 "html"
    Body: {"debate_data": {...}, "stock_code": "..."}
    """
    from datetime import datetime
    body = await request.json()
    debate_data = body.get("debate_data", {})
    stock_code = body.get("stock_code", "")
    company_name = body.get("company_name", stock_code)

    if not debate_data:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "缺少辩论数据"}, status_code=400)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    safe_name = stock_code.replace("/", "_").replace("\\", "_")

    if fmt == "md":
        md = _build_debate_markdown(debate_data, company_name, stock_code, now)
        return PlainTextResponse(
            md, media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="debate_{safe_name}.md"'}
        )
    elif fmt == "html":
        html = _build_debate_html(debate_data, company_name, stock_code, now)
        return PlainTextResponse(
            html, media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="debate_{safe_name}.html"'}
        )
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": f"不支持的格式: {fmt}"}, status_code=400)


def _build_debate_markdown(debate_data: dict, company_name: str, stock_code: str, now: str) -> str:
    """将辩论数据组装为 Markdown"""
    lines = [
        f"# 三方投研辩论 — {company_name}({stock_code})",
        f"> 辩论时间：{now}",
        "",
    ]

    ANALYST_LABELS = {
        "value": "📊 格雷厄姆式价值分析师",
        "growth": "🚀 费雪式成长分析师",
        "risk": "🛡️ 塔勒布式风控师",
    }

    # 各轮辩论
    for round_key, round_title in [("round1", "第1轮：独立陈述"),
                                     ("round2", "第2轮：交叉质询"),
                                     ("round3", "第3轮：共识与情景概率")]:
        lines.append(f"## {round_title}")
        statements = debate_data.get(round_key, {})
        if isinstance(statements, dict):
            for role_key in ["value", "growth", "risk"]:
                content = statements.get(role_key, "")
                label = ANALYST_LABELS.get(role_key, role_key)
                lines.append(f"\n### {label}")
                lines.append(content)
        elif isinstance(statements, str):
            lines.append(statements)
        lines.append("")

    # 综合共识
    consensus = debate_data.get("consensus", "")
    if consensus:
        lines.append("## 综合共识")
        lines.append(consensus)
        lines.append("")

    # 追问
    followups = debate_data.get("followups", [])
    if followups:
        lines.append("## 用户追问")
        for fu in followups:
            lines.append(f"\n> {fu.get('question', '')}")
            for role_key in ["value", "growth", "risk"]:
                content = fu.get(role_key, "")
                label = ANALYST_LABELS.get(role_key, role_key)
                if content:
                    lines.append(f"\n### {label}")
                    lines.append(content)
            lines.append("")

    return "\n".join(lines)


def _build_debate_html(debate_data: dict, company_name: str, stock_code: str, now: str) -> str:
    """将辩论数据组装为独立 HTML 页面"""
    md_content = _build_debate_markdown(debate_data, company_name, stock_code, now)
    # 简单的 markdown 转 HTML（段落 + 标题）
    html_body_parts = []
    for line in md_content.split("\n"):
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith("# "):
            html_body_parts.append(f'<h1 style="color:#F1F5F9;border-bottom:1px solid rgba(59,130,246,0.2);padding-bottom:8px;">{line[2:]}</h1>')
        elif line.startswith("## "):
            html_body_parts.append(f'<h2 style="color:#E2E8F0;margin-top:24px;">{line[3:]}</h2>')
        elif line.startswith("### "):
            html_body_parts.append(f'<h3 style="color:#94A3B8;margin-top:16px;">{line[4:]}</h3>')
        elif line.startswith("> "):
            html_body_parts.append(f'<blockquote style="color:#94A3B8;border-left:3px solid rgba(59,130,246,0.3);padding-left:12px;margin:8px 0;">{line[2:]}</blockquote>')
        elif line.strip():
            html_body_parts.append(f'<p style="color:#CBD5E1;line-height:1.8;">{line}</p>')
        else:
            html_body_parts.append("<br>")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>三方辩论 — {company_name}</title>
<style>
  body {{
    max-width: 900px; margin: 40px auto; padding: 20px;
    background: #0B1021; color: #CBD5E1;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.7;
  }}
  h1 {{ color: #F1F5F9; border-bottom: 1px solid rgba(59,130,246,0.2); padding-bottom: 8px; }}
  h2 {{ color: #E2E8F0; margin-top: 24px; }}
  h3 {{ color: #94A3B8; margin-top: 16px; }}
  blockquote {{ color: #94A3B8; border-left: 3px solid rgba(59,130,246,0.3); padding-left: 12px; margin: 8px 0; }}
</style>
</head>
<body>
{"".join(html_body_parts)}
</body>
</html>"""
```

- [ ] **Step 2: 验证端点**

```bash
python -c "
from financial_analyzer.web.routes.ai_api import router
paths = [r.path for r in router.routes]
assert '/ai/debate/export/{fmt}' in paths
print('Debate export route registered')
"
```

Expected: "Debate export route registered"

- [ ] **Step 3: 提交**

```bash
git add financial_analyzer/web/routes/ai_api.py
git commit -m "feat: add /ai/debate/export/{fmt} for Markdown/HTML debate export

POST endpoint accepts debate data JSON and returns formatted Markdown
or standalone HTML file with Precision Glass dark theme styling.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: CSS — Prompt 编辑器 + 辩论四区域样式

**Files:**
- Create: `financial_analyzer/web/static/css/prompt-lab.css`
- Modify: `financial_analyzer/web/static/css/chat.css` (末尾追加)

- [ ] **Step 1: 创建 prompt-lab.css**

```css
/* ============================================================================
   Prompt Lab — 模板编辑器模态弹窗样式
   ============================================================================ */

.prompt-editor-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(2, 4, 10, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  align-items: center;
  justify-content: center;
}

.prompt-editor-overlay.modal--visible {
  display: flex;
}

.prompt-editor {
  width: min(800px, 95vw);
  max-height: 90vh;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--blur-card)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--blur-card)) saturate(140%);
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modal-in 200ms var(--ease-out-expo) both;
}

@keyframes modal-in {
  from { opacity: 0; transform: scale(0.96) translateY(10px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
}

.prompt-editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
  flex-shrink: 0;
}

.prompt-editor-header h3 {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.prompt-editor-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: color var(--duration-fast) var(--ease-out-expo);
}

.prompt-editor-close:hover {
  color: var(--text-primary);
}

.prompt-editor-body {
  flex: 1 1 0;
  overflow-y: auto;
  padding: 16px 20px;
  min-height: 0;
}

.prompt-editor-body::-webkit-scrollbar { width: 4px; }
.prompt-editor-body::-webkit-scrollbar-track { background: transparent; }
.prompt-editor-body::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.18);
  border-radius: 2px;
}

.prompt-editor-field {
  margin-bottom: 14px;
}

.prompt-editor-field label {
  display: block;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.prompt-editor-field input[type="text"],
.prompt-editor-field select {
  width: 100%;
  padding: 8px 12px;
  background: rgba(6, 8, 14, 0.55);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
}

.prompt-editor-field input[type="text"]:focus,
.prompt-editor-field select:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  outline: none;
}

.prompt-editor-field textarea {
  width: 100%;
  min-height: 100px;
  padding: 10px 12px;
  background: rgba(6, 8, 14, 0.55);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: 'Cascadia Code', 'JetBrains Mono', 'Fira Code', monospace;
  line-height: 1.5;
  resize: vertical;
  tab-size: 2;
}

.prompt-editor-field textarea:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  outline: none;
}

.prompt-editor-footer {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.08);
  flex-shrink: 0;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.prompt-editor-footer button {
  padding: 7px 16px;
  border-radius: 6px;
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.pe-btn-cancel {
  background: transparent;
  border: 1px solid rgba(148, 163, 184, 0.15);
  color: var(--text-secondary);
}

.pe-btn-cancel:hover {
  background: rgba(148, 163, 184, 0.08);
  color: var(--text-primary);
}

.pe-btn-save {
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.25);
  color: var(--accent-primary);
}

.pe-btn-save:hover {
  background: rgba(59, 130, 246, 0.25);
}

.pe-btn-export {
  background: rgba(20, 184, 166, 0.1);
  border: 1px solid rgba(20, 184, 166, 0.2);
  color: var(--positive);
}

.pe-btn-export:hover {
  background: rgba(20, 184, 166, 0.18);
}

.pe-btn-import {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
  color: var(--warning);
}

.pe-btn-import:hover {
  background: rgba(245, 158, 11, 0.18);
}

.pe-btn-duplicate {
  background: rgba(167, 139, 250, 0.1);
  border: 1px solid rgba(167, 139, 250, 0.2);
  color: #A78BFA;
}

.pe-btn-duplicate:hover {
  background: rgba(167, 139, 250, 0.18);
}

/* ---- 数据/模板查看模态弹窗 ---- */
.viewer-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(2, 4, 10, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  align-items: center;
  justify-content: center;
}

.viewer-overlay.modal--visible {
  display: flex;
}

.viewer-modal {
  width: min(780px, 95vw);
  max-height: 88vh;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--blur-card)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--blur-card)) saturate(140%);
  border: 1px solid rgba(59, 130, 246, 0.10);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modal-in 200ms var(--ease-out-expo) both;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
  flex-shrink: 0;
}

.viewer-header h3 {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.viewer-body {
  flex: 1 1 0;
  overflow-y: auto;
  padding: 16px 20px;
  min-height: 0;
}

.viewer-body::-webkit-scrollbar { width: 4px; }
.viewer-body::-webkit-scrollbar-track { background: transparent; }
.viewer-body::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.18);
  border-radius: 2px;
}

.viewer-section {
  margin-bottom: 16px;
}

.viewer-section h4 {
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 6px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.06);
}

.viewer-section .kv-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.viewer-section .kv-row .kv-value {
  color: var(--text-primary);
  font-weight: 500;
}

.viewer-pre {
  background: rgba(6, 8, 14, 0.55);
  border: 1px solid rgba(59, 130, 246, 0.08);
  border-radius: 8px;
  padding: 14px;
  font-family: 'Cascadia Code', 'JetBrains Mono', 'Fira Code', monospace;
  font-size: var(--text-sm);
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: break-word;
}

.viewer-footer {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.08);
  flex-shrink: 0;
  justify-content: flex-end;
}

.viewer-footer button {
  padding: 7px 16px;
  border-radius: 6px;
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

/* ---- AI Tab 工具栏按钮 ---- */
.ai-toolbar {
  display: flex;
  gap: 8px;
  padding: 8px 20px;
  flex-shrink: 0;
  align-items: center;
}

.ai-toolbar-btn {
  padding: 5px 12px;
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-radius: 14px;
  background: rgba(17, 24, 50, 0.35);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out-expo);
  white-space: nowrap;
}

.ai-toolbar-btn:hover {
  background: rgba(59, 130, 246, 0.10);
  border-color: rgba(59, 130, 246, 0.25);
  color: var(--accent-primary);
}

.ai-toolbar select {
  padding: 5px 10px;
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  background: rgba(17, 24, 50, 0.45);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-family: var(--font-sans);
  cursor: pointer;
  max-width: 180px;
}

.ai-toolbar select:focus {
  border-color: var(--accent-primary);
  outline: none;
}
```

- [ ] **Step 2: 在 chat.css 末尾追加辩论四区域样式**

```css
/* 追加到 financial_analyzer/web/static/css/chat.css 末尾 */

/* ============================================================================
   Phase 2 UX: 辩论四区域布局
   ============================================================================ */

/* 辩论容器 — 竖向 flex */
.debate-layout {
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

/* 控制栏 */
.debate-control-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 20px;
  flex-shrink: 0;
  background: rgba(11, 16, 33, 0.35);
  border-bottom: 1px solid rgba(59, 130, 246, 0.06);
}

.debate-control-bar .debate-status {
  color: var(--text-muted);
  font-size: var(--text-xs);
  margin-left: auto;
}

/* 三列区域 */
.debate-columns {
  display: flex;
  gap: 6px;
  flex: 1 1 0;
  min-height: 0;
  padding: 8px;
  overflow: hidden;
}

.debate-column {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: rgba(17, 24, 50, 0.15);
  border: 1px solid rgba(148, 163, 184, 0.05);
  border-radius: 8px;
  overflow: hidden;
}

.debate-column-header {
  padding: 8px 10px;
  font-weight: 700;
  font-size: var(--text-xs);
  flex-shrink: 0;
}

.debate-column-body {
  flex: 1 1 0;
  overflow-y: auto;
  padding: 8px 10px;
  font-size: var(--text-sm);
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
  min-height: 0;
}

.debate-column-body::-webkit-scrollbar { width: 3px; }
.debate-column-body::-webkit-scrollbar-track { background: transparent; }
.debate-column-body::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.12);
  border-radius: 2px;
}

.debate-column--value  { border-top: 2px solid #3B82F6; }
.debate-column--growth { border-top: 2px solid #14B8A6; }
.debate-column--risk   { border-top: 2px solid #F59E0B; }

.debate-column--value  .debate-column-header { background: rgba(59, 130, 246, 0.06); color: #3B82F6; }
.debate-column--growth .debate-column-header { background: rgba(20, 184, 166, 0.06); color: #14B8A6; }
.debate-column--risk   .debate-column-header { background: rgba(245, 158, 11, 0.06); color: #F59E0B; }

/* 轮次标签 */
.debate-round-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: var(--text-2xs);
  font-weight: 600;
  color: var(--text-muted);
  background: rgba(59, 130, 246, 0.06);
  margin: 8px 0 4px;
}

/* 总结区 */
.debate-consensus-area {
  flex-shrink: 0;
  margin: 4px 8px;
  padding: 12px 14px;
  background: rgba(167, 139, 250, 0.05);
  border: 1px solid rgba(167, 139, 250, 0.15);
  border-radius: 8px;
  max-height: 150px;
  overflow-y: auto;
}

.debate-consensus-area .consensus-header {
  font-weight: 700;
  font-size: var(--text-xs);
  color: #A78BFA;
  margin-bottom: 6px;
}

.debate-consensus-area .consensus-body {
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: 1.7;
  white-space: pre-wrap;
}

.debate-consensus-area::-webkit-scrollbar { width: 3px; }
.debate-consensus-area::-webkit-scrollbar-track { background: transparent; }
.debate-consensus-area::-webkit-scrollbar-thumb {
  background: rgba(167, 139, 250, 0.15);
  border-radius: 2px;
}

/* 追问栏 */
.debate-followup-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 20px;
  flex-shrink: 0;
  background: rgba(11, 16, 33, 0.35);
  border-top: 1px solid rgba(59, 130, 246, 0.06);
  flex-wrap: wrap;
}

.debate-followup-bar input {
  flex: 1;
  min-width: 140px;
  background: rgba(6, 8, 14, 0.55);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(59, 130, 246, 0.15);
  color: var(--text-primary);
  padding: 8px 14px;
  border-radius: 8px;
  font-size: var(--text-sm);
  font-family: var(--font-sans);
}

.debate-followup-bar input:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  outline: none;
}

.debate-followup-bar input::placeholder {
  color: var(--text-muted);
}

.debate-followup-bar .btn-export {
  padding: 6px 12px;
  border: 1px solid rgba(20, 184, 166, 0.12);
  border-radius: 6px;
  background: rgba(20, 184, 166, 0.06);
  color: var(--positive);
  font-size: var(--text-xs);
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  white-space: nowrap;
}

.debate-followup-bar .btn-export:hover {
  background: rgba(20, 184, 166, 0.12);
  border-color: rgba(20, 184, 166, 0.25);
}
```

- [ ] **Step 3: 在 base.html 中引入 prompt-lab.css**

在 `base.html` 的 `<head>` 中已有 chat.css 的 link，在其后追加：

```html
<link rel="stylesheet" href="/static/css/prompt-lab.css">
```

- [ ] **Step 4: 提交**

```bash
git add financial_analyzer/web/static/css/prompt-lab.css financial_analyzer/web/static/css/chat.css financial_analyzer/web/templates/base.html
git commit -m "feat: add prompt-lab.css and debate 4-area layout styles

prompt-lab.css: template editor modal, data viewer modal, toolbar buttons.
chat.css additions: debate 3-column layout, consensus area, followup bar.
base.html: link to prompt-lab.css.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: 前端 — AI Tab 工具栏 + 数据/Prompt 查看模态弹窗

**Files:**
- Modify: `financial_analyzer/web/templates/base.html` (AI Tab 工具栏 + 模态弹窗 HTML)
- Modify: `financial_analyzer/web/static/js/app.js` (JS 逻辑)

- [ ] **Step 1: 更新 base.html AI Tab 的 HTML**

替换 `tab-ai` 中 chat-input-area 上方的区域，增加工具栏按钮。在 AI Tab 面板底部（`</div><!-- tab-ai -->` 前）追加两个模态弹窗的 HTML。

找到 `base.html` 中 `chat-input-area`，在其**上方**加入工具栏：

```html
<!-- 在 chat-input-area 之前插入 -->
<div class="ai-toolbar" id="ai-toolbar">
    <select id="prompt-template-selector" onchange="onTemplateChange()" title="选择 Prompt 模板">
        <option value="">加载中...</option>
    </select>
    <button class="ai-toolbar-btn" onclick="openPromptEditor()" title="编辑当前模板">📝 编辑Prompt</button>
    <button class="ai-toolbar-btn" onclick="openDataViewer()" title="查看财务数据报告">📊 财务数据报告</button>
    <button class="ai-toolbar-btn" onclick="openPromptPreview()" title="预览组装后的Prompt">📋 预览Prompt</button>
</div>
```

在 `tab-ai` 面板的 `</div>` 闭合之前（最后的 `</div>` 之前），追加两个模态弹窗：

```html
<!-- Prompt 编辑器模态弹窗 -->
<div class="prompt-editor-overlay" id="prompt-editor-overlay">
    <div class="prompt-editor">
        <div class="prompt-editor-header">
            <h3>编辑 Prompt 模板</h3>
            <button class="prompt-editor-close" onclick="closePromptEditor()">&times;</button>
        </div>
        <div class="prompt-editor-body">
            <div class="prompt-editor-field">
                <label>模板名称</label>
                <input type="text" id="pe-name" placeholder="模板名称">
            </div>
            <div class="prompt-editor-field">
                <label>描述</label>
                <input type="text" id="pe-desc" placeholder="简短描述">
            </div>
            <div class="prompt-editor-field">
                <label>适用模式</label>
                <select id="pe-mode">
                    <option value="deep">deep — 深度分析</option>
                    <option value="quick">quick — 快速问答</option>
                </select>
            </div>
            <div class="prompt-editor-field">
                <label>系统角色</label>
                <textarea id="pe-role" rows="3" placeholder="系统角色提示词..."></textarea>
            </div>
            <div class="prompt-editor-field">
                <label>哈佛分析框架</label>
                <textarea id="pe-harvard" rows="5" class="pe-framework"></textarea>
            </div>
            <div class="prompt-editor-field">
                <label>三表联动验证</label>
                <textarea id="pe-crosscheck" rows="5" class="pe-framework"></textarea>
            </div>
            <div class="prompt-editor-field">
                <label>生命周期定位</label>
                <textarea id="pe-lifecycle" rows="4" class="pe-framework"></textarea>
            </div>
            <div class="prompt-editor-field">
                <label>利润质量预警清单</label>
                <textarea id="pe-warnings" rows="5" class="pe-framework"></textarea>
            </div>
            <div class="prompt-editor-field">
                <label>输出格式</label>
                <textarea id="pe-output" rows="5" placeholder="输出格式要求..."></textarea>
            </div>
        </div>
        <div class="prompt-editor-footer">
            <button class="pe-btn-import" onclick="importTemplate()">📥 导入</button>
            <button class="pe-btn-export" onclick="exportTemplate()">📤 导出</button>
            <button class="pe-btn-duplicate" onclick="duplicateTemplate()">📋 另存为新模板</button>
            <span style="flex:1;"></span>
            <button class="pe-btn-cancel" onclick="closePromptEditor()">取消</button>
            <button class="pe-btn-save" onclick="saveTemplate()">保存</button>
        </div>
    </div>
</div>

<!-- 数据报告查看模态弹窗 -->
<div class="viewer-overlay" id="data-viewer-overlay">
    <div class="viewer-modal">
        <div class="viewer-header">
            <h3 id="data-viewer-title">财务体检报告</h3>
            <button class="prompt-editor-close" onclick="closeDataViewer()">&times;</button>
        </div>
        <div class="viewer-body" id="data-viewer-body">
            <p style="color:var(--text-muted);">加载中...</p>
        </div>
        <div class="viewer-footer">
            <button class="pe-btn-export" onclick="exportDataReport()">导出 JSON</button>
            <button class="pe-btn-cancel" onclick="closeDataViewer()">关闭</button>
        </div>
    </div>
</div>

<!-- Prompt 预览模态弹窗 -->
<div class="viewer-overlay" id="prompt-preview-overlay">
    <div class="viewer-modal">
        <div class="viewer-header">
            <h3>当前 Prompt 模板预览</h3>
            <button class="prompt-editor-close" onclick="closePromptPreview()">&times;</button>
        </div>
        <div class="viewer-body">
            <div class="viewer-pre" id="prompt-preview-content">加载中...</div>
        </div>
        <div class="viewer-footer">
            <button class="pe-btn-save" onclick="closePromptPreview(); openPromptEditor();">在编辑器中打开</button>
            <button class="pe-btn-cancel" onclick="closePromptPreview()">关闭</button>
        </div>
    </div>
</div>
```

- [ ] **Step 2: 在 app.js 末尾追加 AI Tab 工具栏 JS 逻辑**

```js
// ============================================================================
// Phase 2 UX: Prompt Lab + 数据/Prompt 查看
// ============================================================================

let currentTemplateName = '深度分析-默认';
let currentTemplateData = null;
let currentReportData = null;

// ---- 模板选择器 ----

async function loadTemplateList() {
    try {
        const resp = await fetch('/ai/prompts');
        const templates = await resp.json();
        const selector = document.getElementById('prompt-template-selector');
        if (!selector) return;
        selector.innerHTML = '';
        templates.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.name;
            opt.textContent = (t.is_default ? '⭐ ' : '') + t.name + ' (' + t.mode + ')';
            if (t.name === currentTemplateName) opt.selected = true;
            selector.appendChild(opt);
        });
    } catch (e) {
        console.error('加载模板列表失败:', e);
    }
}

async function onTemplateChange() {
    const selector = document.getElementById('prompt-template-selector');
    const name = selector.value;
    if (!name) return;
    currentTemplateName = name;
    try {
        const resp = await fetch('/ai/prompts/' + encodeURIComponent(name));
        if (resp.ok) {
            currentTemplateData = await resp.json();
            console.log('已切换模板:', name);
        }
    } catch (e) {
        console.error('加载模板失败:', e);
    }
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadTemplateList();
    // 预加载默认模板
    fetch('/ai/prompts/' + encodeURIComponent('深度分析-默认'))
        .then(r => r.json())
        .then(d => { currentTemplateData = d; })
        .catch(() => {});
});

// ---- Prompt 编辑器 ----

async function openPromptEditor(templateName) {
    const name = templateName || currentTemplateName;
    try {
        const resp = await fetch('/ai/prompts/' + encodeURIComponent(name));
        if (!resp.ok) { alert('模板加载失败'); return; }
        const t = await resp.json();

        document.getElementById('pe-name').value = t.name || '';
        document.getElementById('pe-desc').value = t.description || '';
        document.getElementById('pe-mode').value = t.mode || 'deep';
        document.getElementById('pe-role').value = t.system_role || '';
        document.getElementById('pe-harvard').value = (t.frameworks && t.frameworks.harvard) || '';
        document.getElementById('pe-crosscheck').value = (t.frameworks && t.frameworks.crosscheck) || '';
        document.getElementById('pe-lifecycle').value = (t.frameworks && t.frameworks.lifecycle) || '';
        document.getElementById('pe-warnings').value = (t.frameworks && t.frameworks.warnings) || '';
        document.getElementById('pe-output').value = t.output_format || '';

        document.getElementById('prompt-editor-overlay').style.display = 'flex';
        requestAnimationFrame(function() {
            document.getElementById('prompt-editor-overlay').classList.add('modal--visible');
        });
    } catch (e) {
        alert('打开编辑器失败: ' + e.message);
    }
}

function closePromptEditor() {
    const overlay = document.getElementById('prompt-editor-overlay');
    overlay.classList.remove('modal--visible');
    overlay.addEventListener('transitionend', function h() {
        overlay.removeEventListener('transitionend', h);
        overlay.style.display = 'none';
    });
}

async function saveTemplate() {
    const name = document.getElementById('pe-name').value.trim();
    if (!name) { alert('请输入模板名称'); return; }

    const data = {
        name: name,
        description: document.getElementById('pe-desc').value.trim(),
        mode: document.getElementById('pe-mode').value,
        system_role: document.getElementById('pe-role').value,
        frameworks: {
            harvard: document.getElementById('pe-harvard').value,
            crosscheck: document.getElementById('pe-crosscheck').value,
            lifecycle: document.getElementById('pe-lifecycle').value,
            warnings: document.getElementById('pe-warnings').value,
        },
        output_format: document.getElementById('pe-output').value,
    };

    try {
        const resp = await fetch('/ai/prompts/' + encodeURIComponent(name), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (resp.ok) {
            currentTemplateName = name;
            currentTemplateData = data;
            closePromptEditor();
            loadTemplateList();
        } else {
            const err = await resp.json();
            alert('保存失败: ' + (err.error || '未知错误'));
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

async function exportTemplate() {
    const name = document.getElementById('pe-name').value.trim();
    if (!name) { alert('请先输入模板名称'); return; }
    window.open('/ai/prompts/' + encodeURIComponent(name) + '/export', '_blank');
}

function importTemplate() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async function() {
        const file = input.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            const resp = await fetch('/ai/prompts/import', { method: 'POST', body: formData });
            if (resp.ok) {
                loadTemplateList();
                alert('模板导入成功');
            } else {
                const err = await resp.json();
                alert('导入失败: ' + (err.error || '未知错误'));
            }
        } catch (e) {
            alert('导入失败: ' + e.message);
        }
    };
    input.click();
}

async function duplicateTemplate() {
    const name = document.getElementById('pe-name').value.trim();
    const newName = prompt('新模板名称:', name + ' - 副本');
    if (!newName) return;
    try {
        const resp = await fetch('/ai/prompts/' + encodeURIComponent(name) + '/duplicate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_name: newName }),
        });
        if (resp.ok) {
            loadTemplateList();
            alert('模板已复制为: ' + newName);
        }
    } catch (e) {
        alert('复制失败: ' + e.message);
    }
}

// ---- 数据报告查看器 ----

async function openDataViewer() {
    document.getElementById('data-viewer-overlay').style.display = 'flex';
    requestAnimationFrame(function() {
        document.getElementById('data-viewer-overlay').classList.add('modal--visible');
    });

    const body = document.getElementById('data-viewer-body');
    body.innerHTML = '<p style="color:var(--text-muted);">加载中...</p>';

    try {
        const resp = await fetch('/ai/report');
        if (!resp.ok) {
            const err = await resp.json();
            body.innerHTML = '<p style="color:var(--negative);">' + (err.error || '请先获取财务数据') + '</p>';
            return;
        }
        const report = await resp.json();
        currentReportData = report;

        const snap = report.company_snapshot || {};
        const titleEl = document.getElementById('data-viewer-title');
        titleEl.textContent = '财务体检报告 — ' + (snap.name || report.stock_code || '');

        let html = '';

        // 公司快照
        html += '<div class="viewer-section"><h4>公司快照</h4>';
        html += '<div class="kv-row"><span>股价</span><span class="kv-value">' + (snap.price || 'N/A') + '</span></div>';
        html += '<div class="kv-row"><span>PE</span><span class="kv-value">' + (snap.pe || 'N/A') + '</span></div>';
        html += '<div class="kv-row"><span>PB</span><span class="kv-value">' + (snap.pb || 'N/A') + '</span></div>';
        html += '<div class="kv-row"><span>市值(亿)</span><span class="kv-value">' + (snap.market_cap_yi || 'N/A') + '</span></div>';
        html += '</div>';

        // 财务健康
        const health = report.financial_health || {};
        for (const [section, data] of Object.entries(health)) {
            if (section.startsWith('_') || !data || typeof data !== 'object') continue;
            html += '<div class="viewer-section"><h4>' + section + '</h4>';
            for (const [k, v] of Object.entries(data)) {
                html += '<div class="kv-row"><span>' + k + '</span><span class="kv-value">' + (v != null ? v : 'N/A') + '</span></div>';
            }
            html += '</div>';
        }

        // 杜邦
        const dupont = report.dupont_analysis || {};
        if (dupont.three_factor && dupont.three_factor.length > 0) {
            html += '<div class="viewer-section"><h4>杜邦分析</h4>';
            dupont.three_factor.forEach(dp => {
                html += '<div class="kv-row"><span>' + (dp.end_date || '') + '</span><span class="kv-value">ROE=' + dp.roe + '% = ' + dp.net_margin + '% x ' + dp.asset_turnover + ' x ' + dp.equity_multiplier + '</span></div>';
            });
            html += '</div>';
        }

        // 风险模型
        const risk = report.risk_models || {};
        if (Object.keys(risk).length > 0) {
            html += '<div class="viewer-section"><h4>风险模型</h4>';
            for (const [key, val] of Object.entries(risk)) {
                if (val && typeof val === 'object') {
                    html += '<div class="kv-row"><span>' + key + '</span><span class="kv-value">' + JSON.stringify(val).substring(0, 120) + '</span></div>';
                }
            }
            html += '</div>';
        }

        // 现金流
        const cf = report.cashflow_analysis || {};
        if (cf.quadrant && cf.quadrant.length > 0) {
            html += '<div class="viewer-section"><h4>现金流象限</h4>';
            cf.quadrant.forEach(q => {
                html += '<div class="kv-row"><span>' + (q.end_date || '') + '</span><span class="kv-value">' + q.quadrant_type + '</span></div>';
            });
            html += '</div>';
        }

        body.innerHTML = html || '<p style="color:var(--text-muted);">暂无数据</p>';
    } catch (e) {
        body.innerHTML = '<p style="color:var(--negative);">加载失败: ' + e.message + '</p>';
    }
}

function closeDataViewer() {
    const overlay = document.getElementById('data-viewer-overlay');
    overlay.classList.remove('modal--visible');
    overlay.addEventListener('transitionend', function h() {
        overlay.removeEventListener('transitionend', h);
        overlay.style.display = 'none';
    });
}

function exportDataReport() {
    window.open('/ai/report/export', '_blank');
}

// ---- Prompt 预览 ----

async function openPromptPreview() {
    document.getElementById('prompt-preview-overlay').style.display = 'flex';
    requestAnimationFrame(function() {
        document.getElementById('prompt-preview-overlay').classList.add('modal--visible');
    });

    const contentEl = document.getElementById('prompt-preview-content');
    contentEl.textContent = '加载中...';

    if (!currentTemplateData) {
        try {
            const resp = await fetch('/ai/prompts/' + encodeURIComponent(currentTemplateName));
            if (resp.ok) currentTemplateData = await resp.json();
        } catch (e) {}
    }

    if (currentTemplateData) {
        let preview = '【系统角色】\n' + (currentTemplateData.system_role || '(未设置)') + '\n\n';
        preview += '【分析模式】' + (currentTemplateData.mode || 'deep') + '\n\n';
        const fws = currentTemplateData.frameworks || {};
        for (const [key, content] of Object.entries(fws)) {
            if (content) preview += '--- ' + key + ' ---\n' + content + '\n\n';
        }
        preview += '【输出格式】\n' + (currentTemplateData.output_format || '(未设置)');
        contentEl.textContent = preview;
    } else {
        contentEl.textContent = '请先获取数据并选择模板';
    }
}

function closePromptPreview() {
    const overlay = document.getElementById('prompt-preview-overlay');
    overlay.classList.remove('modal--visible');
    overlay.addEventListener('transitionend', function h() {
        overlay.removeEventListener('transitionend', h);
        overlay.style.display = 'none';
    });
}

// ---- 修改 sendMessage 注入当前模板 ----

// 将 currentTemplateData 注入到消息发送中
const _origSendMessage = sendMessage;
sendMessage = function() {
    // 在发起对话前，将 currentTemplateData 缓存到 session
    if (currentTemplateData && currentTemplateName) {
        // 通过 chatWs 发送时带上 template 参数
        window._pendingTemplate = currentTemplateData;
    }
    _origSendMessage();
};

// ---- 修改 chatWs.onopen，在初始化消息中附带模板 ----
// (通过 monkey-patch WebSocket 发送逻辑)
const _origSetupChatWs = function() {
    // 在 sendMessage 内部的 WebSocket 创建后，发送初始化时附带模板名称
    // 由 orchestrator._build_prompt 中的 PromptStore 读取
};
```

- [ ] **Step 3: 修改 sendMessage 逻辑以传递模板参数**

修改 `sendMessage` 中 `chatWs.onopen` 的初始化消息，添加 `template_name`：

在 `app.js` 的 `chatWs.onopen` 回调中，找到：

```js
chatWs.send(JSON.stringify({ stock_code: stockCode }));
```

替换为：

```js
chatWs.send(JSON.stringify({
    stock_code: stockCode,
    template_name: currentTemplateName || '',
    template: currentTemplateData || null,
}));
```

- [ ] **Step 4: 提交**

```bash
git add financial_analyzer/web/templates/base.html financial_analyzer/web/static/js/app.js
git commit -m "feat: add AI tab toolbar with template selector and data/prompt modals

Template dropdown selector, edit button opens Prompt Lab editor modal,
data report viewer modal with sections, prompt preview modal. Template
data passed through WebSocket init to orchestrator.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8: 后端 — Orchestrator 接收模板参数

**Files:**
- Modify: `financial_analyzer/web/routes/ai_api.py` (conversation WebSocket init)
- Modify: `financial_analyzer/ai/orchestrator.py` (_build_prompt 方法)

- [ ] **Step 1: 修改 `/ai/conversation` WebSocket 接收模板参数**

在 `ai_conversation` 函数中，解析 `template_name` 参数并加载模板。修改初始化消息处理部分：

在 `ai_api.py` 的 `ai_conversation` 函数中，找到解析 `params` 的行，在 `stock_code` 解析后追加模板加载逻辑：

```python
# 在 params = json.loads(init_data) 之后，stock_code 解析之后，添加：
template_name = params.get("template_name", "")
template_data = params.get("template")  # 前端传过来的完整模板 dict
```

然后将模板传给 orchestrator 使用。最简单的方式是在 orchestrator 上设置当前模板：

```python
# 在创建 orchestrator 之后
if template_data:
    orchestrator._current_template = template_data
elif template_name:
    from financial_analyzer.ai.prompt_store import PromptsStore
    store = PromptsStore()
    orchestrator._current_template = store.get_template(template_name)
```

- [ ] **Step 2: 修改 orchestrator._build_prompt 使用模板**

在 `orchestrator.py` 的 `_build_prompt` 方法中，添加模板加载：

```python
def _build_prompt(self, intent: str, message: str, data: dict | None,
                  report: dict | None, signals: list | None) -> str:
    """构建提示词"""
    builder = PromptBuilder()
    company_name = report.get("company_snapshot", {}).get("name", "") if report else ""

    # 加载当前模板
    template = getattr(self, '_current_template', None)

    if intent == "quick":
        builder.with_mode("quick")
        builder.with_question(message)
        if report:
            builder.with_data(report)
        elif data:
            builder.with_data(data)
        if template:
            builder.with_template(template)
    elif intent == "deep":
        builder.with_mode("deep")
        builder.with_question(message)
        if report:
            builder.with_data(report)
        elif data:
            builder.with_data(data)
        if template:
            builder.with_template(template)
        else:
            # fallback：没有模板时使用硬编码框架
            builder.with_framework("harvard")
            builder.with_framework("crosscheck")
            builder.with_framework("lifecycle")
            builder.with_framework("warnings")
            builder.with_output_format("structured")
        if signals:
            builder.with_signals(signals)
    elif intent == "followup":
        builder.with_mode("followup")
        builder.with_question(message)
        if report:
            builder.with_data(report)
        elif data:
            builder.with_data(data)
        if template:
            builder.with_template(template)
    elif intent == "debate":
        builder.with_mode("debate")
        builder.with_question(message)
        if report:
            builder.with_data(report)
        elif data:
            builder.with_data(data)
        if template:
            builder.with_template(template)

    return builder.build()
```

- [ ] **Step 3: 验证模块导入**

```bash
python -c "
from financial_analyzer.ai.orchestrator import AnalysisOrchestrator
from financial_analyzer.ai.prompt_framework import PromptBuilder
from financial_analyzer.ai.prompt_store import PromptsStore

# 模拟模板加载 + 构建
store = PromptsStore()
template = store.get_template('深度分析-默认')
assert template is not None

builder = PromptBuilder('测试公司')
builder.with_template(template)
builder.with_mode('deep')
prompt = builder.build()
assert '哈佛分析框架' in prompt
print('Template integration OK')
"
```

Expected: "Template integration OK"

- [ ] **Step 4: 提交**

```bash
git add financial_analyzer/ai/orchestrator.py financial_analyzer/web/routes/ai_api.py
git commit -m "feat: wire template loading into orchestrator and WebSocket

/orchestrator._build_prompt loads template via PromptsStore when available.
/ai/conversation WebSocket accepts template_name/template in init message.
Fallback to hardcoded frameworks when no template selected.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 9: 前端 — 辩论 Tab 重布局

**Files:**
- Modify: `financial_analyzer/web/templates/base.html` (辩论 Tab HTML)
- Modify: `financial_analyzer/web/static/js/app.js` (辩论 JS 完全重写)

- [ ] **Step 1: 替换辩论 Tab 的 HTML**

将 `tab-debate` 中的全部内容替换为四区域布局：

```html
<!-- Tab: AI 辩论 — 三方投研辩论 -->
<div id="tab-debate" class="tab-panel">
    <div class="debate-layout" id="debate-layout">
        <!-- 控制栏 -->
        <div class="debate-control-bar">
            <button class="btn btn-accent" onclick="startDebateNew()" id="debate-start-btn">▶ 开始辩论</button>
            <span style="color:var(--text-muted);font-size:var(--text-xs);">三位分析师：价值 / 成长 / 风控</span>
            <span class="debate-status" id="debate-status"></span>
        </div>

        <!-- 三列 -->
        <div class="debate-columns" id="debate-columns">
            <div class="debate-column debate-column--value" id="debate-col-value">
                <div class="debate-column-header">📊 格雷厄姆 · 价值派</div>
                <div class="debate-column-body" id="debate-body-value"></div>
            </div>
            <div class="debate-column debate-column--growth" id="debate-col-growth">
                <div class="debate-column-header">🚀 费雪 · 成长派</div>
                <div class="debate-column-body" id="debate-body-growth"></div>
            </div>
            <div class="debate-column debate-column--risk" id="debate-col-risk">
                <div class="debate-column-header">🛡️ 塔勒布 · 风控派</div>
                <div class="debate-column-body" id="debate-body-risk"></div>
            </div>
        </div>

        <!-- 总结区 -->
        <div class="debate-consensus-area" id="debate-consensus-area">
            <div class="consensus-header">📋 综合共识与情景概率</div>
            <div class="consensus-body" id="debate-consensus-body"></div>
        </div>

        <!-- 追问栏 -->
        <div class="debate-followup-bar">
            <span style="color:var(--text-muted);font-size:var(--text-xs);white-space:nowrap;">💬 追问三方：</span>
            <input type="text" id="debate-followup-input"
                   placeholder="输入追问，如：如果行业增速放缓到5%，你们的结论会如何调整？"
                   onkeydown="if(event.key==='Enter'){event.preventDefault();sendDebateFollowup();}">
            <button class="btn" onclick="sendDebateFollowup()" style="padding:6px 14px;font-size:var(--text-xs);">发送追问</button>
            <button class="chat-stop-btn" onclick="stopDebate()" style="padding:6px 12px;font-size:var(--text-xs);">停止</button>
            <span style="flex:1;"></span>
            <button class="btn-export" onclick="exportDebate('md')">导出 Markdown</button>
            <button class="btn-export" onclick="exportDebate('html')">导出 HTML</button>
        </div>
    </div>

    <!-- 空状态占位 -->
    <div id="debate-empty-state" style="display:flex;align-items:center;justify-content:center;flex:1;min-height:200px;">
        <div class="chat-empty">
            <div style="font-size:32px;opacity:0.3;margin-bottom:8px;">⚔️</div>
            <div>三方投研辩论</div>
            <div class="hint">格雷厄姆价值派 × 费雪成长派 × 塔勒布风控派</div>
        </div>
    </div>
</div>
```

- [ ] **Step 2: 重写辩论 JS 客户端**

替换 `app.js` 中从 `// AI 辩论 WebSocket 客户端` 开始的全部辩论代码（保留 `ANALYST_META` 常量，替换其后的所有辩论函数）：

```js
// ============================================================================
// AI 辩论 WebSocket 客户端 — 四区域布局版
// ============================================================================

const ANALYST_META = {
    'value':    { name: '格雷厄姆式价值分析师', icon: '📊', color: '#3B82F6' },
    'growth':   { name: '费雪式成长分析师', icon: '🚀', color: '#14B8A6' },
    'risk':     { name: '塔勒布式风控师', icon: '🛡️', color: '#F59E0B' },
    'consensus': { name: '综合共识', icon: '📋', color: '#A78BFA' },
};

const ROUND_NAMES = {
    'round1_start': '第1轮：独立陈述',
    'round2_start': '第2轮：交叉质询',
    'round3_start': '第3轮：共识与情景概率',
};

const BODY_IDS = {
    'value': 'debate-body-value',
    'growth': 'debate-body-growth',
    'risk': 'debate-body-risk',
};

let debateWs = null;
let debateRunning = false;
let debateData = {
    round1: {},
    round2: {},
    round3: {},
    consensus: '',
    followups: [],
};
let currentRoundKey = '';
let currentFollowupIndex = -1;

function startDebateNew() {
    const stockCode = document.querySelector('input[name="stock_code"]')?.value || '';
    if (!stockCode) {
        alert('请先输入股票代码并获取数据');
        return;
    }

    if (debateWs && debateWs.readyState === WebSocket.OPEN) {
        debateWs.close();
    }

    // 显示布局，隐藏空状态
    document.getElementById('debate-layout').style.display = 'flex';
    const emptyState = document.getElementById('debate-empty-state');
    if (emptyState) emptyState.style.display = 'none';

    // 清空三列
    ['value', 'growth', 'risk'].forEach(role => {
        document.getElementById(BODY_IDS[role]).textContent = '';
    });
    document.getElementById('debate-consensus-body').textContent = '';

    // 重置辩论数据
    debateData = { round1: {}, round2: {}, round3: {}, consensus: '', followups: [] };
    currentRoundKey = '';
    currentFollowupIndex = -1;

    const statusEl = document.getElementById('debate-status');
    statusEl.textContent = '连接中...';

    const startBtn = document.getElementById('debate-start-btn');
    startBtn.disabled = true;
    startBtn.textContent = '辩论中...';
    debateRunning = true;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = protocol + '//' + location.host + '/ai/debate';

    try {
        debateWs = new WebSocket(wsUrl);

        debateWs.onopen = function() {
            statusEl.textContent = '已连接，准备数据...';
            debateWs.send(JSON.stringify({ stock_code: stockCode }));
        };

        debateWs.onmessage = function(event) {
            const msg = JSON.parse(event.data);

            if (msg.type === 'status') {
                statusEl.textContent = msg.content;
            }
            else if (msg.type === 'meta') {
                if (msg.content in ROUND_NAMES) {
                    currentRoundKey = msg.content.replace('_start', '');
                    statusEl.textContent = ROUND_NAMES[msg.content];
                }
                else if (msg.content.startsWith('analyst_') && msg.content.endsWith('_start')) {
                    const roleKey = msg.content.replace('analyst_', '').replace('_start', '');
                    // 在新一轮中追加标签
                    if (roleKey === 'value' || roleKey === 'growth' || roleKey === 'risk') {
                        const body = document.getElementById(BODY_IDS[roleKey]);
                        const tag = document.createElement('span');
                        tag.className = 'debate-round-tag';
                        tag.textContent = ROUND_NAMES[currentRoundKey + '_start'] || currentRoundKey;
                        body.appendChild(tag);
                        body.appendChild(document.createTextNode('\n'));
                        body.scrollTop = body.scrollHeight;
                    }
                }
                else if (msg.content === 'debate_complete') {
                    statusEl.textContent = '辩论完成';
                    startBtn.disabled = false;
                    startBtn.textContent = '重新辩论';
                    debateRunning = false;
                }
                else if (msg.content.startsWith('error:')) {
                    statusEl.textContent = '出错: ' + msg.content.substring(6);
                    startBtn.disabled = false;
                    startBtn.textContent = '重试';
                    debateRunning = false;
                }
            }
            else if (msg.type === 'chunk') {
                const roleKey = msg.role;
                if (roleKey === 'consensus') {
                    const body = document.getElementById('debate-consensus-body');
                    body.textContent += msg.content;
                    debateData.consensus += msg.content;
                    body.scrollTop = body.scrollHeight;
                } else if (BODY_IDS[roleKey]) {
                    const body = document.getElementById(BODY_IDS[roleKey]);
                    body.textContent += msg.content;
                    body.scrollTop = body.scrollHeight;

                    // 收集到 debateData
                    const roundMap = { 'round1': 'round1', 'round2': 'round2', 'round3': 'round3' };
                    const rk = roundMap[currentRoundKey] || currentRoundKey;
                    if (rk && (rk === 'round1' || rk === 'round2' || rk === 'round3')) {
                        debateData[rk][roleKey] = (debateData[rk][roleKey] || '') + msg.content;
                    }
                }
            }
            else if (msg.type === 'done') {
                statusEl.textContent = '辩论结束';
                startBtn.disabled = false;
                startBtn.textContent = '重新辩论';
                debateRunning = false;
            }
            else if (msg.type === 'error') {
                statusEl.textContent = '出错';
                startBtn.disabled = false;
                startBtn.textContent = '重试';
                debateRunning = false;
            }
        };

        debateWs.onerror = function() {
            statusEl.textContent = '连接失败';
            startBtn.disabled = false;
            startBtn.textContent = '重试';
            debateRunning = false;
        };

        debateWs.onclose = function() {
            if (debateRunning) {
                statusEl.textContent = '连接断开';
                startBtn.disabled = false;
                startBtn.textContent = '重试';
                debateRunning = false;
            }
        };
    } catch (e) {
        statusEl.textContent = '连接失败: ' + e.message;
        startBtn.disabled = false;
        startBtn.textContent = '重试';
        debateRunning = false;
    }
}

function sendDebateFollowup() {
    const input = document.getElementById('debate-followup-input');
    const question = input.value.trim();
    if (!question) return;
    if (!debateWs || debateWs.readyState !== WebSocket.OPEN) {
        alert('辩论未连接或已结束');
        return;
    }

    input.value = '';
    currentFollowupIndex++;
    const fuEntry = { question: question, value: '', growth: '', risk: '' };
    debateData.followups.push(fuEntry);

    ['value', 'growth', 'risk'].forEach(role => {
        const body = document.getElementById(BODY_IDS[role]);
        const tag = document.createElement('span');
        tag.className = 'debate-round-tag';
        tag.textContent = '追问: ' + question.substring(0, 40) + (question.length > 40 ? '...' : '');
        body.appendChild(tag);
        body.appendChild(document.createTextNode('\n'));
        body.scrollTop = body.scrollHeight;
    });

    // 发送追问到服务器
    debateWs.send(JSON.stringify({ type: 'followup', content: question }));
}

function stopDebate() {
    if (debateWs && debateWs.readyState === WebSocket.OPEN) {
        debateWs.send(JSON.stringify({ type: 'stop' }));
        debateWs.close();
    }
    debateRunning = false;
    document.getElementById('debate-status').textContent = '已停止';
    const startBtn = document.getElementById('debate-start-btn');
    startBtn.disabled = false;
    startBtn.textContent = '重新辩论';
}

async function exportDebate(fmt) {
    const stockCode = document.querySelector('input[name="stock_code"]')?.value || '';
    try {
        const resp = await fetch('/ai/debate/export/' + fmt, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                debate_data: debateData,
                stock_code: stockCode,
                company_name: '',  // 前端可能没有此信息
            }),
        });
        if (resp.ok) {
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const ext = fmt === 'md' ? 'md' : 'html';
            a.download = 'debate_' + (stockCode || 'result') + '.' + ext;
            a.click();
            URL.revokeObjectURL(url);
        } else {
            const err = await resp.json();
            alert('导出失败: ' + (err.error || '未知错误'));
        }
    } catch (e) {
        alert('导出失败: ' + e.message);
    }
}
```

- [ ] **Step 3: 验证 HTML 无语法问题**

```bash
python -c "
from financial_analyzer.web.main import create_app
app = create_app()
print('App created successfully with new debate tab layout')
"
```

Expected: "App created successfully with new debate tab layout"

- [ ] **Step 4: 提交**

```bash
git add financial_analyzer/web/templates/base.html financial_analyzer/web/static/js/app.js
git commit -m "feat: redesign debate tab with 4-area layout and export

3-column independent scrolling areas for value/growth/risk analysts,
consensus summary area, follow-up input bar, and Markdown/HTML export
buttons. Debate WebSocket client rewritten for multi-column routing.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 10: 辩论 WebSocket 支持追问

**Files:**
- Modify: `financial_analyzer/web/routes/ai_api.py` (`/ai/debate` WebSocket)

- [ ] **Step 1: 修改 `/ai/debate` 支持辩论后的追问消息**

当前辩论端点辩论完成后立即关闭连接。需要改为保持连接，接收追问消息，调用 `engine.send_followup()`。

在 `ai_api.py` 的 `ai_debate` 函数中，辩论完成后的逻辑改为继续循环接收消息。找到辩论完成的 while 循环，在 `QUEUE_DONE` 处理后不 break，而是继续等待追问：

修改 `ai_debate` 中主循环之后的部分。辩论完成后进入追问模式：

```python
# 在 ai_debate 函数中，辩论完成后的 while True 循环内部，QUEUE_DONE 处理后：

while True:
    msg = await loop.run_in_executor(None, msg_queue.get)
    if msg is QUEUE_DONE:
        await websocket.send_text(json.dumps({"type": "done", "content": ""}))
        break  # 辩论主体结束

    role, content, done = msg
    # ... 现有 chunk/meta 处理 ...

# 辩论结束后进入追问模式
await websocket.send_text(json.dumps({"type": "meta", "content": "debate_complete"}))

while True:
    try:
        followup_msg = await asyncio.wait_for(websocket.receive_text(), timeout=300)
    except asyncio.TimeoutError:
        break

    fu_data = json.loads(followup_msg)
    if fu_data.get("type") == "followup":
        question = fu_data.get("content", "")
        if not question:
            continue

        # 使用 debate engine 的 followup
        fu_queue: queue.Queue = queue.Queue()
        FU_DONE = object()

        def fu_callback(role: str, chunk: str, done: bool):
            fu_queue.put((role, chunk, done))

        def fu_on_complete(state):
            fu_queue.put(FU_DONE)

        engine.send_followup(
            question=question,
            callback=fu_callback,
            on_complete=fu_on_complete,
        )

        # 流式推送追问结果
        while True:
            item = await loop.run_in_executor(None, fu_queue.get)
            if item is FU_DONE:
                await websocket.send_text(json.dumps({"type": "done", "content": ""}))
                break
            role, content, done = item
            if role == "_meta":
                await websocket.send_text(json.dumps({"type": "meta", "content": content}))
            else:
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "role": role,
                    "content": content,
                    "done": done,
                }))

    elif fu_data.get("type") == "stop":
        break
```

- [ ] **Step 2: 提交**

```bash
git add financial_analyzer/web/routes/ai_api.py
git commit -m "feat: add follow-up support to /ai/debate WebSocket

After debate completes, connection stays open for follow-up messages.
Follow-up questions are routed through debate_engine.send_followup()
and streamed back to the three columns independently.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 11: 集成验证

**Files:** (none new — validation only)

- [ ] **Step 1: 运行全部测试确保无回归**

```bash
cd "C:/Users/LK/Desktop/FA/10.6"
python -m pytest tests/ -v --ignore=tests/test_adapter.py
```

Expected: all existing and new tests pass.

- [ ] **Step 2: 验证模块导入链路**

```bash
python -c "
# 新模块
from financial_analyzer.ai.prompt_store import PromptsStore
store = PromptsStore()
templates = store.list_templates()
print(f'模板数: {len(templates)}')
for t in templates:
    print(f'  - {t[\"name\"]} ({t[\"mode\"]})')

# 模板 + PromptBuilder
from financial_analyzer.ai.prompt_framework import PromptBuilder
template = store.get_template('深度分析-默认')
builder = PromptBuilder('测试公司')
builder.with_template(template)
builder.with_mode('deep')
prompt = builder.build()
print(f'\\n深度分析 Prompt 长度: {len(prompt)} chars')
assert '哈佛分析框架' in prompt
assert '测试公司' in prompt
print('PromptBuilder + template OK')

# 不传模板时向后兼容
builder2 = PromptBuilder('测试公司')
builder2.with_mode('deep')
builder2.with_framework('harvard')
prompt2 = builder2.build()
assert '哈佛分析框架' in prompt2
print('Backward compatibility OK')

# Web 模块
from financial_analyzer.web.main import create_app
app = create_app()
print('\\nApp created OK')
print('All imports successful')
"
```

Expected: all assertions pass, "All imports successful"

- [ ] **Step 3: 端到端模板 CRUD 验证**

```bash
python -c "
from financial_analyzer.ai.prompt_store import PromptsStore
import json

store = PromptsStore()

# 创建
store.save_template('E2E测试模板', {
    'name': 'E2E测试模板',
    'description': '端到端测试',
    'mode': 'deep',
    'system_role': '测试角色',
    'frameworks': {'harvard': '哈佛框架测试', 'crosscheck': '联动测试'},
    'output_format': '测试格式',
})
t = store.get_template('E2E测试模板')
assert t is not None
assert t['mode'] == 'deep'
print('Create OK')

# 复制
assert store.duplicate_template('E2E测试模板', 'E2E副本')
t2 = store.get_template('E2E副本')
assert t2 is not None
print('Duplicate OK')

# 导出/导入
json_str = store.export_template('E2E测试模板')
assert json_str is not None
store.delete_template('E2E测试模板')
assert store.get_template('E2E测试模板') is None
assert store.import_template(json_str)
assert store.get_template('E2E测试模板') is not None
print('Export/Import OK')

# 清理
store.delete_template('E2E测试模板')
store.delete_template('E2E副本')
print('Cleanup OK')
print('E2E CRUD all passed')
"
```

Expected: "E2E CRUD all passed"

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "verify: integration tests pass for AI UX optimization

PromptStore CRUD, PromptBuilder template loading, backward compatibility,
and Web app creation all verified. All unit tests passing.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

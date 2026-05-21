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

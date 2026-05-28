"""策略模板管理器测试"""
import json
import pytest
from pathlib import Path

from financial_analyzer.quant.engine.strategy_template import (
    StrategyTemplate,
    TemplateManager,
    TEMPLATE_DIR,
)


@pytest.fixture
def sample_template_data():
    return {
        "name": "测试模板",
        "description": "用于测试",
        "factors": [
            {"name": "pe", "weight": 0.5, "direction": -1},
            {"name": "roe", "weight": 0.5, "direction": 1},
        ],
        "position_sizer": "equal",
        "risk": {"max_drawdown_pct": 15, "stop_loss_pct": -10},
        "top_n": 20,
    }


@pytest.fixture
def sample_template(sample_template_data):
    return StrategyTemplate.from_dict(sample_template_data)


@pytest.fixture
def tmp_template_dir(tmp_path):
    return tmp_path / "templates"


class TestStrategyTemplate:

    def test_from_dict(self, sample_template_data):
        t = StrategyTemplate.from_dict(sample_template_data)
        assert t.name == "测试模板"
        assert t.description == "用于测试"
        assert len(t.factors) == 2
        assert t.position_sizer == "equal"
        assert t.top_n == 20

    def test_from_json(self, tmp_path, sample_template_data):
        path = tmp_path / "test.json"
        path.write_text(json.dumps(sample_template_data, ensure_ascii=False), encoding="utf-8")
        t = StrategyTemplate.from_json(str(path))
        assert t.name == "测试模板"
        assert len(t.factors) == 2

    def test_to_dict(self, sample_template, sample_template_data):
        d = sample_template.to_dict()
        assert d == sample_template_data

    def test_to_json_roundtrip(self, tmp_path, sample_template):
        path = tmp_path / "out.json"
        sample_template.to_json(str(path))
        loaded = StrategyTemplate.from_json(str(path))
        assert loaded.name == sample_template.name
        assert loaded.factors == sample_template.factors

    def test_to_factor_configs(self, sample_template):
        configs = sample_template.to_factor_configs()
        assert len(configs) == 2
        assert configs[0].name == "pe"
        assert configs[0].direction == "negative"
        assert configs[0].weight == 0.5
        assert configs[1].name == "roe"
        assert configs[1].direction == "positive"

    def test_to_factor_configs_default_direction(self):
        t = StrategyTemplate.from_dict({
            "name": "t",
            "factors": [{"name": "x", "weight": 1.0}],
        })
        configs = t.to_factor_configs()
        assert configs[0].direction == "positive"


class TestTemplateManager:

    def test_list_templates_builtin(self):
        mgr = TemplateManager()
        templates = mgr.list_templates()
        assert len(templates) >= 5
        names = {t['file'] for t in templates}
        assert "value_investing" in names
        assert "growth_momentum" in names
        assert "quality_dividend" in names
        assert "balanced_multi_factor" in names
        assert "low_volatility" in names

    def test_list_templates_has_required_fields(self):
        mgr = TemplateManager()
        templates = mgr.list_templates()
        for t in templates:
            assert 'file' in t
            assert 'name' in t
            assert 'factors' in t
            assert 'top_n' in t

    def test_load_template(self):
        mgr = TemplateManager()
        t = mgr.load_template("value_investing")
        assert t.name == "价值投资"
        assert len(t.factors) == 4
        assert t.top_n == 20

    def test_load_template_not_found(self):
        mgr = TemplateManager()
        with pytest.raises(FileNotFoundError):
            mgr.load_template("nonexistent_template")

    def test_save_and_load(self, tmp_path, sample_template):
        mgr = TemplateManager(template_dir=tmp_path)
        mgr.save_template(sample_template, "saved.json")
        loaded = mgr.load_template("saved")
        assert loaded.name == "测试模板"

    def test_clone_template(self, tmp_path):
        src_dir = TEMPLATE_DIR
        mgr = TemplateManager(template_dir=tmp_path)

        # Copy a source template to tmp dir for cloning
        import shutil
        src_file = src_dir / "value_investing.json"
        shutil.copy(src_file, tmp_path / "value_investing.json")

        cloned = mgr.clone_template("value_investing", "my_value", {"top_n": 10})
        assert cloned.name == "my_value"
        assert cloned.top_n == 10
        assert len(cloned.factors) == 4

        # Verify it was saved
        loaded = mgr.load_template("my_value")
        assert loaded.name == "my_value"

    def test_clone_template_not_found(self, tmp_path):
        mgr = TemplateManager(template_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.clone_template("nonexistent", "new_name")

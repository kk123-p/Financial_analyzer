"""策略模板管理器"""
import json
import logging
from pathlib import Path
from typing import Optional
from ..models import FactorConfig

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class StrategyTemplate:
    """策略模板"""

    def __init__(self, name, description, factors, position_sizer, risk, top_n=30):
        self.name = name
        self.description = description
        self.factors = factors  # list of {name, weight, direction}
        self.position_sizer = position_sizer
        self.risk = risk
        self.top_n = top_n

    @classmethod
    def from_json(cls, path: str) -> 'StrategyTemplate':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            factors=data.get('factors', []),
            position_sizer=data.get('position_sizer', 'equal'),
            risk=data.get('risk', {}),
            top_n=data.get('top_n', 30),
        )

    @classmethod
    def from_dict(cls, data: dict) -> 'StrategyTemplate':
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            factors=data.get('factors', []),
            position_sizer=data.get('position_sizer', 'equal'),
            risk=data.get('risk', {}),
            top_n=data.get('top_n', 30),
        )

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'factors': self.factors,
            'position_sizer': self.position_sizer,
            'risk': self.risk,
            'top_n': self.top_n,
        }

    def to_json(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def to_factor_configs(self) -> list[FactorConfig]:
        """转换为引擎可用的 FactorConfig 列表"""
        return [
            FactorConfig(
                name=f['name'],
                label=f['name'],
                category='',
                direction="negative" if f.get('direction', 1) < 0 else "positive",
                weight=f.get('weight', 1.0),
            )
            for f in self.factors
        ]


class TemplateManager:
    """策略模板管理器"""

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or TEMPLATE_DIR

    def list_templates(self) -> list[dict]:
        """列出所有可用模板"""
        templates = []
        for p in sorted(self.template_dir.glob("*.json")):
            try:
                t = StrategyTemplate.from_json(str(p))
                templates.append({
                    'file': p.stem,
                    'name': t.name,
                    'description': t.description,
                    'factors': t.factors,
                    'position_sizer': t.position_sizer,
                    'risk': t.risk,
                    'top_n': t.top_n,
                })
            except Exception as e:
                logger.warning(f"加载模板 {p} 失败: {e}")
        return templates

    def load_template(self, name: str) -> StrategyTemplate:
        """按文件名加载模板"""
        path = self.template_dir / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"模板不存在: {name}")
        return StrategyTemplate.from_json(str(path))

    def save_template(self, template: StrategyTemplate, filename: Optional[str] = None):
        """保存模板"""
        fname = filename or f"{template.name}.json"
        path = self.template_dir / fname
        template.to_json(str(path))
        logger.info(f"模板已保存: {path}")

    def clone_template(self, source_name: str, new_name: str, overrides: Optional[dict] = None) -> StrategyTemplate:
        """克隆模板并应用覆盖"""
        source = self.load_template(source_name)
        data = source.to_dict()
        data['name'] = new_name
        if overrides:
            data.update(overrides)
        cloned = StrategyTemplate.from_dict(data)
        self.save_template(cloned, f"{new_name}.json")
        return cloned

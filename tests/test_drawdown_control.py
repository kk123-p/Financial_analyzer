"""回撤控制模块测试"""
import pytest
from financial_analyzer.quant.risk.drawdown_control import DrawdownController


class TestDrawdownController:
    def test_below_threshold_returns_full(self):
        dc = DrawdownController(max_drawdown_pct=15.0, step_pct=5.0, reduce_ratio=0.25)
        assert dc.compute_position_scale(0.0) == 1.0
        assert dc.compute_position_scale(10.0) == 1.0
        assert dc.compute_position_scale(14.9) == 1.0

    def test_at_threshold_starts_reducing(self):
        dc = DrawdownController(max_drawdown_pct=15.0, step_pct=5.0, reduce_ratio=0.25)
        # 15% drawdown -> steps = int(0/5) + 1 = 1 -> scale = 1.0 - 0.25 = 0.75
        assert dc.compute_position_scale(15.0) == 0.75

    def test_one_step_above(self):
        dc = DrawdownController(max_drawdown_pct=15.0, step_pct=5.0, reduce_ratio=0.25)
        # 19% -> excess=4 -> steps=1 -> scale=0.75
        assert dc.compute_position_scale(19.0) == 0.75

    def test_two_steps(self):
        dc = DrawdownController(max_drawdown_pct=15.0, step_pct=5.0, reduce_ratio=0.25)
        # 20% -> excess=5 -> steps=2 -> scale=0.5
        assert dc.compute_position_scale(20.0) == 0.5

    def test_three_steps(self):
        dc = DrawdownController(max_drawdown_pct=15.0, step_pct=5.0, reduce_ratio=0.25)
        # 25% -> excess=10 -> steps=3 -> scale=0.25
        assert dc.compute_position_scale(25.0) == 0.25

    def test_four_steps_zero(self):
        dc = DrawdownController(max_drawdown_pct=15.0, step_pct=5.0, reduce_ratio=0.25)
        # 30% -> excess=15 -> steps=4 -> scale=0.0
        assert dc.compute_position_scale(30.0) == 0.0

    def test_beyond_zero_stays_zero(self):
        dc = DrawdownController(max_drawdown_pct=15.0, step_pct=5.0, reduce_ratio=0.25)
        assert dc.compute_position_scale(50.0) == 0.0

    def test_custom_params(self):
        dc = DrawdownController(max_drawdown_pct=10.0, step_pct=2.0, reduce_ratio=0.5)
        # 10% -> steps=1 -> scale=0.5
        assert dc.compute_position_scale(10.0) == 0.5
        # 12% -> steps=2 -> scale=0.0
        assert dc.compute_position_scale(12.0) == 0.0

    def test_aggressive_reduce(self):
        dc = DrawdownController(max_drawdown_pct=10.0, step_pct=5.0, reduce_ratio=0.5)
        # 10% -> steps=1 -> scale=0.5
        assert dc.compute_position_scale(10.0) == 0.5
        # 15% -> steps=2 -> scale=0.0
        assert dc.compute_position_scale(15.0) == 0.0

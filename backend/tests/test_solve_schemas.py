"""
solve_agent/schemas.py 单元测试

覆盖模型：
- SolveResult
- SolveBatchResult
"""

import pytest
from pydantic import ValidationError
from agents.solve.schemas import SolveResult, SolveBatchResult


# ═══════════════════════════════════════════════════════════
# SolveResult
# ═══════════════════════════════════════════════════════════


class TestSolveResult:
    """单道题解题结果"""

    def test_minimal(self):
        r = SolveResult(question_id="1", answer="B", reasoning="排除法")
        assert r.question_id == "1"
        assert r.answer == "B"
        assert r.confidence == 1.0  # 默认值

    def test_custom_confidence(self):
        r = SolveResult(question_id="2", answer="17", reasoning="计算", confidence=0.8)
        assert r.confidence == 0.8

    def test_missing_answer(self):
        with pytest.raises(ValidationError):
            SolveResult(question_id="1", reasoning="思路")

    def test_missing_reasoning(self):
        with pytest.raises(ValidationError):
            SolveResult(question_id="1", answer="A")


# ═══════════════════════════════════════════════════════════
# SolveBatchResult
# ═══════════════════════════════════════════════════════════


class TestSolveBatchResult:
    """批量解题结果"""

    def test_empty(self):
        r = SolveBatchResult(results=[])
        assert r.results == []

    def test_with_results(self):
        r = SolveBatchResult(results=[
            {"question_id": "1", "answer": "A", "reasoning": "显然"},
            {"question_id": "2", "answer": "3", "reasoning": "计算"},
        ])
        assert len(r.results) == 2
        assert r.results[0].answer == "A"

    def test_model_dump(self):
        r = SolveBatchResult(results=[
            {"question_id": "1", "answer": "B", "reasoning": "排除"},
        ])
        d = r.model_dump()
        assert len(d["results"]) == 1
        assert d["results"][0]["confidence"] == 1.0

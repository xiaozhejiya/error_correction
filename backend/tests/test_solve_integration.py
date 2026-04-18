"""
solve_agent 集成测试 — 调用真实 LLM API 验证解题能力

需要配置对应的 API Key 环境变量（OPENAI_API_KEY 或 ANTHROPIC_API_KEY）。

用法:
    cd backend
    python -m pytest tests/test_solve_integration.py -v -s
    python -m pytest tests/test_solve_integration.py -v -s --model-provider anthropic
"""

import os
import pytest
from dotenv import load_dotenv
from benchmark.metrics import compare_answers

load_dotenv()

skip_no_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"),
    reason="未配置 LLM API Key（OPENAI_API_KEY 或 ANTHROPIC_API_KEY）",
)


# ── 共享一次 API 调用 ──────────────────────────────────────

SAMPLE_QUESTIONS = [
    {
        "question_id": "choice_1",
        "question_type": "选择题",
        "content_blocks": [{"block_type": "text", "content": "已知集合A={1,2,3}, B={2,3,4}, 则A∩B="}],
        "options": ["A. {1,2}", "B. {2,3}", "C. {3,4}", "D. {1,2,3,4}"],
    },
    {
        "question_id": "fill_1",
        "question_type": "填空题",
        "content_blocks": [{"block_type": "text", "content": "计算: 2^3 + 3^2 = ______"}],
        "options": None,
    },
    {
        "question_id": "judge_1",
        "question_type": "判断题",
        "content_blocks": [{"block_type": "text", "content": "π是有理数。"}],
        "options": None,
    },
]

EXPECTED_ANSWERS = {
    "choice_1": "B",
    "fill_1": "17",
    "judge_1": "错误",
}


@pytest.fixture(scope="session")
def solve_results(model_provider):
    """session 级 fixture：只调用一次 API，所有测试共享结果"""
    from agents.solve import invoke_solve
    return invoke_solve(SAMPLE_QUESTIONS, provider=model_provider)


# ── 测试用例 ──────────────────────────────────────────────


@skip_no_api_key
class TestSolveIntegration:
    """解题智能体集成测试"""

    def test_returns_all_answers(self, solve_results):
        """应返回与输入题目数量相同的答案"""
        assert len(solve_results.results) == len(SAMPLE_QUESTIONS)

    def test_question_ids_match(self, solve_results):
        """返回的 question_id 应与输入一致"""
        returned_ids = {r.question_id for r in solve_results.results}
        expected_ids = {q["question_id"] for q in SAMPLE_QUESTIONS}
        assert returned_ids == expected_ids

    def test_choice_answer_correct(self, solve_results):
        """选择题答案正确"""
        answer_map = {r.question_id: r for r in solve_results.results}
        r = answer_map["choice_1"]
        assert compare_answers(r.answer, EXPECTED_ANSWERS["choice_1"])

    def test_fill_answer_correct(self, solve_results):
        """填空题答案正确"""
        answer_map = {r.question_id: r for r in solve_results.results}
        r = answer_map["fill_1"]
        assert compare_answers(r.answer, EXPECTED_ANSWERS["fill_1"])

    def test_judge_answer_correct(self, solve_results):
        """判断题答案正确"""
        answer_map = {r.question_id: r for r in solve_results.results}
        r = answer_map["judge_1"]
        assert compare_answers(r.answer, EXPECTED_ANSWERS["judge_1"])

    def test_has_reasoning(self, solve_results):
        """每道题应包含非空的推理过程"""
        for r in solve_results.results:
            assert r.reasoning.strip(), f"{r.question_id} 缺少推理过程"

    def test_confidence_in_range(self, solve_results):
        """置信度应在 0-1 范围内"""
        for r in solve_results.results:
            assert 0.0 <= r.confidence <= 1.0, f"{r.question_id} confidence={r.confidence}"

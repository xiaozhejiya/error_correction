"""
benchmark/metrics.py 单元测试

覆盖函数：
- normalize_answer
- compare_answers
- compute_accuracy
"""

import pytest
from benchmark.metrics import normalize_answer, compare_answers, compute_accuracy


# ═══════════════════════════════════════════════════════════
# normalize_answer
# ═══════════════════════════════════════════════════════════


class TestNormalizeAnswer:
    """答案标准化"""

    def test_strip_whitespace(self):
        assert normalize_answer("  hello  ") == "hello"

    def test_single_letter_uppercase(self):
        assert normalize_answer("a") == "A"

    def test_single_letter_already_upper(self):
        assert normalize_answer("B") == "B"

    def test_multi_letter_sorted(self):
        assert normalize_answer("dca") == "ACD"

    def test_multi_letter_already_sorted(self):
        assert normalize_answer("ACD") == "ACD"

    # 判断题标准化
    def test_true_variants(self):
        for v in ("对", "是", "正确", "√", "True", "true"):
            assert normalize_answer(v) == "正确", f"'{v}' should normalize to '正确'"

    def test_false_variants(self):
        for v in ("错", "否", "错误", "×", "False", "false"):
            assert normalize_answer(v) == "错误", f"'{v}' should normalize to '错误'"

    # 非特殊格式原样返回
    def test_plain_text_unchanged(self):
        assert normalize_answer("$\\frac{1}{2}$") == "$\\frac{1}{2}$"

    def test_numeric_string(self):
        assert normalize_answer("17") == "17"

    def test_empty_string(self):
        assert normalize_answer("") == ""


# ═══════════════════════════════════════════════════════════
# compare_answers
# ═══════════════════════════════════════════════════════════


class TestCompareAnswers:
    """答案比较"""

    def test_same_letter(self):
        assert compare_answers("A", "A") is True

    def test_case_insensitive(self):
        assert compare_answers("a", "A") is True

    def test_different_letter(self):
        assert compare_answers("A", "B") is False

    def test_multi_choice_order_independent(self):
        assert compare_answers("BDA", "ABD") is True

    def test_judgment_cross_format(self):
        assert compare_answers("对", "正确") is True
        assert compare_answers("×", "错误") is True
        assert compare_answers("True", "正确") is True

    def test_judgment_mismatch(self):
        assert compare_answers("对", "错误") is False

    def test_exact_text_match(self):
        assert compare_answers("17", "17") is True

    def test_exact_text_mismatch(self):
        assert compare_answers("17", "18") is False

    def test_whitespace_tolerance(self):
        assert compare_answers("  B  ", "B") is True


# ═══════════════════════════════════════════════════════════
# compute_accuracy
# ═══════════════════════════════════════════════════════════


class TestComputeAccuracy:
    """正确率计算"""

    def test_empty_results(self):
        report = compute_accuracy([])
        assert report["total"] == 0
        assert report["correct"] == 0
        assert report["overall_accuracy"] == 0.0
        assert report["by_type"] == {}

    def test_all_correct(self):
        results = [
            {"question_id": "1", "question_type": "选择题", "correct": True},
            {"question_id": "2", "question_type": "选择题", "correct": True},
        ]
        report = compute_accuracy(results)
        assert report["overall_accuracy"] == 1.0
        assert report["correct"] == 2

    def test_all_wrong(self):
        results = [
            {"question_id": "1", "question_type": "填空题", "correct": False},
        ]
        report = compute_accuracy(results)
        assert report["overall_accuracy"] == 0.0

    def test_mixed_results(self):
        results = [
            {"question_id": "1", "question_type": "选择题", "correct": True},
            {"question_id": "2", "question_type": "选择题", "correct": False},
            {"question_id": "3", "question_type": "填空题", "correct": True},
        ]
        report = compute_accuracy(results)
        assert report["total"] == 3
        assert report["correct"] == 2
        assert abs(report["overall_accuracy"] - 2 / 3) < 0.001

    def test_by_type_breakdown(self):
        results = [
            {"question_id": "1", "question_type": "选择题", "correct": True},
            {"question_id": "2", "question_type": "选择题", "correct": False},
            {"question_id": "3", "question_type": "填空题", "correct": True},
            {"question_id": "4", "question_type": "判断题", "correct": False},
        ]
        report = compute_accuracy(results)
        assert report["by_type"]["选择题"]["total"] == 2
        assert report["by_type"]["选择题"]["correct"] == 1
        assert report["by_type"]["选择题"]["accuracy"] == 0.5
        assert report["by_type"]["填空题"]["total"] == 1
        assert report["by_type"]["填空题"]["accuracy"] == 1.0
        assert report["by_type"]["判断题"]["accuracy"] == 0.0

    def test_unknown_type_fallback(self):
        results = [
            {"question_id": "1", "correct": True},
        ]
        report = compute_accuracy(results)
        assert "未知" in report["by_type"]

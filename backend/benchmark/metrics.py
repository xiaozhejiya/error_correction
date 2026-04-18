"""
评测指标计算
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def normalize_answer(answer: str) -> str:
    """标准化答案，用于对比

    - 去除首尾空白
    - 选择题：提取大写字母
    - 判断题：统一为"正确"/"错误"
    """
    answer = answer.strip()

    # 选择题：提取字母选项（如 "A" "AB" "ACD"）
    if re.fullmatch(r"[A-Da-d]+", answer):
        return "".join(sorted(answer.upper()))

    # 判断题
    if answer in ("对", "是", "正确", "√", "True", "true"):
        return "正确"
    if answer in ("错", "否", "错误", "×", "False", "false"):
        return "错误"

    return answer


def compare_answers(predicted: str, target: str) -> bool:
    """比较预测答案与标准答案是否一致"""
    return normalize_answer(predicted) == normalize_answer(target)


def compute_accuracy(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算整体和分类正确率

    Args:
        results: 评测结果列表，每项包含：
            - question_id
            - question_type
            - predicted: 模型答案
            - target: 标准答案
            - correct: bool

    Returns:
        包含 overall_accuracy 和按 question_type 分类的正确率
    """
    if not results:
        return {"overall_accuracy": 0.0, "total": 0, "correct": 0, "by_type": {}}

    total = len(results)
    correct = sum(1 for r in results if r["correct"])

    # 按题型分组
    by_type = {}
    for r in results:
        qtype = r.get("question_type", "未知")
        if qtype not in by_type:
            by_type[qtype] = {"total": 0, "correct": 0}
        by_type[qtype]["total"] += 1
        if r["correct"]:
            by_type[qtype]["correct"] += 1

    for qtype, stats in by_type.items():
        stats["accuracy"] = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0

    return {
        "overall_accuracy": correct / total,
        "total": total,
        "correct": correct,
        "by_type": by_type,
    }

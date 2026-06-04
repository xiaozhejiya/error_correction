"""
RAG 检索召回率评估工具。

输入一组已标注查询样本，统计 Recall@K，便于验证：
- Recall@5 >= 75%
- Recall@10 >= 85%
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True)
class RetrievalCase:
    query: str
    expected_source_ids: list[int]
    retrieved_source_ids: list[int]


def recall_at_k(expected_source_ids: Iterable[int], retrieved_source_ids: Iterable[int], k: int) -> float:
    expected = {int(item) for item in expected_source_ids}
    if not expected:
        return 0.0
    retrieved_top_k = {int(item) for item in list(retrieved_source_ids)[:k]}
    hit_count = len(expected & retrieved_top_k)
    return hit_count / len(expected)


def evaluate_recall(cases: Iterable[RetrievalCase], ks: tuple[int, ...] = (5, 10)) -> dict[str, float]:
    case_list = list(cases)
    if not case_list:
        return {f"Recall@{k}": 0.0 for k in ks}

    scores = {}
    for k in ks:
        total = 0.0
        for case in case_list:
            total += recall_at_k(case.expected_source_ids, case.retrieved_source_ids, k)
        scores[f"Recall@{k}"] = total / len(case_list)
    return scores

"""
correct_questions_node 合并逻辑的单元测试

不调用真实 LLM，只测试标记筛选 + 结果合并逻辑。
"""

import json
import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from src.workflow import correct_questions_node


def _q(qid, text="内容", needs_correction=False, ocr_issues=None):
    """构造题目 dict"""
    q = {
        "question_id": qid,
        "question_type": "选择题",
        "content_blocks": [{"block_type": "text", "content": text}],
        "needs_correction": needs_correction,
    }
    if ocr_issues:
        q["ocr_issues"] = ocr_issues
    return q


class TestCorrectQuestionsNode:
    """correct_questions_node 合并逻辑测试"""

    def test_skip_when_no_questions(self):
        state = {"questions": []}
        result = correct_questions_node(state)
        assert result["questions"] == []

    def test_skip_when_no_flagged(self):
        """无标记题目应直接跳过"""
        qs = [_q("1"), _q("2")]
        state = {"questions": qs}
        result = correct_questions_node(state)
        assert result["questions"] == qs

    @patch("agents.error_correction.tools.correct_batch")
    def test_merge_corrected(self, mock_correct_batch, tmp_path):
        """纠错结果应按 question_id 合并回原列表"""
        q1 = _q("1")
        q2 = _q("2", text="有错误", needs_correction=True, ocr_issues=["乱码"])
        q3 = _q("3")

        # 模拟 correct_batch 返回纠错后的题目
        corrected_q2 = {
            "question_id": "2",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "已修复内容"}],
            "corrections_applied": ["替换乱码字符"],
        }
        mock_correct_batch.invoke.return_value = json.dumps([corrected_q2], ensure_ascii=False)

        # 创建 agent_input.json 供纠错节点读取
        results_dir = str(tmp_path)
        agent_input = json.dumps([{"page_index": 0, "blocks": []}])
        with open(os.path.join(results_dir, "agent_input.json"), "w") as f:
            f.write(agent_input)

        with patch("core.config.settings.results_dir", Path(results_dir)):
            state = {"questions": [q1, q2, q3]}
            result = correct_questions_node(state)

        merged = result["questions"]
        assert len(merged) == 3

        # q2 应被替换为纠错版本
        merged_q2 = next(q for q in merged if q["question_id"] == "2")
        assert merged_q2["content_blocks"][0]["content"] == "已修复内容"
        assert merged_q2["needs_correction"] is False
        assert merged_q2["ocr_issues"] is None

        # q1, q3 不受影响
        merged_q1 = next(q for q in merged if q["question_id"] == "1")
        assert merged_q1["content_blocks"][0]["content"] == "内容"

    @patch("agents.error_correction.tools.correct_batch")
    def test_invalid_json_keeps_original(self, mock_correct_batch, tmp_path):
        """纠错返回无效 JSON 时应保留原始题目"""
        q1 = _q("1", needs_correction=True)
        mock_correct_batch.invoke.return_value = "not valid json"

        results_dir = str(tmp_path)
        with open(os.path.join(results_dir, "agent_input.json"), "w") as f:
            f.write("{}")

        with patch("core.config.settings.results_dir", Path(results_dir)):
            state = {"questions": [q1]}
            result = correct_questions_node(state)

        # 应保留原始题目
        assert result["questions"] == [q1]

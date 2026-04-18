"""
question_tools.py 工具函数的单元测试

覆盖函数（使用 tmp_path 避免写入真实目录）：
- save_questions (文件 I/O 逻辑)
- log_issue (文件 I/O 逻辑)
"""

import os
import json
import pytest
from unittest.mock import patch
from agents.error_correction.tools.question_tools import save_questions, log_issue


# ═══════════════════════════════════════════════════════════
# save_questions
# ═══════════════════════════════════════════════════════════


class TestSaveQuestions:
    """save_questions 工具测试"""

    def test_save_new_file(self, tmp_path):
        out = str(tmp_path / "questions.json")
        questions = [{"question_id": "1", "content_blocks": []}]

        with patch("core.config.settings.results_dir", tmp_path):
            result = save_questions.invoke({
                "questions": questions,
                "output_path": out,
            })

        assert "成功保存" in result
        saved = json.load(open(out, encoding="utf-8"))
        assert len(saved) == 1

    def test_append_to_existing(self, tmp_path):
        """第二次调用应追加到已有数据"""
        out = str(tmp_path / "questions.json")
        q1 = [{"question_id": "1", "content_blocks": []}]
        q2 = [{"question_id": "2", "content_blocks": []}]

        with patch("core.config.settings.results_dir", tmp_path):
            save_questions.invoke({"questions": q1, "output_path": out})
            save_questions.invoke({"questions": q2, "output_path": out})

        saved = json.load(open(out, encoding="utf-8"))
        assert len(saved) == 2

    def test_subject_metadata(self, tmp_path):
        """传入 subject 应保存到 split_metadata.json"""
        out = str(tmp_path / "questions.json")
        questions = [{"question_id": "1", "content_blocks": []}]

        with patch("core.config.settings.results_dir", tmp_path):
            save_questions.invoke({
                "questions": questions,
                "subject": "高中数学",
                "output_path": out,
            })

        meta_path = tmp_path / "split_metadata.json"
        assert meta_path.exists()
        meta = json.load(open(meta_path, encoding="utf-8"))
        assert meta["subject"] == "高中数学"

    def test_empty_subject_no_metadata(self, tmp_path):
        """空 subject 不应生成 metadata"""
        out = str(tmp_path / "questions.json")
        questions = [{"question_id": "1", "content_blocks": []}]

        with patch("core.config.settings.results_dir", tmp_path):
            save_questions.invoke({
                "questions": questions,
                "subject": "",
                "output_path": out,
            })

        meta_path = tmp_path / "split_metadata.json"
        assert not meta_path.exists()


# ═══════════════════════════════════════════════════════════
# log_issue
# ═══════════════════════════════════════════════════════════


class TestLogIssue:
    """log_issue 工具测试"""

    def test_basic_log(self, tmp_path):
        with patch("core.config.settings.results_dir", tmp_path):
            result = log_issue.invoke({
                "issue_type": "unclear_boundary",
                "description": "第3题和第4题边界不清",
            })

        assert "问题已记录" in result

        log_path = tmp_path / "split_issues.jsonl"
        assert log_path.exists()
        line = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert line["issue_type"] == "unclear_boundary"
        assert "第3题" in line["description"]

    def test_with_block_info(self, tmp_path):
        with patch("core.config.settings.results_dir", tmp_path):
            log_issue.invoke({
                "issue_type": "missing_question_number",
                "description": "缺少题号",
                "block_info": {"block_id": "b3", "content": "..."},
            })

        log_path = tmp_path / "split_issues.jsonl"
        line = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert "block_info" in line
        assert line["block_info"]["block_id"] == "b3"

    def test_append_multiple(self, tmp_path):
        """多次调用应追加（JSONL 格式）"""
        with patch("core.config.settings.results_dir", tmp_path):
            log_issue.invoke({"issue_type": "a", "description": "issue 1"})
            log_issue.invoke({"issue_type": "b", "description": "issue 2"})

        log_path = tmp_path / "split_issues.jsonl"
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

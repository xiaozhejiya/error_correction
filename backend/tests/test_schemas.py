"""
Pydantic schema 模型的单元测试

覆盖模型：
- ContentBlock
- Question
- QuestionSplitResult
- CorrectedQuestion
- CorrectionResult
"""

import pytest
from pydantic import ValidationError
from agents.error_correction.schemas import (
    ContentBlock,
    Question,
    QuestionSplitResult,
    CorrectedQuestion,
    CorrectionResult,
)


# ═══════════════════════════════════════════════════════════
# ContentBlock
# ═══════════════════════════════════════════════════════════


class TestContentBlock:
    """ContentBlock 模型测试"""

    def test_text_block(self):
        b = ContentBlock(block_type="text", content="hello")
        assert b.block_type == "text"
        assert b.content == "hello"

    def test_image_block(self):
        b = ContentBlock(block_type="image", content="/images/test.jpg")
        assert b.block_type == "image"

    def test_invalid_block_type(self):
        """不允许的 block_type 应校验失败"""
        with pytest.raises(ValidationError):
            ContentBlock(block_type="video", content="x")

    def test_missing_content(self):
        with pytest.raises(ValidationError):
            ContentBlock(block_type="text")


# ═══════════════════════════════════════════════════════════
# Question
# ═══════════════════════════════════════════════════════════


class TestQuestion:
    """Question 模型测试"""

    def _minimal(self, **kwargs):
        defaults = {
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "题目"}],
        }
        defaults.update(kwargs)
        return Question(**defaults)

    def test_minimal_valid(self):
        q = self._minimal()
        assert q.question_id == "1"
        assert q.options is None
        assert q.has_formula is False
        assert q.needs_correction is False

    def test_all_question_types(self):
        for qt in ["选择题", "填空题", "解答题", "判断题"]:
            q = self._minimal(question_type=qt)
            assert q.question_type == qt

    def test_invalid_question_type(self):
        with pytest.raises(ValidationError):
            self._minimal(question_type="论述题")

    def test_with_options(self):
        q = self._minimal(options=["A. 1", "B. 2", "C. 3", "D. 4"])
        assert len(q.options) == 4

    def test_with_image_refs(self):
        q = self._minimal(
            has_image=True,
            image_refs=["/images/img_in_image_box_10_20_30_40.jpg"]
        )
        assert q.has_image is True
        assert len(q.image_refs) == 1

    def test_with_knowledge_tags(self):
        q = self._minimal(knowledge_tags=["三角函数", "诱导公式"])
        assert q.knowledge_tags == ["三角函数", "诱导公式"]

    def test_with_ocr_issues(self):
        q = self._minimal(
            needs_correction=True,
            ocr_issues=["公式断裂: 缺少闭合括号"]
        )
        assert q.needs_correction is True
        assert len(q.ocr_issues) == 1

    def test_model_dump(self):
        """model_dump 应产出完整字段"""
        q = self._minimal()
        d = q.model_dump()
        assert "question_id" in d
        assert "content_blocks" in d
        assert "needs_correction" in d


# ═══════════════════════════════════════════════════════════
# QuestionSplitResult
# ═══════════════════════════════════════════════════════════


class TestQuestionSplitResult:
    """QuestionSplitResult 模型测试"""

    def test_empty_questions(self):
        r = QuestionSplitResult(questions=[])
        assert r.questions == []

    def test_with_questions(self):
        r = QuestionSplitResult(questions=[{
            "question_id": "1",
            "question_type": "填空题",
            "content_blocks": [{"block_type": "text", "content": "x"}],
        }])
        assert len(r.questions) == 1


# ═══════════════════════════════════════════════════════════
# CorrectedQuestion & CorrectionResult
# ═══════════════════════════════════════════════════════════


class TestCorrectedQuestion:
    """CorrectedQuestion 模型测试"""

    def test_valid(self):
        cq = CorrectedQuestion(
            question_id="3",
            question_type="解答题",
            content_blocks=[{"block_type": "text", "content": "修复后的内容"}],
            corrections_applied=["修复断裂公式"],
        )
        assert cq.corrections_applied == ["修复断裂公式"]

    def test_missing_corrections(self):
        """corrections_applied 为必填字段"""
        with pytest.raises(ValidationError):
            CorrectedQuestion(
                question_id="1",
                question_type="选择题",
                content_blocks=[{"block_type": "text", "content": "x"}],
            )


class TestCorrectionResult:
    """CorrectionResult 模型测试"""

    def test_empty(self):
        r = CorrectionResult(corrected_questions=[])
        assert r.corrected_questions == []

    def test_with_corrected(self):
        r = CorrectionResult(corrected_questions=[{
            "question_id": "5",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": "fixed"}],
            "corrections_applied": ["替换乱码字符"],
        }])
        assert len(r.corrected_questions) == 1

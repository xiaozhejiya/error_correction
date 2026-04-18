"""
export_wrongbook() 单元测试

使用 tmp_path fixture 避免写入真实文件系统。
"""

import os
import pytest
from unittest.mock import patch
from src.utils import export_wrongbook


class TestExportWrongbook:
    """export_wrongbook 测试"""

    def _make_question(self, qid, text="题目内容", qtype="选择题", options=None,
                       image_refs=None, content_blocks=None):
        """构造标准题目 dict"""
        if content_blocks is None:
            content_blocks = [{"block_type": "text", "content": text}]
        q = {
            "question_id": qid,
            "question_type": qtype,
            "content_blocks": content_blocks,
        }
        if options is not None:
            q["options"] = options
        if image_refs is not None:
            q["image_refs"] = image_refs
        return q

    def test_basic_export(self, tmp_path):
        """基本导出：选中的题目应出现在输出中"""
        q1 = self._make_question("1", "第一题")
        q2 = self._make_question("2", "第二题")
        out = str(tmp_path / "test.md")

        result = export_wrongbook([q1, q2], ["1", "2"], output_path=out)

        assert result == out
        content = open(out, encoding="utf-8").read()
        assert "第一题" in content
        assert "第二题" in content
        assert "共收录 2 道题目" in content

    def test_filter_selected_ids(self, tmp_path):
        """只导出选中的题目"""
        q1 = self._make_question("1", "选中的题目")
        q2 = self._make_question("2", "未选中的题目")
        out = str(tmp_path / "test.md")

        export_wrongbook([q1, q2], ["1"], output_path=out)

        content = open(out, encoding="utf-8").read()
        assert "选中的题目" in content
        assert "未选中的题目" not in content
        assert "共收录 1 道题目" in content

    def test_empty_selection(self, tmp_path):
        """选中列表为空时应生成空错题本"""
        q1 = self._make_question("1")
        out = str(tmp_path / "test.md")

        export_wrongbook([q1], [], output_path=out)

        content = open(out, encoding="utf-8").read()
        assert "共收录 0 道题目" in content

    def test_options_rendered(self, tmp_path):
        """选项应被渲染"""
        q = self._make_question("1", options=["A. 选项一", "B. 选项二"])
        out = str(tmp_path / "test.md")

        export_wrongbook([q], ["1"], output_path=out)

        content = open(out, encoding="utf-8").read()
        assert "A. 选项一" in content
        assert "B. 选项二" in content

    def test_image_block_rendered(self, tmp_path):
        """image block 应渲染为 markdown 图片"""
        q = self._make_question("1", content_blocks=[
            {"block_type": "text", "content": "看图回答"},
            {"block_type": "image", "content": "/images/img_in_image_box_10_20_30_40.jpg"},
        ])
        out = str(tmp_path / "test.md")

        export_wrongbook([q], ["1"], output_path=out)

        content = open(out, encoding="utf-8").read()
        assert "![图片](" in content
        assert "img_in_image_box_10_20_30_40.jpg" in content

    def test_question_type_shown(self, tmp_path):
        """题目类型应出现在输出中"""
        q = self._make_question("5", qtype="填空题")
        out = str(tmp_path / "test.md")

        export_wrongbook([q], ["5"], output_path=out)

        content = open(out, encoding="utf-8").read()
        assert "填空题" in content

    def test_answer_sections_present(self, tmp_path):
        """应包含我的答案、正确答案、解析三个区域"""
        q = self._make_question("1")
        out = str(tmp_path / "test.md")

        export_wrongbook([q], ["1"], output_path=out)

        content = open(out, encoding="utf-8").read()
        assert "### 我的答案" in content
        assert "### 正确答案" in content
        assert "### 解析" in content

    def test_image_refs_fallback(self, tmp_path):
        """content_blocks 未覆盖的 image_refs 应兜底渲染"""
        q = self._make_question("1", content_blocks=[
            {"block_type": "text", "content": "题目"},
        ], image_refs=[
            "/images/img_in_chart_box_100_200_300_400.jpg",
        ])
        out = str(tmp_path / "test.md")

        export_wrongbook([q], ["1"], output_path=out)

        content = open(out, encoding="utf-8").read()
        assert "img_in_chart_box_100_200_300_400.jpg" in content

    def test_image_refs_not_duplicated(self, tmp_path):
        """content_blocks 已渲染的图片不应在 image_refs 兜底中重复"""
        img_path = "/images/img_in_image_box_10_20_30_40.jpg"
        q = self._make_question("1", content_blocks=[
            {"block_type": "image", "content": img_path},
        ], image_refs=[img_path])
        out = str(tmp_path / "test.md")

        export_wrongbook([q], ["1"], output_path=out)

        content = open(out, encoding="utf-8").read()
        # 图片应只出现 1 次 (来自 content_blocks)
        assert content.count("img_in_image_box_10_20_30_40.jpg") == 1

    def test_multiple_questions_numbered(self, tmp_path):
        """多道题目应有编号"""
        q1 = self._make_question("1", "题目一")
        q2 = self._make_question("2", "题目二")
        out = str(tmp_path / "test.md")

        export_wrongbook([q1, q2], ["1", "2"], output_path=out)

        content = open(out, encoding="utf-8").read()
        assert "## 1. 题目 1" in content
        assert "## 2. 题目 2" in content

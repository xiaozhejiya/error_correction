"""
集成测试 — 验证大模型能否正常分割题目

用法:
    # 默认使用 openai
    pytest tests/test_split_integration.py -v -s

    # 指定模型
    pytest tests/test_split_integration.py -v -s --model-provider anthropic
    pytest tests/test_split_integration.py -v -s --model-provider openai

需要配置对应的环境变量（OPENAI_API_KEY 或 ANTHROPIC_API_KEY）。
"""

import os
import json
import pytest
from dotenv import load_dotenv

load_dotenv()

# ── 跳过条件 ───────────────────────────────────────────────

skip_no_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"),
    reason="未配置 LLM API Key（OPENAI_API_KEY 或 ANTHROPIC_API_KEY）",
)

# ── 测试数据路径 ───────────────────────────────────────────

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "sample_ocr_data.json"
)


@pytest.fixture(scope="session")
def ocr_data():
    """从 fixtures/sample_ocr_data.json 加载 OCR 测试数据"""
    path = os.path.abspath(FIXTURE_PATH)
    if not os.path.exists(path):
        pytest.skip(f"测试数据文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list) and len(data) > 0, "sample_ocr_data.json 应为非空列表"
    return data


@pytest.fixture(scope="session")
def split_result(ocr_data, model_provider):
    """调用 split_batch 一次，所有测试共享结果（节省 API 调用）"""
    from agents.error_correction.tools import split_batch

    result = split_batch.invoke({
        "ocr_data": json.dumps(ocr_data, ensure_ascii=False),
        "subject": "高中数学",
        "existing_tags": "",
        "model_provider": model_provider,
    })

    assert result, "split_batch 返回为空"
    assert not result.startswith("分割失败"), f"split_batch 失败: {result}"

    questions = json.loads(result)
    assert isinstance(questions, list), "返回值应为列表"
    return questions


# ── 测试用例 ───────────────────────────────────────────────


@skip_no_api_key
@pytest.mark.xfail(reason="LangChain ToolStrategy 与部分 API 兼容性问题，待上游修复")
class TestSplitIntegration:
    """集成测试：验证 split_batch 能否通过大模型正确分割题目"""

    def test_returns_non_empty(self, split_result):
        """应至少分割出一道题目"""
        assert len(split_result) > 0, "未分割出任何题目"

    def test_question_schema(self, split_result):
        """每道题目应符合 Question schema"""
        from agents.error_correction.schemas import Question

        for q_data in split_result:
            q = Question(**q_data)
            assert q.question_id, "question_id 不能为空"
            assert q.question_type in ("选择题", "填空题", "解答题", "判断题")
            assert len(q.content_blocks) > 0, f"题目 {q.question_id} 缺少 content_blocks"
            for block in q.content_blocks:
                assert block.block_type in ("text", "image")
                assert block.content, f"题目 {q.question_id} 存在空 content_block"

    def test_covers_all_questions(self, split_result, ocr_data):
        """应覆盖 OCR 数据中的所有题目"""
        # 从 OCR 数据中提取期望的题号
        import re
        expected_ids = set()
        for page in ocr_data:
            for block in page.get("blocks", []):
                text = block.get("block_content", "")
                m = re.match(r"^(\d+)\s*[.、．]", text)
                if m:
                    expected_ids.add(m.group(1))

        actual_ids = {q["question_id"] for q in split_result}

        assert expected_ids, "未从 OCR 数据中解析出任何期望题号"
        missing = expected_ids - actual_ids
        assert not missing, f"缺少题目: {missing}（期望 {expected_ids}，实际 {actual_ids}）"

    def test_choice_questions_have_options(self, split_result):
        """选择题应包含 options 字段"""
        choice_qs = [q for q in split_result if q["question_type"] == "选择题"]

        for q in choice_qs:
            assert q.get("options"), f"选择题 {q['question_id']} 缺少 options"
            assert len(q["options"]) >= 2, f"选择题 {q['question_id']} 选项数不足"

    def test_formula_detection(self, split_result):
        """包含 LaTeX 公式的题目应标记 has_formula"""
        for q in split_result:
            text = " ".join(b["content"] for b in q["content_blocks"] if b["block_type"] == "text")
            options_text = " ".join(q.get("options") or [])
            all_text = text + " " + options_text
            has_latex = "$" in all_text
            if has_latex:
                assert q.get("has_formula"), (
                    f"题目 {q['question_id']} 含 LaTeX 但 has_formula=false"
                )

    def test_knowledge_tags(self, split_result):
        """应为题目标注知识点"""
        tagged_count = sum(1 for q in split_result if q.get("knowledge_tags"))
        assert tagged_count >= len(split_result) // 2, (
            f"至少一半题目应有知识点标注，实际 {tagged_count}/{len(split_result)}"
        )

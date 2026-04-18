"""
workflow.py 中纯函数的单元测试

覆盖函数：
- _simplify_ocr_results
- _build_overlapping_batches
- _dedup_questions
- _question_richness
- _sort_key
- _extract_text_sample
- _identify_subject（含 LLM 预检层）
"""

import pytest
from unittest.mock import patch, MagicMock
from src.utils import simplify_ocr_results as _simplify_ocr_results
from src.paddleocr_client import PaddleOCRClient
from src.workflow import (
    _build_overlapping_batches,
    _run_ocr_and_simplify,
    _dedup_questions,
    _question_richness,
    _sort_key,
    _extract_text_sample,
    _identify_subject,
)


# ═══════════════════════════════════════════════════════════
# _simplify_ocr_results
# ═══════════════════════════════════════════════════════════


class TestSimplifyOcrResults:
    """_simplify_ocr_results 测试"""

    def test_empty_input(self):
        assert _simplify_ocr_results([]) == []

    def test_skip_result_without_layout(self):
        """缺少 layoutParsingResults 的结果应跳过"""
        assert _simplify_ocr_results([{"other_key": 123}]) == []

    def test_skip_page_without_pruned(self):
        """缺少 prunedResult 的页应跳过"""
        result = [{"layoutParsingResults": [{"noKey": True}]}]
        assert _simplify_ocr_results(result) == []

    def test_basic_text_block(self):
        """普通文本 block 应保留原始字段"""
        ocr = [{
            "layoutParsingResults": [{
                "prunedResult": {
                    "parsing_res_list": [{
                        "block_label": "text",
                        "block_content": "Hello",
                        "block_order": 1,
                    }]
                }
            }]
        }]
        result = _simplify_ocr_results(ocr)
        assert len(result) == 1
        assert result[0]["page_index"] == 0
        assert len(result[0]["blocks"]) == 1
        block = result[0]["blocks"][0]
        assert block["block_label"] == "text"
        assert block["block_content"] == "Hello"
        assert block["block_order"] == 1

    def test_image_block_with_bbox(self):
        """image 类型空内容 block + bbox 应生成 img_in_image_box 路径"""
        ocr = [{
            "layoutParsingResults": [{
                "prunedResult": {
                    "parsing_res_list": [{
                        "block_label": "image",
                        "block_content": "",
                        "block_order": 2,
                        "block_bbox": [100.5, 200.3, 300.7, 400.9],
                    }]
                }
            }]
        }]
        result = _simplify_ocr_results(ocr)
        block = result[0]["blocks"][0]
        assert block["block_content"] == "/images/img_in_image_box_100_200_300_400.jpg"

    def test_chart_block_with_bbox(self):
        """chart 类型空内容 block + bbox 应生成 img_in_chart_box 路径"""
        ocr = [{
            "layoutParsingResults": [{
                "prunedResult": {
                    "parsing_res_list": [{
                        "block_label": "chart",
                        "block_content": "",
                        "block_order": 3,
                        "block_bbox": [10, 20, 30, 40],
                    }]
                }
            }]
        }]
        result = _simplify_ocr_results(ocr)
        block = result[0]["blocks"][0]
        assert block["block_content"] == "/images/img_in_chart_box_10_20_30_40.jpg"

    def test_image_with_content_not_replaced(self):
        """image/chart 有 content 时不应被 bbox 路径替换"""
        ocr = [{
            "layoutParsingResults": [{
                "prunedResult": {
                    "parsing_res_list": [{
                        "block_label": "image",
                        "block_content": "existing_content",
                        "block_order": 1,
                        "block_bbox": [0, 0, 100, 100],
                    }]
                }
            }]
        }]
        result = _simplify_ocr_results(ocr)
        assert result[0]["blocks"][0]["block_content"] == "existing_content"

    def test_image_no_bbox(self):
        """image block 无 bbox 时保持空 content"""
        ocr = [{
            "layoutParsingResults": [{
                "prunedResult": {
                    "parsing_res_list": [{
                        "block_label": "image",
                        "block_content": "",
                        "block_order": 1,
                    }]
                }
            }]
        }]
        result = _simplify_ocr_results(ocr)
        assert result[0]["blocks"][0]["block_content"] == ""

    def test_multi_page_indexing(self):
        """多页 page_index 应递增"""
        ocr = [{
            "layoutParsingResults": [
                {"prunedResult": {"parsing_res_list": [
                    {"block_label": "text", "block_content": "p0", "block_order": 0}
                ]}},
                {"prunedResult": {"parsing_res_list": [
                    {"block_label": "text", "block_content": "p1", "block_order": 0}
                ]}},
            ]
        }]
        result = _simplify_ocr_results(ocr)
        assert len(result) == 2
        assert result[0]["page_index"] == 0
        assert result[1]["page_index"] == 1

    def test_multi_result_page_index_continues(self):
        """跨多个 result 对象时 page_index 应连续"""
        ocr = [
            {"layoutParsingResults": [
                {"prunedResult": {"parsing_res_list": [
                    {"block_label": "text", "block_content": "r0p0", "block_order": 0}
                ]}}
            ]},
            {"layoutParsingResults": [
                {"prunedResult": {"parsing_res_list": [
                    {"block_label": "text", "block_content": "r1p0", "block_order": 0}
                ]}}
            ]},
        ]
        result = _simplify_ocr_results(ocr)
        assert len(result) == 2
        assert result[0]["page_index"] == 0
        assert result[1]["page_index"] == 1

    def test_empty_parsing_res_list(self):
        """parsing_res_list 为空时应产出空 blocks 页"""
        ocr = [{
            "layoutParsingResults": [{
                "prunedResult": {"parsing_res_list": []}
            }]
        }]
        result = _simplify_ocr_results(ocr)
        assert len(result) == 1
        assert result[0]["blocks"] == []

    def test_only_keeps_three_fields(self):
        """输出 block 只应包含 block_label, block_content, block_order"""
        ocr = [{
            "layoutParsingResults": [{
                "prunedResult": {
                    "parsing_res_list": [{
                        "block_label": "text",
                        "block_content": "hi",
                        "block_order": 1,
                        "block_bbox": [0, 0, 10, 10],
                        "extra_field": "should_not_appear",
                    }]
                }
            }]
        }]
        result = _simplify_ocr_results(ocr)
        block = result[0]["blocks"][0]
        assert set(block.keys()) == {"block_label", "block_content", "block_order"}


# ═══════════════════════════════════════════════════════════
# _build_overlapping_batches
# ═══════════════════════════════════════════════════════════


class TestBuildOverlappingBatches:
    """_build_overlapping_batches 测试"""

    def _pages(self, n):
        """快速生成 n 个 page dict"""
        return [{"page_index": i, "blocks": []} for i in range(n)]

    def test_empty(self):
        assert _build_overlapping_batches([]) == []

    def test_single_page(self):
        pages = self._pages(1)
        batches = _build_overlapping_batches(pages, batch_size=2, overlap=1)
        assert len(batches) == 1
        assert batches[0] == pages

    def test_exactly_batch_size(self):
        pages = self._pages(2)
        batches = _build_overlapping_batches(pages, batch_size=2, overlap=1)
        assert len(batches) == 1
        assert batches[0] == pages

    def test_three_pages(self):
        """3 页, batch=2, overlap=1 → 2 批: [0,1], [1,2]"""
        pages = self._pages(3)
        batches = _build_overlapping_batches(pages, batch_size=2, overlap=1)
        assert len(batches) == 2
        assert [p["page_index"] for p in batches[0]] == [0, 1]
        assert [p["page_index"] for p in batches[1]] == [1, 2]

    def test_five_pages(self):
        """5 页, batch=2, overlap=1 → 4 批: [0,1],[1,2],[2,3],[3,4]"""
        pages = self._pages(5)
        batches = _build_overlapping_batches(pages, batch_size=2, overlap=1)
        assert len(batches) == 4
        for i, batch in enumerate(batches):
            assert [p["page_index"] for p in batch] == [i, i + 1]

    def test_no_overlap(self):
        """6 页, batch=2, overlap=0 → 3 批: [0,1],[2,3],[4,5]"""
        pages = self._pages(6)
        batches = _build_overlapping_batches(pages, batch_size=2, overlap=0)
        assert len(batches) == 3
        assert [p["page_index"] for p in batches[0]] == [0, 1]
        assert [p["page_index"] for p in batches[1]] == [2, 3]
        assert [p["page_index"] for p in batches[2]] == [4, 5]

    def test_large_batch_size(self):
        """batch_size > n_pages → 返回单个批次"""
        pages = self._pages(3)
        batches = _build_overlapping_batches(pages, batch_size=10, overlap=1)
        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_batch_size_3_overlap_1(self):
        """7 页, batch=3, overlap=1 → 3 批: [0,1,2],[2,3,4],[4,5,6]"""
        pages = self._pages(7)
        batches = _build_overlapping_batches(pages, batch_size=3, overlap=1)
        assert len(batches) == 3
        assert [p["page_index"] for p in batches[0]] == [0, 1, 2]
        assert [p["page_index"] for p in batches[1]] == [2, 3, 4]
        assert [p["page_index"] for p in batches[2]] == [4, 5, 6]

    def test_last_batch_may_be_shorter(self):
        """4 页, batch=3, overlap=1 → 2 批: [0,1,2],[2,3]"""
        pages = self._pages(4)
        batches = _build_overlapping_batches(pages, batch_size=3, overlap=1)
        assert len(batches) == 2
        assert [p["page_index"] for p in batches[0]] == [0, 1, 2]
        assert [p["page_index"] for p in batches[1]] == [2, 3]


# ═══════════════════════════════════════════════════════════
# _question_richness & _sort_key
# ═══════════════════════════════════════════════════════════


class TestQuestionRichness:
    """_question_richness 测试"""

    def test_empty_question(self):
        assert _question_richness({}) == 0

    def test_content_blocks_only(self):
        q = {"content_blocks": [
            {"content": "hello"},       # 5
            {"content": "world!!"},     # 7
        ]}
        assert _question_richness(q) == 12

    def test_options_only(self):
        q = {"options": ["A. 1", "B. 2"]}
        assert _question_richness(q) == 8  # 4 + 4

    def test_combined(self):
        q = {
            "content_blocks": [{"content": "abc"}],  # 3
            "options": ["A", "BB"],                   # 1 + 2
        }
        assert _question_richness(q) == 6

    def test_none_options(self):
        """options 为 None 时不应报错"""
        q = {"content_blocks": [{"content": "x"}], "options": None}
        assert _question_richness(q) == 1

    def test_block_without_content_key(self):
        """block 缺少 content 键时应计为 0"""
        q = {"content_blocks": [{"other": "data"}]}
        assert _question_richness(q) == 0


class TestSortKey:
    """_sort_key 测试"""

    def test_numeric_id(self):
        assert _sort_key("5") == (0, 5, "")

    def test_large_numeric(self):
        assert _sort_key("123") == (0, 123, "")

    def test_non_numeric_id(self):
        assert _sort_key("A1") == (1, 0, "A1")

    def test_empty_id(self):
        assert _sort_key("") == (1, 0, "")

    def test_numeric_sorts_before_string(self):
        """数字 id 应排在非数字 id 前面"""
        assert _sort_key("1") < _sort_key("A")

    def test_numeric_order(self):
        ids = ["10", "2", "1", "20", "3"]
        sorted_ids = sorted(ids, key=_sort_key)
        assert sorted_ids == ["1", "2", "3", "10", "20"]

    def test_mixed_order(self):
        ids = ["B", "2", "A", "1"]
        sorted_ids = sorted(ids, key=_sort_key)
        assert sorted_ids == ["1", "2", "A", "B"]


# ═══════════════════════════════════════════════════════════
# _dedup_questions
# ═══════════════════════════════════════════════════════════


class TestDedupQuestions:
    """_dedup_questions 测试"""

    def test_empty(self):
        assert _dedup_questions([]) == []

    def test_no_duplicates(self):
        qs = [
            {"question_id": "1", "content_blocks": [{"content": "q1"}]},
            {"question_id": "2", "content_blocks": [{"content": "q2"}]},
        ]
        result = _dedup_questions(qs)
        assert len(result) == 2
        assert [q["question_id"] for q in result] == ["1", "2"]

    def test_duplicate_keeps_richer(self):
        """重复 id 保留内容更丰富的版本"""
        q_short = {"question_id": "1", "content_blocks": [{"content": "ab"}]}
        q_long = {"question_id": "1", "content_blocks": [{"content": "abcdef"}]}
        result = _dedup_questions([q_short, q_long])
        assert len(result) == 1
        assert result[0]["content_blocks"][0]["content"] == "abcdef"

    def test_duplicate_keeps_richer_reverse_order(self):
        """即使较丰富的版本先出现也正确"""
        q_long = {"question_id": "1", "content_blocks": [{"content": "abcdef"}]}
        q_short = {"question_id": "1", "content_blocks": [{"content": "ab"}]}
        result = _dedup_questions([q_long, q_short])
        assert len(result) == 1
        assert result[0]["content_blocks"][0]["content"] == "abcdef"

    def test_skip_empty_id(self):
        """空 question_id 应被跳过"""
        qs = [
            {"question_id": "", "content_blocks": [{"content": "skip me"}]},
            {"question_id": "1", "content_blocks": [{"content": "keep me"}]},
        ]
        result = _dedup_questions(qs)
        assert len(result) == 1
        assert result[0]["question_id"] == "1"

    def test_skip_missing_id(self):
        """缺少 question_id 键应被跳过"""
        qs = [
            {"content_blocks": [{"content": "no id"}]},
            {"question_id": "2", "content_blocks": [{"content": "has id"}]},
        ]
        result = _dedup_questions(qs)
        assert len(result) == 1

    def test_sorted_output(self):
        """输出应按题号排序"""
        qs = [
            {"question_id": "3", "content_blocks": []},
            {"question_id": "1", "content_blocks": []},
            {"question_id": "2", "content_blocks": []},
        ]
        result = _dedup_questions(qs)
        assert [q["question_id"] for q in result] == ["1", "2", "3"]

    def test_mixed_id_types_sorted(self):
        """数字和字母 id 混合排序"""
        qs = [
            {"question_id": "B", "content_blocks": []},
            {"question_id": "2", "content_blocks": []},
            {"question_id": "A", "content_blocks": []},
            {"question_id": "1", "content_blocks": []},
        ]
        result = _dedup_questions(qs)
        assert [q["question_id"] for q in result] == ["1", "2", "A", "B"]

    def test_richness_with_options(self):
        """options 也计入 richness"""
        q_no_opt = {"question_id": "1", "content_blocks": [{"content": "abc"}]}
        q_with_opt = {
            "question_id": "1",
            "content_blocks": [{"content": "ab"}],
            "options": ["A. long option text"],
        }
        result = _dedup_questions([q_no_opt, q_with_opt])
        assert len(result) == 1
        # q_with_opt: 2 + 19 = 21 > q_no_opt: 3
        assert result[0].get("options") is not None


# ═══════════════════════════════════════════════════════════
# _extract_text_sample
# ═══════════════════════════════════════════════════════════


class TestExtractTextSample:
    """_extract_text_sample 测试"""

    def test_empty_input(self):
        assert _extract_text_sample([]) == ""

    def test_extracts_text_blocks(self):
        """应提取 text 类型 block 的内容"""
        ocr = [{
            "page_index": 0,
            "blocks": [
                {"block_label": "text", "block_content": "hello"},
                {"block_label": "text", "block_content": "world"},
            ]
        }]
        result = _extract_text_sample(ocr)
        assert "hello" in result
        assert "world" in result

    def test_includes_title_blocks(self):
        """应包含 paragraph_title 和 doc_title"""
        ocr = [{
            "page_index": 0,
            "blocks": [
                {"block_label": "doc_title", "block_content": "数学试卷"},
                {"block_label": "paragraph_title", "block_content": "选择题"},
            ]
        }]
        result = _extract_text_sample(ocr)
        assert "数学试卷" in result
        assert "选择题" in result

    def test_ignores_non_text_blocks(self):
        """不应包含 image/chart 类型"""
        ocr = [{
            "page_index": 0,
            "blocks": [
                {"block_label": "image", "block_content": "图片内容"},
                {"block_label": "text", "block_content": "文本内容"},
            ]
        }]
        result = _extract_text_sample(ocr)
        assert "图片内容" not in result
        assert "文本内容" in result

    def test_only_first_two_pages(self):
        """只应读取前 2 页"""
        ocr = [
            {"page_index": 0, "blocks": [{"block_label": "text", "block_content": "页面0"}]},
            {"page_index": 1, "blocks": [{"block_label": "text", "block_content": "页面1"}]},
            {"page_index": 2, "blocks": [{"block_label": "text", "block_content": "页面2"}]},
        ]
        result = _extract_text_sample(ocr)
        assert "页面0" in result
        assert "页面1" in result
        assert "页面2" not in result


# ═══════════════════════════════════════════════════════════
# _identify_subject
# ═══════════════════════════════════════════════════════════


class TestIdentifySubject:
    """_identify_subject 测试

    autouse fixture 默认 mock detect_subject_via_llm 返回空字符串，
    确保关键词 / 特征推断的 fallback 逻辑不受 LLM 层影响。
    """

    @pytest.fixture(autouse=True)
    def _mock_llm(self):
        with patch(
            "agents.error_correction.agent.detect_subject_via_llm",
            return_value="",
        ) as mock:
            self.mock_llm = mock
            yield mock

    def _make_ocr(self, text: str) -> list:
        """构造只有一页、一个 text block 的 OCR 数据"""
        return [{
            "page_index": 0,
            "blocks": [{
                "block_label": "text",
                "block_content": text,
            }]
        }]

    def test_empty_input(self):
        assert _identify_subject([], []) == ""

    def test_db_subject_priority(self):
        """db_subjects 应优先于关键词匹配"""
        ocr = self._make_ocr("本次高中物理考试")
        # db 里有 "高中物理"，同时也能通过关键词匹配
        result = _identify_subject(ocr, ["高中物理", "高中化学"])
        assert result == "高中物理"

    def test_keyword_match_math(self):
        ocr = self._make_ocr("2024年数学试卷")
        assert _identify_subject(ocr, []) == "高中数学"

    def test_keyword_match_physics(self):
        ocr = self._make_ocr("物理考试试题")
        assert _identify_subject(ocr, []) == "高中物理"

    def test_keyword_match_chemistry(self):
        ocr = self._make_ocr("化学试卷模拟题")
        assert _identify_subject(ocr, []) == "高中化学"

    def test_keyword_match_biology(self):
        ocr = self._make_ocr("生物试卷")
        assert _identify_subject(ocr, []) == "高中生物"

    def test_keyword_match_english(self):
        ocr = self._make_ocr("英语考试")
        assert _identify_subject(ocr, []) == "高中英语"

    def test_keyword_match_chinese(self):
        ocr = self._make_ocr("语文试题")
        assert _identify_subject(ocr, []) == "高中语文"

    def test_indicator_fallback_math(self):
        """关键词无匹配时，使用内容特征推断（>=2 个指标词）"""
        ocr = self._make_ocr("求函数 f(x) 在 x=1 处的导数")
        result = _identify_subject(ocr, [])
        assert result == "高中数学"

    def test_indicator_fallback_physics(self):
        ocr = self._make_ocr("一个物体以加速度 a 运动，速度从 0 增加到 v")
        result = _identify_subject(ocr, [])
        assert result == "高中物理"

    def test_indicator_insufficient(self):
        """只有 1 个指标词时不应匹配"""
        ocr = self._make_ocr("请计算函数值")
        result = _identify_subject(ocr, [])
        assert result == ""

    def test_only_reads_first_two_pages(self):
        """应只读取前 2 页内容"""
        ocr = [
            {"page_index": 0, "blocks": [
                {"block_label": "text", "block_content": "普通内容"}
            ]},
            {"page_index": 1, "blocks": [
                {"block_label": "text", "block_content": "普通内容2"}
            ]},
            {"page_index": 2, "blocks": [
                {"block_label": "text", "block_content": "数学试卷"}
            ]},
        ]
        # 第 3 页有 "数学试卷" 但不应被读取
        result = _identify_subject(ocr, [])
        assert result == ""

    def test_ignores_non_text_blocks(self):
        """非 text/paragraph_title/doc_title 类型的 block 不应参与匹配"""
        ocr = [{
            "page_index": 0,
            "blocks": [
                {"block_label": "image", "block_content": "数学试卷"},
                {"block_label": "chart", "block_content": "物理考试"},
            ]
        }]
        result = _identify_subject(ocr, [])
        assert result == ""

    def test_paragraph_title_included(self):
        """paragraph_title 类型的 block 应参与匹配"""
        ocr = [{
            "page_index": 0,
            "blocks": [
                {"block_label": "paragraph_title", "block_content": "数学试卷"},
            ]
        }]
        result = _identify_subject(ocr, [])
        assert result == "高中数学"

    def test_doc_title_included(self):
        """doc_title 类型的 block 应参与匹配"""
        ocr = [{
            "page_index": 0,
            "blocks": [
                {"block_label": "doc_title", "block_content": "化学考试期末卷"},
            ]
        }]
        result = _identify_subject(ocr, [])
        assert result == "高中化学"


# ═══════════════════════════════════════════════════════════
# _identify_subject — LLM 预检层专项测试
# ═══════════════════════════════════════════════════════════


class TestIdentifySubjectLLM:
    """_identify_subject LLM 预检层测试"""

    def _make_ocr(self, text: str) -> list:
        return [{
            "page_index": 0,
            "blocks": [{
                "block_label": "text",
                "block_content": text,
            }]
        }]

    @patch("agents.error_correction.agent.detect_subject_via_llm", return_value="高中数学")
    def test_llm_success(self, mock_llm):
        """LLM 返回有效科目时直接采用"""
        ocr = self._make_ocr("普通内容无关键词")
        result = _identify_subject(ocr, [])
        assert result == "高中数学"
        mock_llm.assert_called_once()

    @patch("agents.error_correction.agent.detect_subject_via_llm", return_value="初中地理")
    def test_llm_returns_new_subject(self, mock_llm):
        """LLM 返回不在 db_subjects 中的新科目也应采用"""
        ocr = self._make_ocr("普通内容")
        result = _identify_subject(ocr, ["高中数学"])
        assert result == "初中地理"

    @patch("agents.error_correction.agent.detect_subject_via_llm", return_value="")
    def test_llm_empty_fallback_to_keyword(self, mock_llm):
        """LLM 返回空时应 fallback 到关键词匹配"""
        ocr = self._make_ocr("数学试卷")
        result = _identify_subject(ocr, [])
        assert result == "高中数学"

    @patch(
        "agents.error_correction.agent.detect_subject_via_llm",
        side_effect=Exception("API error"),
    )
    def test_llm_exception_fallback(self, mock_llm):
        """LLM 调用异常时应静默 fallback"""
        ocr = self._make_ocr("物理考试")
        result = _identify_subject(ocr, [])
        assert result == "高中物理"

    @patch("agents.error_correction.agent.detect_subject_via_llm", return_value="高中物理")
    def test_llm_receives_provider(self, mock_llm):
        """model_provider 应正确传递到 LLM 函数"""
        ocr = self._make_ocr("普通内容")
        _identify_subject(ocr, ["高中数学"], model_provider="anthropic")
        _, kwargs = mock_llm.call_args
        assert kwargs.get("provider") == "anthropic"


# ── _merge_pages 测试 ─────────────────────────────────────────


class TestMergePages:
    """PaddleOCRClient._merge_pages 静态方法测试"""

    def test_empty_input(self):
        """空列表应返回空 layoutParsingResults"""
        result = PaddleOCRClient._merge_pages([])
        assert result == {"layoutParsingResults": []}

    def test_single_page(self):
        """单页结果应原样保留"""
        page = {"layoutParsingResults": [{"prunedResult": {"parsing_res_list": [{"block_label": "text"}]}}]}
        result = PaddleOCRClient._merge_pages([page])
        assert len(result["layoutParsingResults"]) == 1

    def test_multi_page_merge(self):
        """多页结果应合并到一个 layoutParsingResults"""
        pages = [
            {"layoutParsingResults": [{"page": 0}]},
            {"layoutParsingResults": [{"page": 1}, {"page": 2}]},
            {"layoutParsingResults": [{"page": 3}]},
        ]
        result = PaddleOCRClient._merge_pages(pages)
        assert len(result["layoutParsingResults"]) == 4

    def test_missing_key_skipped(self):
        """缺少 layoutParsingResults 的页面应被跳过"""
        pages = [
            {"layoutParsingResults": [{"page": 0}]},
            {"other_key": "value"},
        ]
        result = PaddleOCRClient._merge_pages(pages)
        assert len(result["layoutParsingResults"]) == 1


# ── _run_ocr_and_simplify 混合文件类型测试 ────────────────────


class TestRunOcrAndSimplifyFileTypes:
    """_run_ocr_and_simplify 文件类型分发逻辑测试"""

    @staticmethod
    def _make_ocr_result(n_blocks=2):
        """构造一个最小的 OCR 返回结果"""
        return {
            "layoutParsingResults": [{
                "prunedResult": {
                    "parsing_res_list": [
                        {"block_label": "text", "block_content": f"内容{i}", "block_order": i}
                        for i in range(n_blocks)
                    ]
                },
                "markdown": {"text": "test", "images": {}},
                "outputImages": {},
            }]
        }

    @patch("src.workflow.run_async")
    @patch.object(PaddleOCRClient, "parse_pdf")
    @patch.object(PaddleOCRClient, "__init__", return_value=None)
    def test_only_images(self, mock_init, mock_pdf, mock_run_async):
        """纯图片列表应只调用 parse_images_async，不调用 parse_pdf"""
        mock_init.return_value = None
        mock_run_async.return_value = [self._make_ocr_result()]

        result = _run_ocr_and_simplify(["a.png", "b.jpg"])

        mock_pdf.assert_not_called()
        mock_run_async.assert_called_once()
        assert len(result) >= 1

    @patch("src.workflow.run_async")
    @patch.object(PaddleOCRClient, "parse_pdf")
    @patch.object(PaddleOCRClient, "__init__", return_value=None)
    def test_only_pdfs(self, mock_init, mock_pdf, mock_run_async):
        """纯 PDF 列表应只调用 parse_pdf，不调用 parse_images_async"""
        mock_pdf.return_value = self._make_ocr_result()

        result = _run_ocr_and_simplify(["a.pdf", "b.pdf"])

        assert mock_pdf.call_count == 2
        mock_run_async.assert_not_called()
        assert len(result) >= 1

    @patch("src.workflow.run_async")
    @patch.object(PaddleOCRClient, "parse_pdf")
    @patch.object(PaddleOCRClient, "__init__", return_value=None)
    def test_mixed_files(self, mock_init, mock_pdf, mock_run_async):
        """混合文件应分别调用 parse_pdf 和 parse_images_async"""
        mock_pdf.return_value = self._make_ocr_result(3)
        mock_run_async.return_value = [self._make_ocr_result(2)]

        result = _run_ocr_and_simplify(["doc.pdf", "img.png"])

        mock_pdf.assert_called_once()
        mock_run_async.assert_called_once()
        # PDF 3 blocks + 图片 2 blocks = 2 pages
        assert len(result) == 2

    @patch("src.workflow.run_async")
    @patch.object(PaddleOCRClient, "parse_pdf")
    @patch.object(PaddleOCRClient, "__init__", return_value=None)
    def test_pdf_case_insensitive(self, mock_init, mock_pdf, mock_run_async):
        """PDF 扩展名应不区分大小写"""
        mock_pdf.return_value = self._make_ocr_result()

        _run_ocr_and_simplify(["DOC.PDF", "test.Pdf"])

        assert mock_pdf.call_count == 2
        mock_run_async.assert_not_called()

    @patch("src.workflow.run_async")
    @patch.object(PaddleOCRClient, "parse_pdf")
    @patch.object(PaddleOCRClient, "__init__", return_value=None)
    def test_empty_input(self, mock_init, mock_pdf, mock_run_async):
        """空文件列表应返回空结果"""
        result = _run_ocr_and_simplify([])

        mock_pdf.assert_not_called()
        mock_run_async.assert_not_called()
        assert result == []

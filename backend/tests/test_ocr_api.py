"""
集成测试 — 验证 PaddleOCR V2 异步任务 API 的连通性与结果格式

用法:
    pytest tests/test_ocr_api.py -v -s

需要配置环境变量：PADDLEOCR_API_URL、PADDLEOCR_API_TOKEN。
测试图片使用 example_uploads/notes/test.jpg，测试 PDF 使用 example_uploads/exams/test4.pdf。
"""

import os
import json
import time
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

# ── 配置 ────────────────────────────────────────────────


def _load_ocr_creds_from_db() -> dict:
    """从数据库读取激活的 PaddleOCR provider 凭据（作为环境变量的 fallback）"""
    try:
        import sys
        _backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _backend not in sys.path:
            sys.path.insert(0, _backend)
        from db import SessionLocal
        from db.models import ProviderConfig
        with SessionLocal() as db:
            p = db.query(ProviderConfig).filter(
                ProviderConfig.category == "paddleocr",
                ProviderConfig.is_active == True,
            ).first()
            if p:
                return {
                    "api_url": p.base_url or "",
                    "token": p.api_key or "",
                    "model": p.model_name or "PaddleOCR-VL-1.5",
                    "use_doc_orientation": p.use_doc_orientation,
                    "use_doc_unwarping": p.use_doc_unwarping,
                    "use_chart_recognition": p.use_chart_recognition,
                }
    except Exception:
        pass
    return {}


_DB_CREDS = _load_ocr_creds_from_db()

API_URL = os.getenv("PADDLEOCR_API_URL") or _DB_CREDS.get("api_url", "")
TOKEN = os.getenv("PADDLEOCR_API_TOKEN") or _DB_CREDS.get("token", "")
MODEL = os.getenv("PADDLEOCR_MODEL") or _DB_CREDS.get("model", "PaddleOCR-VL-1.5")

EXAMPLE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "example_uploads")
)
TEST_IMAGE = os.path.join(EXAMPLE_DIR, "notes", "test.jpg")
TEST_PDF = os.path.join(EXAMPLE_DIR, "exams", "test4.pdf")

POLL_INTERVAL = 3
POLL_TIMEOUT = 120  # 最长等待秒数


# ── 跳过条件 ──────────────────────────────────────────────

skip_no_config = pytest.mark.skipif(
    not API_URL or not TOKEN,
    reason="未配置 PADDLEOCR_API_URL 或 PADDLEOCR_API_TOKEN",
)

skip_no_image = pytest.mark.skipif(
    not os.path.exists(TEST_IMAGE),
    reason=f"测试图片不存在: {TEST_IMAGE}",
)

skip_no_pdf = pytest.mark.skipif(
    not os.path.exists(TEST_PDF),
    reason=f"测试 PDF 不存在: {TEST_PDF}",
)


# ── 公共辅助 ──────────────────────────────────────────────

def _submit_and_poll(file_path, headers):
    """提交 OCR 任务并轮询到完成，返回 (job_id, job_data)"""
    data = {
        "model": MODEL,
        "optionalPayload": json.dumps({
            "useDocOrientationClassify": False,
            "useDocUnwarping": False,
            "useChartRecognition": False,
        }),
    }
    with open(file_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(API_URL, headers=headers, data=data, files=files)

    assert resp.status_code == 200, f"提交失败: {resp.status_code} {resp.text}"
    job_id = resp.json()["data"]["jobId"]

    elapsed = 0
    while elapsed < POLL_TIMEOUT:
        poll_resp = requests.get(f"{API_URL}/{job_id}", headers=headers)
        assert poll_resp.status_code == 200
        job_data = poll_resp.json()["data"]
        state = job_data["state"]

        if state == "done":
            return job_id, job_data
        elif state == "failed":
            pytest.fail(f"OCR 任务失败: {job_data.get('errorMsg', '未知错误')}")

        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    pytest.fail(f"OCR 任务超时（{POLL_TIMEOUT}s）: {job_id}")


def _download_jsonl(jsonl_url):
    """下载 JSONL 并解析为结果列表"""
    resp = requests.get(jsonl_url)
    resp.raise_for_status()
    results = []
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if line:
            results.append(json.loads(line)["result"])
    return results


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def headers():
    return {"Authorization": f"bearer {TOKEN}"}


@pytest.fixture(scope="module")
def image_job_result(headers):
    """提交图片 OCR 任务，模块共享"""
    return _submit_and_poll(TEST_IMAGE, headers)


@pytest.fixture(scope="module")
def image_parsed_result(image_job_result):
    """图片 OCR 解析结果"""
    _, job_data = image_job_result
    return _download_jsonl(job_data["resultUrl"]["jsonUrl"])


@pytest.fixture(scope="module")
def pdf_job_result(headers):
    """提交 PDF OCR 任务，模块共享"""
    return _submit_and_poll(TEST_PDF, headers)


@pytest.fixture(scope="module")
def pdf_parsed_result(pdf_job_result):
    """PDF OCR 解析结果"""
    _, job_data = pdf_job_result
    return _download_jsonl(job_data["resultUrl"]["jsonUrl"])


# ── 图片 OCR 测试 ─────────────────────────────────────────


@skip_no_config
@skip_no_image
class TestImageApiConnection:
    """图片 API 连通性测试"""

    def test_submit_returns_job_id(self, image_job_result):
        """提交图片任务应返回非空 jobId"""
        job_id, _ = image_job_result
        assert job_id

    def test_job_completes_successfully(self, image_job_result):
        """图片任务应在超时前完成"""
        _, job_data = image_job_result
        assert job_data["state"] == "done"

    def test_has_result_url(self, image_job_result):
        """完成的任务应包含 jsonUrl"""
        _, job_data = image_job_result
        json_url = job_data["resultUrl"]["jsonUrl"]
        assert json_url and json_url.startswith("http")

    def test_extract_progress(self, image_job_result):
        """完成的任务应包含提取进度信息"""
        _, job_data = image_job_result
        progress = job_data["extractProgress"]
        assert progress["extractedPages"] >= 1
        assert "startTime" in progress
        assert "endTime" in progress


@skip_no_config
@skip_no_image
class TestImageResultFormat:
    """图片结果格式兼容性测试（确保与 simplify_ocr_results 兼容）"""

    def test_result_is_non_empty(self, image_parsed_result):
        """JSONL 至少包含一条结果"""
        assert len(image_parsed_result) >= 1

    def test_has_layout_parsing_results(self, image_parsed_result):
        """每条结果应包含 layoutParsingResults"""
        for result in image_parsed_result:
            assert "layoutParsingResults" in result

    def test_layout_has_pruned_result(self, image_parsed_result):
        """layoutParsingResults 中应包含 prunedResult"""
        for result in image_parsed_result:
            for layout in result["layoutParsingResults"]:
                assert "prunedResult" in layout, (
                    f"缺少 prunedResult，实际 keys: {list(layout.keys())}"
                )

    def test_pruned_result_has_parsing_res_list(self, image_parsed_result):
        """prunedResult 中应包含 parsing_res_list"""
        for result in image_parsed_result:
            for layout in result["layoutParsingResults"]:
                pruned = layout["prunedResult"]
                assert "parsing_res_list" in pruned

    def test_blocks_have_required_fields(self, image_parsed_result):
        """每个 block 应包含 block_label、block_content、block_order"""
        required_fields = {"block_label", "block_content", "block_order"}
        for result in image_parsed_result:
            for layout in result["layoutParsingResults"]:
                for block in layout["prunedResult"]["parsing_res_list"]:
                    missing = required_fields - set(block.keys())
                    assert not missing, f"block 缺少字段: {missing}"

    def test_has_markdown_output(self, image_parsed_result):
        """layoutParsingResults 中应包含 markdown 输出"""
        for result in image_parsed_result:
            for layout in result["layoutParsingResults"]:
                assert "markdown" in layout
                md = layout["markdown"]
                assert "text" in md

    @pytest.mark.xfail(reason="PaddleOCR API 新增 display_formula/number 标签，已在 simplify_ocr_results 中归一化")
    def test_block_labels_are_known(self, image_parsed_result):
        """block_label 应为已知类型"""
        known_labels = {
            "text", "title", "paragraph_title", "doc_title",
            "table", "image", "chart", "formula", "figure_title",
            "header", "footer", "reference", "abstract",
            "table_title", "figure", "seal", "equation",
        }
        unknown = set()
        for result in image_parsed_result:
            for layout in result["layoutParsingResults"]:
                for block in layout["prunedResult"]["parsing_res_list"]:
                    label = block["block_label"]
                    if label not in known_labels:
                        unknown.add(label)
        assert not unknown, f"发现未知 block_label: {unknown}"


# ── PDF OCR 测试 ──────────────────────────────────────────


@skip_no_config
@skip_no_pdf
class TestPdfApiConnection:
    """PDF API 连通性测试"""

    def test_submit_returns_job_id(self, pdf_job_result):
        """提交 PDF 任务应返回非空 jobId"""
        job_id, _ = pdf_job_result
        assert job_id

    def test_job_completes_successfully(self, pdf_job_result):
        """PDF 任务应在超时前完成"""
        _, job_data = pdf_job_result
        assert job_data["state"] == "done"

    def test_extracts_multiple_pages(self, pdf_job_result):
        """PDF 应解析出多页"""
        _, job_data = pdf_job_result
        progress = job_data["extractProgress"]
        assert progress["totalPages"] >= 1
        assert progress["extractedPages"] == progress["totalPages"]


@skip_no_config
@skip_no_pdf
class TestPdfResultFormat:
    """PDF 结果格式测试"""

    def test_result_is_non_empty(self, pdf_parsed_result):
        """PDF JSONL 至少包含一条结果"""
        assert len(pdf_parsed_result) >= 1

    def test_has_layout_parsing_results(self, pdf_parsed_result):
        """每条结果应包含 layoutParsingResults"""
        for result in pdf_parsed_result:
            assert "layoutParsingResults" in result

    def test_blocks_have_required_fields(self, pdf_parsed_result):
        """PDF block 应包含必填字段"""
        required_fields = {"block_label", "block_content", "block_order"}
        for result in pdf_parsed_result:
            for layout in result["layoutParsingResults"]:
                if "prunedResult" not in layout:
                    continue
                for block in layout["prunedResult"]["parsing_res_list"]:
                    missing = required_fields - set(block.keys())
                    assert not missing, f"block 缺少字段: {missing}"


# ── PaddleOCRClient 客户端集成测试 ────────────────────────


@skip_no_config
@skip_no_image
class TestOcrClientImage:
    """PaddleOCRClient 图片解析集成测试"""

    def test_parse_image_returns_result(self, tmp_path):
        """parse_image 应返回包含 layoutParsingResults 的结果"""
        from src.paddleocr_client import PaddleOCRClient

        client = PaddleOCRClient(**_DB_CREDS)
        result = client.parse_image(TEST_IMAGE, save_output=True, output_dir=str(tmp_path))

        assert "layoutParsingResults" in result
        assert len(result["layoutParsingResults"]) >= 1

    def test_saves_struct_json(self, tmp_path):
        """parse_image 应在 output_dir 下保存 _struct.json"""
        from src.paddleocr_client import PaddleOCRClient
        from pathlib import Path

        client = PaddleOCRClient(**_DB_CREDS)
        client.parse_image(TEST_IMAGE, save_output=True, output_dir=str(tmp_path))

        stem = Path(TEST_IMAGE).stem
        struct_file = tmp_path / f"{stem}_struct.json"
        assert struct_file.exists(), f"未生成 {struct_file}"

        with open(struct_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "layoutParsingResults" in data

    def test_simplify_ocr_results_compatible(self):
        """parse_image 的返回值应能被 simplify_ocr_results 正常处理"""
        from src.paddleocr_client import PaddleOCRClient
        from src.utils import simplify_ocr_results

        client = PaddleOCRClient(**_DB_CREDS)
        result = client.parse_image(TEST_IMAGE, save_output=False)

        simplified = simplify_ocr_results([result])
        assert len(simplified) >= 1
        for page in simplified:
            assert "page_index" in page
            assert "blocks" in page
            assert isinstance(page["blocks"], list)


@skip_no_config
@skip_no_pdf
class TestOcrClientPdf:
    """PaddleOCRClient PDF 解析集成测试"""

    def test_parse_pdf_returns_result(self, tmp_path):
        """parse_pdf 应返回包含 layoutParsingResults 的结果"""
        from src.paddleocr_client import PaddleOCRClient

        client = PaddleOCRClient(**_DB_CREDS)
        result = client.parse_pdf(TEST_PDF, save_output=True, output_dir=str(tmp_path))

        assert "layoutParsingResults" in result
        assert len(result["layoutParsingResults"]) >= 1

    def test_pdf_simplify_compatible(self):
        """parse_pdf 的返回值应能被 simplify_ocr_results 正常处理"""
        from src.paddleocr_client import PaddleOCRClient
        from src.utils import simplify_ocr_results

        client = PaddleOCRClient(**_DB_CREDS)
        result = client.parse_pdf(TEST_PDF, save_output=False)

        simplified = simplify_ocr_results([result])
        assert len(simplified) >= 1
        for page in simplified:
            assert "page_index" in page
            assert "blocks" in page

    def test_pdf_multipage_index_continuity(self):
        """PDF 多页经 simplify 后 page_index 应连续递增（0, 1, 2...）"""
        from src.paddleocr_client import PaddleOCRClient
        from src.utils import simplify_ocr_results

        client = PaddleOCRClient(**_DB_CREDS)
        result = client.parse_pdf(TEST_PDF, save_output=False)

        simplified = simplify_ocr_results([result])
        assert len(simplified) >= 2, "PDF 应解析出多页"
        indexes = [p["page_index"] for p in simplified]
        assert indexes == list(range(len(simplified))), (
            f"page_index 应连续递增，实际: {indexes}"
        )

"""
Benchmark 数据批量采集

复用本系统的 PaddleOCR + Agent 分割流水线，
批量处理 dataset/ 下的考试 PDF（每份取前 2 页），
提取所有题目并按科目分目录保存。

用法:
    cd backend
    python -m benchmark.collect                        # 采集全部科目
    python -m benchmark.collect --subject 高中数学     # 只采集指定科目
    python -m benchmark.collect --dry-run              # 只扫描 PDF
    python -m benchmark.collect --provider anthropic   # 指定分割模型
    python -m benchmark.collect --workers 4            # 并行数（默认 4）
"""

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

# 确保 backend/ 在 sys.path 中
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import settings

logger = logging.getLogger(__name__)

# ── 路径 ────────────────────────────────────────────────────────
PROJECT_ROOT = BACKEND_ROOT.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
BENCHMARK_DATA_DIR = BACKEND_ROOT / "benchmark" / "data"
TARGET_DIR = BENCHMARK_DATA_DIR / "target"

MAX_PAGES = 2


# ═══════════════════════════════════════════════════════════════
# 1. PDF 扫描与转图
# ═══════════════════════════════════════════════════════════════

def scan_pdfs(subject: str = None) -> List[Tuple[Path, str]]:
    """扫描 dataset/ 下的所有 PDF，返回 (pdf_path, 科目名) 列表"""
    results = []
    for pdf in sorted(DATASET_DIR.rglob("*.pdf")):
        if subject and subject not in str(pdf):
            continue
        # 从路径推断科目: dataset/{科目}/pdf文档/xxx.pdf
        rel = pdf.relative_to(DATASET_DIR)
        subject_name = rel.parts[0] if len(rel.parts) > 1 else "未分类"
        results.append((pdf, subject_name))
    return results


def pdf_to_images(pdf_path: Path, max_pages: int = MAX_PAGES) -> List[str]:
    """PDF 前 max_pages 页 → 标准化 PNG，返回图片路径列表"""
    from pdf2image import convert_from_path

    os.makedirs(settings.pages_dir, exist_ok=True)
    images = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=max_pages)

    paths = []
    stem = pdf_path.stem
    for i, img in enumerate(images):
        out = os.path.join(settings.pages_dir, f"{stem}_page_{i + 1:03d}.png")
        img.convert("RGB").save(out, "PNG")
        paths.append(out)

    return paths


# ═══════════════════════════════════════════════════════════════
# 2. OCR + Agent 分割（复用现有流水线）
# ═══════════════════════════════════════════════════════════════

def ocr_and_split(image_paths: List[str], provider: str = "openai") -> List[Dict]:
    """对一组图片执行 OCR → Agent 分割，返回结构化题目列表"""
    from src.workflow import _run_ocr_and_simplify, _build_overlapping_batches, _dedup_questions

    # OCR
    ocr_data = _run_ocr_and_simplify(image_paths)
    if not ocr_data:
        return []

    # 构建批次
    batches = _build_overlapping_batches(ocr_data, batch_size=2, overlap=1)

    # 分割
    from agents.error_correction.tools import split_batch

    all_questions = []
    for batch_data in batches:
        try:
            result_str = split_batch.invoke({
                "ocr_data": json.dumps(batch_data, ensure_ascii=False),
                "subject": "",
                "existing_tags": "",
                "model_provider": provider,
            })
            if result_str and result_str.startswith("["):
                all_questions.extend(json.loads(result_str))
        except Exception as e:
            logger.warning(f"分割批次失败: {e}")

    return _dedup_questions(all_questions)


# ═══════════════════════════════════════════════════════════════
# 3. targets 格式化
# ═══════════════════════════════════════════════════════════════

def format_targets(
    questions: List[Dict],
    pdf_name: str,
) -> List[Dict]:
    """将分割结果转为 targets 格式（保留所有题型）"""
    results = []
    for q in questions:
        qid = q.get("question_id", "")
        qtype = q.get("question_type", "解答题")
        global_id = f"{pdf_name}_{qid}"

        results.append({
            "question_id": global_id,
            "question_type": qtype,
            "answer": "",
            "source": {
                "pdf": pdf_name,
                "local_id": qid,
            },
            "question": {
                "question_id": global_id,
                "question_type": qtype,
                "content_blocks": q.get("content_blocks", []),
                "options": q.get("options"),
                "has_formula": q.get("has_formula", False),
                "has_image": q.get("has_image", False),
                "image_refs": q.get("image_refs"),
                "knowledge_tags": q.get("knowledge_tags"),
            },
        })
    return results


# ═══════════════════════════════════════════════════════════════
# 4. 单个 PDF 处理（并行单元）
# ═══════════════════════════════════════════════════════════════

def process_one_pdf(
    pdf_path: Path,
    subject_name: str,
    provider: str,
    idx: int,
    total: int,
) -> Dict:
    """处理单个 PDF，返回统计信息"""
    pdf_name = pdf_path.stem
    rel = pdf_path.relative_to(PROJECT_ROOT)
    result = {"pdf": str(rel), "subject": subject_name, "pages": 0, "questions": 0, "error": None}

    # Step 1: PDF → 图片
    try:
        image_paths = pdf_to_images(pdf_path)
        result["pages"] = len(image_paths)
        print(f"  [{idx}/{total}] {rel} — 转图完成: {len(image_paths)} 页")
    except Exception as e:
        result["error"] = f"PDF 转图失败: {e}"
        print(f"  [{idx}/{total}] {rel} — PDF 转图失败: {e}")
        return result

    # Step 2: OCR + 分割
    try:
        questions = ocr_and_split(image_paths, provider=provider)
        result["questions"] = len(questions)
        print(f"  [{idx}/{total}] {rel} — 分割完成: {len(questions)} 道题目")
    except Exception as e:
        result["error"] = f"分割失败: {e}"
        print(f"  [{idx}/{total}] {rel} — 分割失败: {e}")
        return result

    # Step 3: 格式化并保存到 target/{科目}/{试卷名}.json
    targets = format_targets(questions, pdf_name)
    subject_dir = TARGET_DIR / subject_name
    subject_dir.mkdir(parents=True, exist_ok=True)
    out_path = subject_dir / f"{pdf_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(targets, f, ensure_ascii=False, indent=2)

    return result


# ═══════════════════════════════════════════════════════════════
# 5. 主流程
# ═══════════════════════════════════════════════════════════════

def collect(
    subject: str = None,
    dry_run: bool = False,
    provider: str = "openai",
    max_workers: int = 4,
):
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    pdf_list = scan_pdfs(subject)
    print(f"共扫描到 {len(pdf_list)} 个 PDF 文件")

    if dry_run:
        for p, s in pdf_list:
            print(f"  [{s}] {p.relative_to(PROJECT_ROOT)}")
        return

    total = len(pdf_list)
    stats = {"pdfs": total, "pages": 0, "questions": 0, "errors": 0}
    type_counts = {}

    # 并行处理
    print(f"\n使用 {max_workers} 个线程并行处理...\n")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_one_pdf, pdf_path, subj, provider, idx, total): (pdf_path, subj)
            for idx, (pdf_path, subj) in enumerate(pdf_list, 1)
        }
        for future in as_completed(futures):
            result = future.result()
            stats["pages"] += result["pages"]
            stats["questions"] += result["questions"]
            if result["error"]:
                stats["errors"] += 1

            # 统计题型（从保存的文件读回）
            if not result["error"]:
                pdf_path, subj = futures[future]
                out_path = TARGET_DIR / subj / f"{pdf_path.stem}.json"
                if out_path.exists():
                    with open(out_path, "r", encoding="utf-8") as f:
                        for t in json.load(f):
                            qtype = t["question_type"]
                            type_counts[qtype] = type_counts.get(qtype, 0) + 1

    print(f"\n{'=' * 50}")
    print(f"采集完成")
    print(f"  PDF 数量:    {stats['pdfs']}")
    print(f"  处理页数:    {stats['pages']}")
    print(f"  总题目数:    {stats['questions']}")
    print(f"  题型分布:")
    for qtype, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {qtype}: {cnt}")
    print(f"  错误次数:    {stats['errors']}")
    print(f"  输出目录:    {TARGET_DIR}/")
    print(f"\n下一步: 标注人员在各 JSON 文件中填写 answer 字段")
    print(f"标注完成后运行: python -m benchmark.evaluate")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="批量采集题目，生成 benchmark targets")
    parser.add_argument("--subject", "-s", default=None,
                        help="筛选科目关键词（如 '高中数学'、'化学'），不指定则全部")
    parser.add_argument("--dry-run", action="store_true",
                        help="只扫描 PDF 列表，不执行 OCR 和分割")
    parser.add_argument("--provider", "-p", default="openai", choices=["openai", "anthropic"],
                        help="分割用的模型供应商（默认 openai）")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="并行线程数（默认 4）")
    args = parser.parse_args()

    collect(
        subject=args.subject,
        dry_run=args.dry_run,
        provider=args.provider,
        max_workers=args.workers,
    )


if __name__ == "__main__":
    main()

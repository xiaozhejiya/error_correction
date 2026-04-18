"""
笔记整理 Agent — 将 OCR 文本整理为结构化 Markdown 笔记

支持：
  - 重试机制（指数退避，最多 3 次）
  - 多页分批处理（超过阈值时分批整理再合并）
"""

import logging
import time

from langchain_core.messages import SystemMessage, HumanMessage

from core.config import settings
from core.llm import init_model
from .prompts import NOTE_ORGANIZE_PROMPT
from .schemas import OrganizedNote

logger = logging.getLogger(__name__)

# 单次 LLM 调用的文本长度上限（字符数），超过则分批
BATCH_CHAR_LIMIT = 6000
MAX_RETRIES = 3


def _invoke_once(model, ocr_text: str) -> OrganizedNote:
    """单次 LLM 调用，返回结构化笔记"""
    structured_model = model.with_structured_output(OrganizedNote, method="function_calling")
    return structured_model.invoke([
        SystemMessage(content=NOTE_ORGANIZE_PROMPT),
        HumanMessage(content=f"以下是 OCR 识别出的课堂笔记原始文本，请整理为结构化笔记：\n\n{ocr_text}"),
    ])


def _invoke_with_retry(model, ocr_text: str) -> OrganizedNote:
    """带指数退避的重试调用"""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = _invoke_once(model, ocr_text)
            if result:
                return result
            last_error = "LLM 未返回有效结果"
        except Exception as e:
            last_error = str(e)
            logger.warning(f"笔记整理: 第 {attempt}/{MAX_RETRIES} 次失败: {last_error}")

        if attempt < MAX_RETRIES:
            wait = 2 ** attempt  # 2s, 4s
            logger.info(f"笔记整理: {wait}s 后重试...")
            time.sleep(wait)

    raise RuntimeError(f"笔记整理失败（重试 {MAX_RETRIES} 次）: {last_error}")


def _split_text_into_batches(text: str) -> list:
    """按行将文本拆分为多个批次，每批不超过 BATCH_CHAR_LIMIT 字符"""
    lines = text.split('\n')
    batches = []
    current = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > BATCH_CHAR_LIMIT and current:
            batches.append('\n'.join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + 1

    if current:
        batches.append('\n'.join(current))
    return batches


def _merge_notes(notes: list) -> OrganizedNote:
    """合并多批次的笔记结果"""
    # 用第一批的标题和科目
    title = notes[0].title
    subject = notes[0].subject

    # 合并 Markdown 内容
    all_markdown = '\n\n'.join(n.content_markdown for n in notes)

    # 合并去重标签
    all_tags = []
    seen = set()
    for n in notes:
        for tag in n.knowledge_tags:
            if tag not in seen:
                all_tags.append(tag)
                seen.add(tag)

    return OrganizedNote(
        title=title,
        subject=subject,
        content_markdown=all_markdown,
        knowledge_tags=all_tags[:5],  # 最多 5 个
    )


def invoke_note_organize(
    ocr_text: str,
    provider: str = "openai",
    model_name: str = None,
) -> OrganizedNote:
    """调用 LLM 将 OCR 文本整理为结构化笔记

    文本较短时直接整理，较长时分批处理再合并。
    每次调用带 3 次重试（指数退避）。

    Args:
        ocr_text: OCR 识别出的原始文本
        provider: 模型供应商
        model_name: 指定模型名称，None 使用默认

    Returns:
        OrganizedNote 结构化结果
    """
    model = init_model(temperature=0.3, provider=provider, model_name=model_name)

    # 短文本：直接整理
    if len(ocr_text) <= BATCH_CHAR_LIMIT:
        return _invoke_with_retry(model, ocr_text)

    # 长文本：分批处理
    batches = _split_text_into_batches(ocr_text)
    logger.info(f"笔记文本较长（{len(ocr_text)} 字符），分 {len(batches)} 批处理")

    results = []
    for i, batch in enumerate(batches):
        logger.info(f"处理第 {i + 1}/{len(batches)} 批（{len(batch)} 字符）")
        result = _invoke_with_retry(model, batch)
        results.append(result)

    return _merge_notes(results)

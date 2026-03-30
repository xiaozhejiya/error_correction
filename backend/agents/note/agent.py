"""
笔记整理 Agent — 将 OCR 文本整理为结构化 Markdown 笔记
"""

import logging

from langchain_core.messages import SystemMessage, HumanMessage

from core.config import settings
from core.llm import init_model
from .prompts import NOTE_ORGANIZE_PROMPT
from .schemas import OrganizedNote

logger = logging.getLogger(__name__)


def invoke_note_organize(
    ocr_text: str,
    provider: str = "openai",
    model_name: str = None,
) -> OrganizedNote:
    """调用 LLM 将 OCR 文本整理为结构化笔记

    Args:
        ocr_text: OCR 识别出的原始文本
        provider: 模型供应商
        model_name: 指定模型名称，None 使用默认

    Returns:
        OrganizedNote 结构化结果（title、subject、content_markdown、knowledge_tags）
    """
    model = init_model(temperature=0.3, provider=provider, model_name=model_name)

    # 使用 function_calling 方式实现结构化输出
    # DeepSeek 等 OpenAI 兼容 API 不支持 response_format（JSON Schema），
    # 但支持 function calling，所以显式指定 method="function_calling"
    structured_model = model.with_structured_output(OrganizedNote, method="function_calling")

    result = structured_model.invoke([
        SystemMessage(content=NOTE_ORGANIZE_PROMPT),
        HumanMessage(content=f"以下是 OCR 识别出的课堂笔记原始文本，请整理为结构化笔记：\n\n{ocr_text}"),
    ])

    return result

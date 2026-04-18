"""
教学辅导智能体 — 流式多轮对话
"""

import logging
from typing import Generator, List, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from core.llm import init_model
from .prompts import build_teach_prompt

logger = logging.getLogger(__name__)


def _build_question_text(question: Dict[str, Any]) -> str:
    """从 Question ORM 序列化数据中提取题目文本"""
    parts = []

    q_type = question.get("question_type", "")
    if q_type:
        parts.append(f"【{q_type}】")

    content_json = question.get("content_json")
    if isinstance(content_json, list):
        for block in content_json:
            if block.get("block_type") == "text":
                parts.append(block.get("content", ""))
            elif block.get("block_type") == "image":
                parts.append(f"[图片: {block.get('content', '')}]")

    options_json = question.get("options_json")
    if isinstance(options_json, list):
        for opt in options_json:
            parts.append(opt)

    return "\n".join(parts)


GENERAL_SYSTEM_PROMPT = """你是一位专业的学习辅导助手，擅长数学、物理、化学、英语等学科。
请用清晰、有条理的方式回答学生的问题。
如果涉及数学公式，使用 LaTeX 标记（行内 $...$，独占行 $$...$$）。
回答要准确、简洁，适合中学生和大学生理解。"""


def stream_teach(
    *,
    question: Dict[str, Any] = None,
    messages: List[Dict[str, str]],
    provider: str = "openai",
    model_name: str | None = None,
) -> Generator[str, None, None]:
    """流式教学对话

    Args:
        question: 题目数据（可选，None 为独立对话）
        messages: 对话历史 [{"role": "user"|"assistant", "content": "..."}]
        provider: 模型供应商
        model_name: 指定模型名称，为 None 时使用 provider 默认模型

    Yields:
        逐 token 的文本片段
    """
    if question:
        subject = question.get("subject") or "未知科目"
        knowledge_tags = question.get("knowledge_tags") or []
        answer_text = question.get("answer") or "暂无答案"
        question_text = _build_question_text(question)

        system_prompt = build_teach_prompt(
            subject=subject,
            knowledge_tags=knowledge_tags,
            question_text=question_text,
            answer_text=answer_text,
        )
    else:
        system_prompt = GENERAL_SYSTEM_PROMPT

    # 构建 LangChain 消息列表
    lc_messages = [SystemMessage(content=system_prompt)]
    for msg in messages:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    model = init_model(temperature=0.4, provider=provider, model_name=model_name)

    for chunk in model.stream(lc_messages):
        # DeepSeek reasoner 模型会在 additional_kwargs 里返回 reasoning_content
        reasoning = None
        if hasattr(chunk, 'additional_kwargs'):
            reasoning = chunk.additional_kwargs.get('reasoning_content')

        token = chunk.content
        # 安全处理：确保 token 是字符串（某些模型返回 list）
        if isinstance(token, list):
            token = ''.join(str(t) for t in token if t)
        if reasoning and isinstance(reasoning, str):
            yield {"type": "reasoning", "content": reasoning}
        if token and isinstance(token, str):
            yield {"type": "content", "content": token}

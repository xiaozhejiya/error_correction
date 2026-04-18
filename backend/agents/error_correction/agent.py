"""
错题本智能体工厂
- 内层：create_agent (langchain) + ToolStrategy — 结构化输出题目分割结果
"""

import logging
import threading
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import SystemMessage, HumanMessage

from core.config import settings
from core.llm import init_model as _init_model
from .prompts import SPLIT_PROMPT, SPLIT_PROMPT_LITE, CORRECTION_PROMPT
from .schemas import QuestionSplitResult, CorrectionResult

logger = logging.getLogger(__name__)

# Agent 实例缓存（避免每次调用重复初始化模型和编译图）
_agent_cache = {}
_agent_cache_lock = threading.Lock()


def detect_subject_via_llm(ocr_text_sample: str, db_subjects: list, provider: str = "openai") -> str:
    """通过轻量 LLM 识别试卷科目

    Args:
        ocr_text_sample: 前几页 OCR 文本拼接
        db_subjects: 数据库已有科目列表
        provider: 模型供应商

    Returns:
        识别出的科目名称，失败时返回空字符串
    """
    model = _init_model(temperature=0.0, provider=provider, use_light=True)

    existing = '、'.join(db_subjects) if db_subjects else '无'
    prompt = (
        f'已有科目列表：{existing}\n\n'
        f'以下是一份试卷的 OCR 文字节选：\n{ocr_text_sample[:1500]}\n\n'
        '判断试卷科目，输出格式【学段+科目】。'
        '学段：小学/初中/高中/大学；未标注学段不默认，直接用"未知学段"。'
        '科目可能包含大学课程（如高等数学、线性代数、概率论、大学物理、数据结构等）。'
        '只输出结果，不要引号/解释/换行；无法判断输出"未知"。'
    )

    response = model.invoke([HumanMessage(content=prompt)])
    result = response.content.strip()

    if not result or '未知' in result:
        return ""

    return result


def create_inner_split_agent(provider: str = "openai", model_name: str | None = None):
    """创建内层题目分割智能体

    使用 create_agent + ToolStrategy，保证结构化输出。
    无外部工具，专注于将 OCR 数据分割为 QuestionSplitResult。

    由 split_batch 工具内部调用。

    Args:
        provider: 模型供应商，"openai" 或 "anthropic"
        model_name: 指定模型名称，为 None 时使用 provider 默认模型

    Returns:
        create_agent 返回的 CompiledStateGraph
    """
    model = _init_model(temperature=0.1, provider=provider, model_name=model_name)

    return create_agent(
        model=model,
        tools=[],
        system_prompt=SPLIT_PROMPT,
        response_format=ToolStrategy(
            schema=QuestionSplitResult,
            handle_errors=True,
        ),
    )


def create_correction_agent(provider: str = "openai", model_name: str | None = None):
    """创建内层 OCR 纠错智能体

    使用 create_agent + ToolStrategy，保证结构化输出。
    无外部工具，专注于修复 OCR 错误并输出 CorrectionResult。

    由 correct_batch 工具内部调用。

    Args:
        provider: 模型供应商，"openai" 或 "anthropic"
        model_name: 指定模型名称，为 None 时使用 provider 默认模型

    Returns:
        create_agent 返回的 CompiledStateGraph
    """
    model = _init_model(temperature=0.0, provider=provider, model_name=model_name)

    return create_agent(
        model=model,
        tools=[],
        system_prompt=CORRECTION_PROMPT,
        response_format=ToolStrategy(
            schema=CorrectionResult,
            handle_errors=True,
        ),
    )


def _invoke_structured(
    *,
    prompt: str,
    provider: str,
    model_name: str | None,
    temperature: float,
    schema,
    system_prompt_fallback: str,
    cache_key: str,
    agent_factory,
):
    """通用结构化输出调用，屏蔽 ToolStrategy vs with_structured_output 差异"""
    cfg = settings.get_provider(provider)

    if not cfg.supports_function_calling:
        model = _init_model(temperature=temperature, provider=provider, model_name=model_name)
        return model.with_structured_output(schema).invoke([
            SystemMessage(content=system_prompt_fallback),
            HumanMessage(content=prompt),
        ])

    full_key = f"{cache_key}_{provider}_{model_name or 'default'}"
    with _agent_cache_lock:
        if full_key not in _agent_cache:
            logger.info(f"创建 Agent 实例 (key={full_key})")
            _agent_cache[full_key] = agent_factory(provider=provider, model_name=model_name)
        agent = _agent_cache[full_key]
    response = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"recursion_limit": 100},
    )
    return response.get("structured_response")


def invoke_split(prompt: str, provider: str = "openai", model_name: str | None = None):
    """统一调用分割，屏蔽 ToolStrategy vs with_structured_output 差异"""
    return _invoke_structured(
        prompt=prompt, provider=provider, model_name=model_name,
        temperature=0.1, schema=QuestionSplitResult,
        system_prompt_fallback=SPLIT_PROMPT_LITE,
        cache_key="split", agent_factory=create_inner_split_agent,
    )


def invoke_correction(prompt: str, provider: str = "openai", model_name: str | None = None):
    """统一调用纠错，屏蔽 ToolStrategy vs with_structured_output 差异"""
    return _invoke_structured(
        prompt=prompt, provider=provider, model_name=model_name,
        temperature=0.0, schema=CorrectionResult,
        system_prompt_fallback=CORRECTION_PROMPT,
        cache_key="correction", agent_factory=create_correction_agent,
    )

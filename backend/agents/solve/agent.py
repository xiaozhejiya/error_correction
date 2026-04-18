"""
解题智能体

调用 LLM 对结构化题目进行解答，返回结构化解题结果。
"""

import json
import time
import logging
from typing import List, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from core.llm import init_model
from .prompts import SOLVE_PROMPT
from .schemas import SolveBatchResult

logger = logging.getLogger(__name__)


def invoke_solve(questions: List[Dict[str, Any]], provider: str = "openai", max_retries: int = 3) -> SolveBatchResult:
    """对一批题目进行解答

    Args:
        questions: 题目列表（Question schema 格式的 dict）
        provider: 模型供应商，"openai" 或 "anthropic"
        max_retries: 最大重试次数

    Returns:
        SolveBatchResult 结构化解题结果
    """
    if not questions:
        return SolveBatchResult(results=[])

    model = init_model(temperature=0.0, provider=provider)
    structured_model = model.with_structured_output(SolveBatchResult)

    prompt = f"""请解答以下题目，返回每道题的答案和解题过程。

题目数据：
{json.dumps(questions, ensure_ascii=False, indent=2)}"""

    messages = [
        SystemMessage(content=SOLVE_PROMPT),
        HumanMessage(content=prompt),
    ]

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            result = structured_model.invoke(messages)
            logger.info(f"invoke_solve done: {len(result.results)} answers (provider={provider})")
            return result
        except Exception as e:
            last_error = e
            logger.warning(f"invoke_solve: 第 {attempt}/{max_retries} 次失败: {e}")
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info(f"invoke_solve: 等待 {wait}s 后重试...")
                time.sleep(wait)

    raise last_error

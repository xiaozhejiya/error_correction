"""
解题结果结构化输出 Schema
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SolveResult(BaseModel):
    """单道题目的解题结果"""
    question_id: str = Field(description="题号")
    answer: str = Field(description="最终答案（选择题填选项字母，填空题填答案，解答题填完整解答过程）")
    reasoning: str = Field(description="解题思路与推理过程")
    confidence: float = Field(default=1.0, description="置信度 0-1，1 表示非常确定")


class SolveBatchResult(BaseModel):
    """批量解题结果"""
    results: List[SolveResult] = Field(description="解题结果列表")

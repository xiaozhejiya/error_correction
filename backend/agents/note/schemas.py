"""
笔记整理结构化输出 Schema
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class OrganizedNote(BaseModel):
    """LLM 整理后的笔记结构"""
    title: str = Field(description="笔记标题，根据内容自动生成，简洁明确")
    subject: str = Field(description="科目，如 '高中数学'、'初中物理'，无法判断则输出 '未知'")
    content_markdown: str = Field(description="整理后的 Markdown 格式笔记内容，包含知识点归纳、公式、要点等")
    knowledge_tags: List[str] = Field(description="知识点标签列表（2-5 个），如 ['三角函数', '诱导公式']")

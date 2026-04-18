"""
题目分割结构化输出 Schema
使用 Pydantic 模型定义，配合 LangChain ToolStrategy 实现结构化输出
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    """题目内容块"""
    block_type: Literal["text", "image"] = Field(description="内容类型：text 或 image")
    content: str = Field(description="文本内容（公式用 LaTeX 标记：行内 $...$，独占行 $$...$$）或图片路径")


class Question(BaseModel):
    """单道题目"""
    question_id: str = Field(description="题号，如 '1', '2', '(1)' 等")
    section_title: Optional[str] = Field(default=None, description="该题所属的大题标题，即题目之前最近出现的 paragraph_title block 的文字，如'四、我会计算。'；若试卷无大题结构则为 null")
    question_type: Literal["选择题", "填空题", "解答题", "判断题"] = Field(description="题目类型")
    content_blocks: List[ContentBlock] = Field(description="题干内容块列表（不含选项）")
    options: Optional[List[str]] = Field(default=None, description="选项列表，仅选择题需要，如 ['A. xxx', 'B. yyy']")
    option_images: Optional[List[str]] = Field(default=None, description="选项对应的图片路径列表，与 options 按索引一一对应；无图片的选项填 null 或空字符串")
    has_formula: bool = Field(default=False, description="是否包含数学公式")
    has_image: bool = Field(default=False, description="是否包含图片")
    image_refs: Optional[List[str]] = Field(default=None, description="图片引用路径列表")
    knowledge_tags: Optional[List[str]] = Field(default=None, description="知识点标签列表，如 ['三角函数', '诱导公式']")
    needs_correction: bool = Field(default=False, description="是否疑似存在OCR错误（乱码、公式残缺等），需要后续纠错")
    ocr_issues: Optional[List[str]] = Field(default=None, description="疑似OCR错误描述列表，如 ['公式断裂: 缺少闭合括号']")


class QuestionSplitResult(BaseModel):
    """题目分割结果"""
    questions: List[Question] = Field(description="分割后的题目列表")


class CorrectedQuestion(BaseModel):
    """纠错后的单道题目"""
    question_id: str = Field(description="题号")
    section_title: Optional[str] = Field(default=None, description="所属大题标题，透传自分割结果，不需要修改")
    question_type: Literal["选择题", "填空题", "解答题", "判断题"] = Field(description="题目类型")
    content_blocks: List[ContentBlock] = Field(description="纠错后的题干内容块列表")
    options: Optional[List[str]] = Field(default=None, description="纠错后的选项列表")
    option_images: Optional[List[str]] = Field(default=None, description="选项对应的图片路径列表，与 options 按索引一一对应")
    has_formula: bool = Field(default=False, description="是否包含数学公式")
    has_image: bool = Field(default=False, description="是否包含图片")
    image_refs: Optional[List[str]] = Field(default=None, description="图片引用路径列表")
    knowledge_tags: Optional[List[str]] = Field(default=None, description="知识点标签列表")
    corrections_applied: List[str] = Field(description="已应用的纠错操作列表，如 ['修复断裂公式', '替换乱码字符']")


class CorrectionResult(BaseModel):
    """纠错结果"""
    corrected_questions: List[CorrectedQuestion] = Field(description="纠错后的题目列表")

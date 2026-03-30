"""
数据库 ORM 模型定义
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="user")
    upload_batches = relationship("UploadBatch", back_populates="user")
    split_records = relationship("SplitRecord", back_populates="user")
    provider_configs = relationship("ProviderConfig", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user")


class ProviderConfig(Base):
    """用户级 API 供应商配置（每用户可配置多个，同类激活一个）"""
    __tablename__ = "provider_configs"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String(20), nullable=False)  # 'openai' | 'anthropic' | 'paddleocr'
    name = Column(String(100), default="")
    is_active = Column(Boolean, default=False)
    api_key = Column(Text, default="")  # 加密存储（后续）
    base_url = Column(Text, default="")
    model_name = Column(String(100), default="")
    light_model_name = Column(String(100), default="")
    supports_function_calling = Column(Boolean, default=True)
    # PaddleOCR 专用
    use_doc_orientation = Column(Boolean, default=False)
    use_doc_unwarping = Column(Boolean, default=False)
    use_chart_recognition = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="provider_configs")


class UploadBatch(Base):
    """上传批次表"""
    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    original_filename = Column(String(255), nullable=False)
    subject = Column(String(50))
    file_path = Column(Text)
    upload_time = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="upload_batches")
    questions = relationship("Question", back_populates="batch")


class Question(Base):
    """题目表"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"))
    content_hash = Column(String(64), nullable=False)
    question_type = Column(String(20))
    content_json = Column(Text)
    options_json = Column(Text)
    has_formula = Column(Boolean, default=False)
    has_image = Column(Boolean, default=False)
    image_refs_json = Column(Text)
    needs_correction = Column(Boolean, default=False)
    ocr_issues_json = Column(Text)
    user_answer = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    review_status = Column(String(10), nullable=True, default='待复习', index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    answer = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint('content_hash', 'user_id', name='uq_question_hash_user'),
    )

    user = relationship("User", back_populates="questions")
    batch = relationship("UploadBatch", back_populates="questions")
    tags = relationship("QuestionTagMapping", back_populates="question")
    chat_sessions = relationship("ChatSession", back_populates="question")


class ChatSession(Base):
    """教学辅导对话会话"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    question = relationship("Question", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.id")


class ChatMessage(Base):
    """对话消息"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class SplitRecord(Base):
    """分割历史记录表"""
    __tablename__ = "split_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    subject = Column(String(50))
    model_provider = Column(String(20))
    file_names_json = Column(Text)
    questions_json = Column(Text)
    question_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="split_records")


class KnowledgeTag(Base):
    """知识点标签表"""
    __tablename__ = "knowledge_tags"

    id = Column(Integer, primary_key=True)
    tag_name = Column(String(50), nullable=False)
    subject = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tag_name", "subject", name="uq_tag_subject"),
    )


class QuestionTagMapping(Base):
    """题目-标签关联表"""
    __tablename__ = "question_tag_mapping"

    question_id = Column(Integer, ForeignKey("questions.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("knowledge_tags.id"), primary_key=True)

    question = relationship("Question", back_populates="tags")
    tag = relationship("KnowledgeTag")


class Note(Base):
    """笔记表"""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)          # 笔记标题
    subject = Column(String(50))                          # 科目
    content_markdown = Column(Text, default="")           # LLM 整理后的 Markdown 内容
    source_images_json = Column(Text)                     # 原始上传图片路径列表 JSON
    ocr_text = Column(Text)                               # OCR 识别的原始文本（保留用于重新整理）
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notes")
    tags = relationship("NoteTagMapping", back_populates="note", cascade="all, delete-orphan")


class NoteTagMapping(Base):
    """笔记-标签关联表（与错题共享 KnowledgeTag）"""
    __tablename__ = "note_tag_mapping"

    note_id = Column(Integer, ForeignKey("notes.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("knowledge_tags.id"), primary_key=True)

    note = relationship("Note", back_populates="tags")
    tag = relationship("KnowledgeTag")

"""
数据库 ORM 模型定义
"""

import uuid
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
    display_name = Column(String(50), nullable=True)
    nickname = Column(String(50), nullable=True)
    avatar_path = Column(Text, nullable=True)
    avatar_url = Column(Text, nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    session_version = Column(Integer, default=0, nullable=False)
    daily_free_quota = Column(Integer, default=5, nullable=False)
    daily_free_used = Column(Integer, default=0, nullable=False)
    daily_free_quota_date = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="user")
    upload_batches = relationship("UploadBatch", back_populates="user")
    split_records = relationship("SplitRecord", back_populates="user")
    provider_configs = relationship("ProviderConfig", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user")
    workflow_runs = relationship("WorkflowRun", back_populates="user")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    """Learning space that groups questions and notes."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    project_type = Column(String(20), default="question", nullable=False, index=True)
    summary = Column(String(200), default="")
    description = Column(Text, default="")
    color = Column(String(20), default="#2563eb")
    icon = Column(String(50), default="book-open")
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="projects")
    upload_batches = relationship("UploadBatch", back_populates="project")
    questions = relationship("Question", back_populates="project")
    notes = relationship("Note", back_populates="project")


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


class SystemProviderConfig(Base):
    """系统级 API 供应商配置（管理员维护，全站共享）"""
    __tablename__ = "system_provider_configs"

    id = Column(String(36), primary_key=True)  # UUID
    category = Column(String(20), nullable=False)  # 'openai' | 'anthropic' | 'paddleocr'
    name = Column(String(100), default="")
    is_active = Column(Boolean, default=False)
    api_key = Column(Text, default="")
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


class UploadBatch(Base):
    """上传批次表"""
    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    original_filename = Column(String(255), nullable=False)
    subject = Column(String(50))
    file_path = Column(Text)
    upload_time = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="upload_batches")
    project = relationship("Project", back_populates="upload_batches")
    questions = relationship("Question", back_populates="batch")


class Question(Base):
    """题目表"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
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
        UniqueConstraint('content_hash', 'user_id', 'project_id', name='uq_question_hash_user_project'),
    )

    user = relationship("User", back_populates="questions")
    project = relationship("Project", back_populates="questions")
    batch = relationship("UploadBatch", back_populates="questions")
    tags = relationship("QuestionTagMapping", back_populates="question")
    chat_sessions = relationship("ChatSession", back_populates="question")
    embedding = relationship("QuestionEmbedding", back_populates="question", uselist=False, cascade="all, delete-orphan")


class QuestionEmbedding(Base):
    """Cached vector representation for natural-language question search."""
    __tablename__ = "question_embeddings"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, unique=True, index=True)
    model_name = Column(String(50), nullable=False, default="local-hash-v1")
    text_hash = Column(String(64), nullable=False)
    vector_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    question = relationship("Question", back_populates="embedding")


class ChatSession(Base):
    """对话会话（可绑定题目，也可独立对话）"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=True, index=True)
    title = Column(String(255), default="新对话")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
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


class WorkflowRun(Base):
    """一次可追踪的后端工作流运行记录。

    当前由 SQLite 持久化，业务层通过 core.workflow_run_store 访问；
    后续替换为 Redis/任务队列时，尽量只替换 store 层。
    """
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    run_type = Column(String(30), nullable=False, default="split", index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    subject = Column(String(50), nullable=True)
    model_provider = Column(String(20), nullable=True)
    file_names_json = Column(Text, nullable=True)
    result_dir = Column(Text, nullable=False, default="")
    question_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="workflow_runs")


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
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)          # 笔记标题
    subject = Column(String(50))                          # 科目
    content_markdown = Column(Text, default="")           # LLM 整理后的 Markdown 内容
    source_images_json = Column(Text)                     # 原始上传图片路径列表 JSON
    ocr_text = Column(Text)                               # OCR 识别的原始文本（保留用于重新整理）
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notes")
    project = relationship("Project", back_populates="notes")
    tags = relationship("NoteTagMapping", back_populates="note", cascade="all, delete-orphan")


class NoteTagMapping(Base):
    """笔记-标签关联表（与错题共享 KnowledgeTag）"""
    __tablename__ = "note_tag_mapping"

    note_id = Column(Integer, ForeignKey("notes.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("knowledge_tags.id"), primary_key=True)

    note = relationship("Note", back_populates="tags")
    tag = relationship("KnowledgeTag")


class RagDocumentChunk(Base):
    """RAG 文档切块（统一索引表，第一期仅索引错题）"""
    __tablename__ = "rag_document_chunks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    source_type = Column(String(20), nullable=False, index=True)   # "question"
    source_id = Column(Integer, nullable=False, index=True)        # Question.id
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)                         # 用于 embedding 和注入 prompt 的文本
    metadata_json = Column(Text)                                   # 学科、题型、知识点等
    content_hash = Column(String(64), nullable=False)              # 判断是否需要重建索引
    embedding_model = Column(String(100))                          # 生成 embedding 的模型名
    vector_json = Column(Text)                                     # JSON 数组存储向量
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('source_type', 'source_id', 'chunk_index', name='uq_rag_chunk_source'),
    )


class EmailVerification(Base):
    """注册邮箱验证码（仅存哈希，不存明文）"""
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_sent_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

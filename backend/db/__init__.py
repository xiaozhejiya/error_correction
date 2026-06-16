"""
数据库模块：引擎创建、Session 工厂、初始化函数
"""

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
import os
import sys

# 添加 backend 目录到路径以支持导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import settings
from db.models import Base

# 确保数据库目录存在
db_dir = settings.db_path.parent
db_dir.mkdir(parents=True, exist_ok=True)

# 创建引擎
engine = create_engine(settings.database_url, echo=settings.database_echo)

# 启用 SQLite 外键约束 (仅针对 SQLite)
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def is_postgresql_backend(bind) -> bool:
    dialect = getattr(bind, "dialect", None)
    if dialect is not None:
        return getattr(dialect, "name", "") == "postgresql"
    return False


def _migrate_schema():
    """轻量级自动迁移：为已有表补充新列"""
    if not settings.database_url.startswith("sqlite"):
        return
    import sqlite3
    import uuid
    conn = sqlite3.connect(str(settings.db_path))
    try:
        cursor = conn.cursor()
        # 检查 questions 表是否有 answer 列
        cursor.execute("PRAGMA table_info(questions)")
        columns = {row[1] for row in cursor.fetchall()}
        if 'answer' not in columns:
            cursor.execute("ALTER TABLE questions ADD COLUMN answer TEXT")
            conn.commit()
        if 'project_id' not in columns:
            cursor.execute("ALTER TABLE questions ADD COLUMN project_id INTEGER")
            conn.commit()

        cursor.execute("PRAGMA table_info(upload_batches)")
        batch_columns = {row[1] for row in cursor.fetchall()}
        if 'project_id' not in batch_columns:
            cursor.execute("ALTER TABLE upload_batches ADD COLUMN project_id INTEGER")
            conn.commit()

        cursor.execute("PRAGMA table_info(notes)")
        note_columns = {row[1] for row in cursor.fetchall()}
        if 'project_id' not in note_columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN project_id INTEGER")
            conn.commit()

        cursor.execute("PRAGMA table_info(projects)")
        project_columns = {row[1] for row in cursor.fetchall()}
        if 'project_type' not in project_columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN project_type TEXT DEFAULT 'question'")
            conn.commit()
        if 'summary' not in project_columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN summary TEXT DEFAULT ''")
            conn.commit()
        if 'public_id' not in project_columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN public_id TEXT")
            conn.commit()

        cursor.execute("SELECT id FROM projects WHERE public_id IS NULL OR public_id = ''")
        missing_project_rows = cursor.fetchall()
        for (project_id,) in missing_project_rows:
            cursor.execute(
                "UPDATE projects SET public_id = ? WHERE id = ?",
                (str(uuid.uuid4()), project_id),
            )
        if missing_project_rows:
            conn.commit()

        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_public_id_unique ON projects(public_id)")
        conn.commit()

        cursor.execute("PRAGMA table_info(users)")
        user_columns = {row[1] for row in cursor.fetchall()}
        if 'display_name' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
            conn.commit()
        if 'nickname' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN nickname TEXT")
            conn.commit()
        if 'avatar_path' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_path TEXT")
            conn.commit()
        if 'avatar_url' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
            conn.commit()
        if 'daily_free_quota' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN daily_free_quota INTEGER DEFAULT 5")
            conn.commit()
        if 'daily_free_used' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN daily_free_used INTEGER DEFAULT 0")
            conn.commit()
        if 'daily_free_quota_date' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN daily_free_quota_date TEXT")
            conn.commit()

        # chat_sessions 表：question_id 需要改为 nullable
        # SQLite 不支持 ALTER COLUMN，需要重建表
        cursor.execute("PRAGMA table_info(chat_sessions)")
        cs_columns = {row[1]: row for row in cursor.fetchall()}
        if 'title' not in cs_columns:
            # 旧表结构，需要重建
            cursor.execute("DROP TABLE IF EXISTS chat_messages")
            cursor.execute("DROP TABLE IF EXISTS chat_sessions")
            conn.commit()

        # chat_sessions.public_id：对外使用 UUID，避免暴露自增主键
        cursor.execute("PRAGMA table_info(chat_sessions)")
        cs_columns = {row[1] for row in cursor.fetchall()}
        if 'public_id' not in cs_columns:
            cursor.execute("ALTER TABLE chat_sessions ADD COLUMN public_id TEXT")
            conn.commit()

        # 回填历史数据的 public_id
        cursor.execute("SELECT id FROM chat_sessions WHERE public_id IS NULL OR public_id = ''")
        missing_rows = cursor.fetchall()
        for (sid,) in missing_rows:
            cursor.execute(
                "UPDATE chat_sessions SET public_id = ? WHERE id = ?",
                (str(uuid.uuid4()), sid),
            )
        if missing_rows:
            conn.commit()

        # 给 public_id 创建唯一索引（SQLite 不支持后加 UNIQUE 约束，用唯一索引替代）
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_sessions_public_id_unique ON chat_sessions(public_id)")
        conn.commit()

    finally:
        conn.close()


def _prepare_postgresql_extensions():
    """在 PostgreSQL 建表前确保 pgvector 扩展可用。"""
    if not is_postgresql_backend(engine):
        return
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def _ensure_postgresql_schema():
    """为 PostgreSQL 现有表补齐 pgvector 列和索引。"""
    if not is_postgresql_backend(engine):
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "rag_document_chunks" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("rag_document_chunks")}
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        if "embedding_vector" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE rag_document_chunks "
                    f"ADD COLUMN embedding_vector vector({settings.postgres_vector_dimensions})"
                )
            )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_embedding_vector "
                "ON rag_document_chunks USING ivfflat (embedding_vector vector_cosine_ops) "
                "WITH (lists = 100)"
            )
        )


def init_db():
    """初始化数据库：建表并执行轻量级自动迁移"""
    _prepare_postgresql_extensions()
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
    _ensure_postgresql_schema()

"""
数据库模块：引擎创建、Session 工厂、初始化函数
"""

from sqlalchemy import create_engine, event
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
engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)

# 启用 SQLite 外键约束
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_schema():
    """轻量级自动迁移：为已有表补充新列"""
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


def init_db():
    """初始化数据库：建表并执行轻量级自动迁移"""
    Base.metadata.create_all(bind=engine)
    _migrate_schema()

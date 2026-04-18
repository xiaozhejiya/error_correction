"""
数据库重建脚本 — 清空并重建所有表，创建默认 Admin 用户

用法：
    cd backend
    python -m db.migrate
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash
from core.config import settings
from db import engine, SessionLocal
from db.models import Base
from db import crud


def _add_column_if_missing(conn, table: str, column: str, col_type: str, default=None):
    """安全地给已有表添加列，若已存在则跳过"""
    from sqlalchemy import text, inspect
    inspector = inspect(conn)
    existing = [c["name"] for c in inspector.get_columns(table)]
    if column not in existing:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}"))
        print(f"[migrate] 已添加列: {table}.{column}")


def migrate():
    """增量迁移：仅创建缺失的表，并确保 Admin 用户存在。每次启动自动调用，安全幂等。"""
    Base.metadata.create_all(bind=engine)  # checkfirst=True by default，已存在的表不动

    # 增量列迁移（新增字段时在此追加）
    with engine.connect() as conn:
        _add_column_if_missing(conn, "users", "session_version", "INTEGER", 0)
        _add_column_if_missing(conn, "users", "display_name", "VARCHAR(50)")
        _add_column_if_missing(conn, "users", "nickname", "VARCHAR(50)")
        _add_column_if_missing(conn, "users", "avatar_path", "TEXT")
        _add_column_if_missing(conn, "users", "avatar_url", "TEXT")
        _add_column_if_missing(conn, "users", "daily_free_quota", "INTEGER", 5)
        _add_column_if_missing(conn, "users", "daily_free_used", "INTEGER", 0)
        _add_column_if_missing(conn, "users", "daily_free_quota_date", "VARCHAR(10)")
        _add_column_if_missing(conn, "chat_sessions", "public_id", "TEXT")
        conn.commit()

    # 回填 chat_sessions.public_id（历史数据兼容）
    import uuid
    from db.models import ChatSession
    with SessionLocal() as db:
        rows = db.query(ChatSession).filter((ChatSession.public_id == None) | (ChatSession.public_id == "")).all()
        if rows:
            for s in rows:
                s.public_id = str(uuid.uuid4())
            db.commit()

    default_users = [
        {"email": "admin@admin.com",  "username": "Admin",  "password": "123456", "is_admin": True},
        {"email": "admin2@admin.com", "username": "Admin2", "password": "123456", "is_admin": True},
    ]
    with SessionLocal() as db:
        for u in default_users:
            if not crud.get_user_by_email(db, u["email"]):
                crud.create_user(
                    db,
                    email=u["email"],
                    password_hash=generate_password_hash(u["password"]),
                    username=u["username"],
                    is_admin=u["is_admin"],
                )
                print(f"[migrate] 已创建默认用户: {u['username']} ({u['email']})")


def rebuild():
    """危险：删除所有表并重建。仅用于开发环境手动重置。"""
    print("[migrate] 正在删除所有表...")
    Base.metadata.drop_all(bind=engine)
    print("[migrate] 正在重建所有表...")
    migrate()
    print("[migrate] 重建完成")


if __name__ == "__main__":
    rebuild()

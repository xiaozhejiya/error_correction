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
from db import engine, SessionLocal, ensure_pgvector_extension, is_postgresql_backend
from db.models import Base
from db import crud


def _add_column_if_missing(conn, table: str, column: str, col_type: str, default=None):
    """安全地给已有表添加列，若已存在则跳过"""
    from sqlalchemy import text, inspect

    inspector = inspect(conn)
    existing = [c["name"] for c in inspector.get_columns(table)]
    if column not in existing:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        conn.execute(
            text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")
        )
        print(f"[migrate] 已添加列: {table}.{column}")


def _ensure_default_question_project(db, user_id: int, name: str):
    from db.models import Project

    project = (
        db.query(Project)
        .filter(
            Project.user_id == user_id,
            Project.project_type == "question",
            Project.name == name,
        )
        .first()
    )
    if project:
        changed = False
        if not project.is_default:
            project.is_default = True
            changed = True
        return project, changed

    project = Project(
        user_id=user_id,
        name=name,
        project_type="question",
        description="",
        color="#2563eb",
        icon="database",
        is_default=True,
    )
    db.add(project)
    db.flush()
    return project, True


def _migrate_legacy_questions_for_user(db, user_id: int, project_id: int):
    import hashlib
    from db.models import Question, QuestionTagMapping, UploadBatch

    legacy_questions = (
        db.query(Question)
        .filter(Question.user_id == user_id, Question.project_id == None)
        .all()
    )
    if not legacy_questions:
        return 0, 0

    migrated = 0
    merged = 0
    batch_ids = set()

    for q in legacy_questions:
        if q.batch_id:
            batch_ids.add(q.batch_id)

        base_hash = (q.content_hash or "").strip()
        scoped_hash = (
            hashlib.sha256(f"{project_id}:{base_hash}".encode()).hexdigest()
            if base_hash
            else ""
        )

        existing = None
        if base_hash:
            candidates = [base_hash]
            if scoped_hash:
                candidates.append(scoped_hash)
            existing = (
                db.query(Question)
                .filter(
                    Question.user_id == user_id,
                    Question.project_id == project_id,
                    Question.content_hash.in_(candidates),
                )
                .first()
            )

        if existing:
            if (
                existing.answer is None or str(existing.answer).strip() == ""
            ) and q.answer:
                existing.answer = q.answer
            if (
                existing.user_answer is None or str(existing.user_answer).strip() == ""
            ) and q.user_answer:
                existing.user_answer = q.user_answer
            if (
                (
                    existing.review_status is None
                    or str(existing.review_status).strip() == ""
                    or existing.review_status == "待复习"
                )
                and q.review_status
                and q.review_status != "待复习"
            ):
                existing.review_status = q.review_status

            old_mappings = (
                db.query(QuestionTagMapping)
                .filter(QuestionTagMapping.question_id == q.id)
                .all()
            )
            if old_mappings:
                existing_tag_ids = {
                    m.tag_id
                    for m in db.query(QuestionTagMapping)
                    .filter(QuestionTagMapping.question_id == existing.id)
                    .all()
                }
                for m in old_mappings:
                    if m.tag_id not in existing_tag_ids:
                        db.add(
                            QuestionTagMapping(question_id=existing.id, tag_id=m.tag_id)
                        )
                db.query(QuestionTagMapping).filter(
                    QuestionTagMapping.question_id == q.id
                ).delete()

            db.delete(q)
            merged += 1
            continue

        q.project_id = project_id
        if base_hash and scoped_hash:
            q.content_hash = scoped_hash
        migrated += 1

    if batch_ids:
        (
            db.query(UploadBatch)
            .filter(
                UploadBatch.user_id == user_id,
                UploadBatch.id.in_(list(batch_ids)),
                UploadBatch.project_id == None,
            )
            .update({UploadBatch.project_id: project_id}, synchronize_session=False)
        )

    return migrated, merged


def migrate():
    """增量迁移：仅创建缺失的表，并确保 Admin 用户存在。每次启动自动调用，安全幂等。"""
    ensure_pgvector_extension(engine)
    Base.metadata.create_all(bind=engine)  # checkfirst=True by default，已存在的表不动

    # 增量列迁移（新增字段时在此追加）
    with engine.connect() as conn:
        from sqlalchemy import text

        _add_column_if_missing(conn, "users", "session_version", "INTEGER", 0)
        _add_column_if_missing(conn, "users", "display_name", "VARCHAR(50)")
        _add_column_if_missing(conn, "users", "nickname", "VARCHAR(50)")
        _add_column_if_missing(conn, "users", "avatar_path", "TEXT")
        _add_column_if_missing(conn, "users", "avatar_url", "TEXT")
        _add_column_if_missing(conn, "users", "daily_free_quota", "INTEGER", 5)
        _add_column_if_missing(conn, "users", "daily_free_used", "INTEGER", 0)
        _add_column_if_missing(conn, "users", "daily_free_quota_date", "VARCHAR(10)")
        _add_column_if_missing(conn, "upload_batches", "project_id", "INTEGER")
        _add_column_if_missing(conn, "questions", "project_id", "INTEGER")
        _add_column_if_missing(conn, "notes", "project_id", "INTEGER")
        _add_column_if_missing(
            conn, "projects", "project_type", "VARCHAR(20)", "'question'"
        )
        _add_column_if_missing(conn, "projects", "summary", "VARCHAR(200)", "''")
        _add_column_if_missing(conn, "projects", "public_id", "TEXT")
        _add_column_if_missing(conn, "chat_sessions", "public_id", "TEXT")
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_public_id_unique ON projects(public_id)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_sessions_public_id_unique ON chat_sessions(public_id)"))
        if is_postgresql_backend(engine):
            vector_dim = settings.postgres_vector_dimensions
            conn.execute(
                text(
                    f"ALTER TABLE rag_document_chunks "
                    f"ADD COLUMN IF NOT EXISTS embedding_vector vector({vector_dim})"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_source_user_project "
                    "ON rag_document_chunks(source_type, user_id, project_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_embedding_vector "
                    "ON rag_document_chunks "
                    "USING ivfflat (embedding_vector vector_cosine_ops) "
                    "WITH (lists = 100)"
                )
            )
        conn.commit()

    # 回填 projects/chat_sessions.public_id（历史数据兼容）
    import uuid
    from db.models import ChatSession, Project

    with SessionLocal() as db:
        project_rows = (
            db.query(Project)
            .filter((Project.public_id == None) | (Project.public_id == ""))
            .all()
        )
        for project in project_rows:
            project.public_id = str(uuid.uuid4())

        rows = (
            db.query(ChatSession)
            .filter((ChatSession.public_id == None) | (ChatSession.public_id == ""))
            .all()
        )
        for s in rows:
            s.public_id = str(uuid.uuid4())
        if project_rows or rows:
            db.commit()

    default_users = [
        {
            "email": "admin@admin.com",
            "username": "Admin",
            "password": "123456",
            "is_admin": True,
        },
        {
            "email": "admin2@admin.com",
            "username": "Admin2",
            "password": "123456",
            "is_admin": True,
        },
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

    from db.models import User

    with SessionLocal() as db:
        users = db.query(User).all()
        total_users = 0
        total_created_or_updated = 0
        total_migrated = 0
        total_merged = 0
        project_name = "默认错题库"

        for user in users:
            total_users += 1
            project, project_changed = _ensure_default_question_project(
                db, user.id, project_name
            )
            if project_changed:
                total_created_or_updated += 1
            migrated, merged = _migrate_legacy_questions_for_user(
                db, user.id, project.id
            )
            total_migrated += migrated
            total_merged += merged

        if total_created_or_updated or total_migrated or total_merged:
            db.commit()
            print(
                f"[migrate] 已确保默认错题库并迁移旧错题: 用户 {total_users}，默认库更新 {total_created_or_updated}，迁移 {total_migrated}，合并去重 {total_merged}"
            )


def rebuild():
    """危险：删除所有表并重建。仅用于开发环境手动重置。"""
    print("[migrate] 正在删除所有表...")
    Base.metadata.drop_all(bind=engine)
    print("[migrate] 正在重建所有表...")
    migrate()
    print("[migrate] 重建完成")


if __name__ == "__main__":
    migrate()

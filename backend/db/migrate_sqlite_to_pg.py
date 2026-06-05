"""
SQLite → PostgreSQL 数据迁移脚本

用法：
    cd backend
    python -m db.migrate_sqlite_to_pg
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy import Boolean as SABoolean
from db.models import Base

# 按外键依赖顺序排列
TABLE_ORDER = [
    "users",
    "projects",
    "provider_configs",
    "system_provider_configs",
    "upload_batches",
    "questions",
    "question_embeddings",
    "knowledge_tags",
    "question_tag_mapping",
    "chat_sessions",
    "chat_messages",
    "split_records",
    "workflow_runs",
    "notes",
    "note_tag_mapping",
    "rag_document_chunks",
    "email_verifications",
]


def migrate():
    # SQLite 源
    sqlite_path = os.path.join(os.path.dirname(__file__), "..", "runtime_data", "error_book.db")
    sqlite_path = os.path.abspath(sqlite_path)
    if not os.path.exists(sqlite_path):
        print(f"[错误] SQLite 数据库不存在: {sqlite_path}")
        sys.exit(1)

    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")

    # PostgreSQL 目标
    from core.config import settings
    import psycopg

    pg_url = settings.database_url
    if "postgresql" not in pg_url:
        print(f"[错误] 当前配置不是 PostgreSQL: {pg_url}")
        sys.exit(1)

    # 从 SQLAlchemy URL 解析连接参数
    from sqlalchemy.engine.url import make_url
    url = make_url(pg_url)

    pg_conn = psycopg.connect(
        host=url.host,
        port=url.port or 5432,
        dbname=url.database,
        user=url.username,
        password=url.password,
        autocommit=True,
    )
    cur = pg_conn.cursor()

    sqlite_inspector = inspect(sqlite_engine)

    # 禁用外键检查
    cur.execute("SET session_replication_role = 'replica';")

    with sqlite_engine.connect() as sqlite_conn:
        # 清空目标表
        for table in reversed(TABLE_ORDER):
            try:
                cur.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')
            except Exception:
                pass
        print("[准备] 已清空 PostgreSQL 目标表\n")

        for table in TABLE_ORDER:
            if table not in sqlite_inspector.get_table_names():
                print(f"[跳过] SQLite 中不存在表: {table}")
                continue

            columns = sqlite_inspector.get_columns(table)
            col_names = [c["name"] for c in columns]
            rows = sqlite_conn.execute(text(f'SELECT * FROM "{table}"')).fetchall()

            if not rows:
                print(f"[跳过] {table}: 无数据")
                continue

            col_list = ", ".join(f'"{c}"' for c in col_names)
            placeholders = ", ".join(f"%s" for _ in col_names)
            insert_sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

            # 找出布尔列（SQLite 存 0/1，PG 需要 true/false）
            orm_model = None
            for mapper in Base.registry.mappers:
                if mapper.local_table.name == table:
                    orm_model = mapper.class_
                    break
            bool_cols = set()
            if orm_model:
                for col in orm_model.__table__.columns:
                    if isinstance(col.type, SABoolean):
                        bool_cols.add(col.name)

            count = 0
            for row in rows:
                # 转换布尔值
                values = list(row)
                for i, col in enumerate(col_names):
                    if col in bool_cols and values[i] is not None:
                        values[i] = bool(values[i])
                try:
                    cur.execute(insert_sql, values)
                    count += 1
                except Exception as e:
                    err_str = str(e).lower()
                    if any(kw in err_str for kw in ["duplicate key", "unique", "foreign key", "violat"]):
                        continue
                    else:
                        print(f"  [警告] {table} id={row[0] if row else '?'}: {e}")

            # 重置序列
            pk_col = col_names[0]
            try:
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{pk_col}'), "
                    f"COALESCE((SELECT MAX({pk_col}) FROM {table}), 1))"
                )
            except Exception:
                pass

            print(f"[完成] {table}: 迁移 {count} 行")

    # 恢复外键检查
    cur.execute("SET session_replication_role = 'origin';")
    cur.close()
    pg_conn.close()
    print("\n迁移完成！")


if __name__ == "__main__":
    migrate()

from unittest.mock import Mock, patch

import db as db_module


class _BeginContext:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        return False


class _RecordingConnection:
    def __init__(self):
        self.statements = []

    def execute(self, statement):
        self.statements.append(" ".join(str(statement).split()))


def test_prepare_postgresql_extensions_creates_vector_extension():
    conn = _RecordingConnection()
    fake_engine = Mock()
    fake_engine.begin.return_value = _BeginContext(conn)

    with (
        patch.object(db_module, "engine", fake_engine),
        patch.object(db_module, "is_postgresql_backend", return_value=True),
    ):
        db_module._prepare_postgresql_extensions()

    assert any(
        "CREATE EXTENSION IF NOT EXISTS vector" in statement
        for statement in conn.statements
    )


def test_ensure_postgresql_schema_adds_missing_vector_column_and_index():
    conn = _RecordingConnection()
    fake_engine = Mock()
    fake_engine.begin.return_value = _BeginContext(conn)
    fake_inspector = Mock()
    fake_inspector.get_table_names.return_value = ["rag_document_chunks"]
    fake_inspector.get_columns.return_value = [
        {"name": "id"},
        {"name": "content"},
        {"name": "vector_json"},
    ]

    with (
        patch.object(db_module, "engine", fake_engine),
        patch.object(db_module, "inspect", return_value=fake_inspector),
        patch.object(db_module, "is_postgresql_backend", return_value=True),
    ):
        db_module._ensure_postgresql_schema()

    assert any(
        "CREATE EXTENSION IF NOT EXISTS vector" in statement
        for statement in conn.statements
    )
    assert any(
        "ALTER TABLE rag_document_chunks" in statement
        and "embedding_vector" in statement
        for statement in conn.statements
    )
    assert any(
        "CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_embedding_vector"
        in statement
        for statement in conn.statements
    )


def test_ensure_postgresql_schema_skips_column_creation_when_present():
    conn = _RecordingConnection()
    fake_engine = Mock()
    fake_engine.begin.return_value = _BeginContext(conn)
    fake_inspector = Mock()
    fake_inspector.get_table_names.return_value = ["rag_document_chunks"]
    fake_inspector.get_columns.return_value = [
        {"name": "id"},
        {"name": "embedding_vector"},
    ]

    with (
        patch.object(db_module, "engine", fake_engine),
        patch.object(db_module, "inspect", return_value=fake_inspector),
        patch.object(db_module, "is_postgresql_backend", return_value=True),
    ):
        db_module._ensure_postgresql_schema()

    assert not any(
        "ALTER TABLE rag_document_chunks ADD COLUMN embedding_vector" in statement
        for statement in conn.statements
    )
    assert any(
        "CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_embedding_vector"
        in statement
        for statement in conn.statements
    )

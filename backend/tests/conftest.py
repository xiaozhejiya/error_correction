"""
pytest 配置 — 确保 backend/ 在 sys.path 中，以便 import config 等模块。
"""

import sys
import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db.models import Base

# 将 backend/ 目录加入 sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def pytest_addoption(parser):
    parser.addoption(
        "--model-provider",
        action="store",
        default="openai",
        choices=["openai", "anthropic"],
        help="指定测试使用的模型供应商: openai (默认) 或 anthropic",
    )


@pytest.fixture(scope="session")
def model_provider(request):
    return request.config.getoption("--model-provider")


# ── 公共 fixture ─────────────────────────────────────────


@pytest.fixture
def db():
    """每个测试用例使用独立的内存 SQLite 数据库"""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ── 公共 helper ──────────────────────────────────────────


def make_question(qid, text="题目内容", qtype="选择题", tags=None):
    """构造符合 save_questions_to_db 输入格式的题目 dict"""
    q = {
        "question_id": qid,
        "question_type": qtype,
        "content_blocks": [{"block_type": "text", "content": f"{text}_{qid}"}],
        "has_formula": False,
        "has_image": False,
    }
    if tags:
        q["knowledge_tags"] = tags
    return q

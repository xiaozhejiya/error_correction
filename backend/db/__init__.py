"""数据库模块：引擎创建、Session 工厂、初始化函数。"""

import os
import sys

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker

import logging

logger = logging.getLogger(__name__)

# 添加 backend 目录到路径以支持导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import settings
from db.models import Base


def _database_url():
    return settings.database_url


def _database_backend(url: str | None = None) -> str:
    try:
        backend = make_url(url or _database_url()).get_backend_name()
        return (backend or "").lower()
    except Exception:
        return ""


def is_sqlite_backend(bind_or_url=None) -> bool:
    url = str(bind_or_url.url) if hasattr(bind_or_url, "url") else bind_or_url
    return _database_backend(url).startswith("sqlite")


def is_postgresql_backend(bind_or_url=None) -> bool:
    url = str(bind_or_url.url) if hasattr(bind_or_url, "url") else bind_or_url
    return _database_backend(url).startswith("postgresql")


if is_sqlite_backend():
    db_dir = settings.db_path.parent
    db_dir.mkdir(parents=True, exist_ok=True)

# 默认引擎，设置较短的连接超时以便在数据库未启动时快速失败
def create_db_engine(url=None):
    db_url = url or _database_url()
    return create_engine(
        db_url,
        echo=settings.database_echo,
        pool_pre_ping=not is_sqlite_backend(db_url),
        connect_args={"connect_timeout": 5} if is_postgresql_backend(db_url) else {},
    )

def _attach_sqlite_pragmas(target_engine: Engine) -> Engine:
    if not is_sqlite_backend(target_engine):
        return target_engine

    @event.listens_for(target_engine, "connect")
    def _configure_sqlite_connection(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return target_engine


engine = _attach_sqlite_pragmas(create_db_engine())


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_pgvector_extension(bind: Engine | None = None):
    target = bind or engine
    if not is_postgresql_backend(target):
        return
    # 尝试执行，如果失败则抛出异常，外层会处理
    with target.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def init_db():
    """初始化数据库：确保扩展存在并创建缺失表。"""
    global engine, SessionLocal
    
    try:
        # 尝试使用当前配置初始化
        ensure_pgvector_extension(engine)
        Base.metadata.create_all(bind=engine)
        logger.info(f"数据库初始化成功: {engine.url}")
    except Exception as e:
        if is_postgresql_backend(engine):
            err_msg = str(e)
            missing_driver = isinstance(e, ModuleNotFoundError) or (
                isinstance(e, ImportError) and "psycopg" in err_msg.lower()
            )
            missing_pgvector = 'extension "vector" is not available' in err_msg.lower()
            if missing_driver:
                logger.error("\n" + "!"*60 +
                            "\n[缺少数据库驱动] 你配置了 PostgreSQL 但未安装驱动程序。"
                            "\n请运行以下命令安装："
                            "\n\n  pip install \"psycopg[binary]\""
                            "\n" + "!"*60 + "\n")
            elif missing_pgvector:
                logger.error("\n" + "!"*60 +
                            "\n[缺少 pgvector 扩展] PostgreSQL 已连接，但数据库中无法创建 vector 扩展。"
                            "\n请使用已安装 pgvector 的 PostgreSQL 镜像/实例，例如："
                            "\n\n  docker run -d --name pg-vector -e POSTGRES_PASSWORD=root -p 15432:5432 pgvector/pgvector:pg16"
                            "\n\n或者在当前 PostgreSQL 实例中先安装 pgvector 扩展后再执行："
                            "\n\n  CREATE EXTENSION vector;"
                            "\n" + "!"*60 + "\n")
            
            logger.warning(f"无法连接到 PostgreSQL ({engine.url}): {e}")
            
            # 如果是开发环境且 PG 连接失败，尝试自动回退到 SQLite 以防阻塞开发
            if os.getenv('FLASK_DEBUG', 'false').lower() == 'true':
                fallback_url = f"sqlite:///{settings.db_path}"
                logger.warning(f"检测到开发模式，自动回退到本地 SQLite: {fallback_url}")
                logger.warning("\n" + "="*60 +
                             "\n[提示] 如果你想使用 PostgreSQL，请检查以下几点："
                             "\n\n  1. 确保本地 PostgreSQL 服务已启动 (默认端口 5432)"
                             "\n  2. 确保已创建名为 'ctb' 的数据库 (CREATE DATABASE ctb;)"
                             "\n  3. 确保 PostgreSQL 已安装 pgvector 扩展，并可执行 CREATE EXTENSION vector;"
                             "\n  4. 检查 .env 中的密码是否正确 (当前尝试密码: 123456)"
                             "\n\n  * 如果没有安装 PostgreSQL，系统将继续使用 SQLite 运行。"
                             "\n" + "="*60 + "\n")
                
                # 重新创建引擎和 SessionLocal
                engine = _attach_sqlite_pragmas(create_db_engine(fallback_url))
                SessionLocal.configure(bind=engine)
                
                # 重新执行建表
                Base.metadata.create_all(bind=engine)
                return
                
        # 非开发环境或无法回退时，打印详细指引并抛出
        if is_postgresql_backend(engine):
            logger.error("\n" + "="*60 +
                        "\n[数据库连接失败] 请确保 PostgreSQL 容器已启动！"
                        "\n你可以运行以下命令来启动数据库："
                        "\n\n  docker pull pgvector/pgvector:pg16"
                        "\n  docker run -d --name pg-vector -e POSTGRES_PASSWORD=root -p 15432:5432 pgvector/pgvector:pg16"
                        "\n\n或者在 .env 中删除 APP_DATABASE_URL 以回退到本地 SQLite。"
                        "\n" + "="*60 + "\n")
        raise

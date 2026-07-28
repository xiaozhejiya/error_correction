"""Gunicorn 生产入口：显式准备运行目录并初始化数据库。"""

from core.config import settings


settings.ensure_dirs()

from db import init_db
from db.migrate import migrate
from web_app import app


init_db()
migrate()

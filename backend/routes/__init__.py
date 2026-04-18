"""
路由注册模块 — 将所有 Blueprint 注册到 Flask app
"""

from .auth import bp as auth_bp
from .upload import bp as upload_bp
from .questions import bp as questions_bp
from .chat import bp as chat_bp
from .stats import bp as stats_bp
from .settings import bp as settings_bp
from .notes import bp as notes_bp


def register_routes(app):
    """注册所有 Blueprint 到 Flask app"""
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(questions_bp, url_prefix='/api')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(stats_bp, url_prefix='/api')
    app.register_blueprint(settings_bp, url_prefix='/api')
    app.register_blueprint(notes_bp, url_prefix='/api/notes')

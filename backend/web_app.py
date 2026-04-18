"""
错题本生成系统 - Web应用（纯 API 服务）

职责：
  - 创建 Flask 应用实例，配置全局参数
  - 注册所有 Blueprint 路由（routes/ 目录）
  - 提供全局错误处理和登录鉴权中间件
  - 提供 OCR 图片、下载文件、擦除结果等静态资源接口

前端由 Vite dev server 独立运行（localhost:5173），
通过代理将 /api 等请求转发到本服务（localhost:5001）。
"""

import os
import sys
import logging

# 无论从项目根目录执行 `python backend/web_app.py` 还是在 `backend` 下执行 `python web_app.py`，
# 都把 backend 目录加入 sys.path，保证 `core`、`routes`、`db` 等包解析一致。
_BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
from dotenv import load_dotenv

from core.config import settings
from db import init_db, SessionLocal
from db import crud
from routes import register_routes

# 加载 backend/.env（无论从哪个目录启动都指向同一文件）
load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))

# 模块级日志记录器，日志名称为 'web_app'
logger = logging.getLogger(__name__)

# ============================================================
# Flask 应用初始化
# ============================================================

app = Flask(__name__)

# 会话密钥：用于加密 Flask session cookie，生产环境必须修改
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')

# 跨域支持：前端 dev server (5173) 和后端 (5001) 端口不同，需要 CORS
# supports_credentials=True 允许携带 cookie（登录态依赖 session cookie）
CORS(app, supports_credentials=True)

# 文件上传配置
app.config['UPLOAD_FOLDER'] = settings.upload_dir
app.config['MAX_CONTENT_LENGTH'] = settings.max_file_size_mb * 1024 * 1024  # MB → 字节


# ============================================================
# 全局错误处理
# ============================================================

@app.errorhandler(413)
def request_entity_too_large(error):
    """上传文件超出 MAX_CONTENT_LENGTH 限制时触发"""
    return jsonify({
        'success': False,
        'error': f'文件大小超出限制，最大允许 {settings.max_file_size_mb}MB'
    }), 413


@app.errorhandler(404)
def not_found(error):
    """请求的路由不存在"""
    return jsonify({
        'success': False,
        'error': '请求的资源不存在'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """未捕获的服务端异常"""
    return jsonify({
        'success': False,
        'error': '服务器内部错误，请稍后重试'
    }), 500


# ============================================================
# 全局中间件
# ============================================================

@app.before_request
def require_login():
    """登录鉴权：所有 /api/ 路由默认要求登录

    豁免列表：
      - /api/auth/*  — 登录、注册、获取当前用户等认证接口
      - /api/status  — 系统状态查询（前端初始化时需要）
    """
    if request.path.startswith('/api/'):
        if request.path.startswith('/api/auth/') or request.path == '/api/status':
            return None
        if 'user_id' not in session:
            return jsonify({'error': '请先登录', 'code': 'UNAUTHORIZED'}), 401
        # 密码重置后失效旧 session：仅在写操作时查 DB 比对 session_version，
        # GET 请求无需每次查库，降低高频只读接口的数据库压力
        if request.method != 'GET':
            user_id = session['user_id']
            sess_ver = session.get('session_version')
            with SessionLocal() as db:
                user = crud.get_user_by_id(db, user_id)
                if not user:
                    session.clear()
                    return jsonify({'error': '用户不存在', 'code': 'UNAUTHORIZED'}), 401
                db_ver = user.session_version or 0
                if sess_ver != db_ver:
                    session.clear()
                    return jsonify({'error': '登录已失效，请重新登录', 'code': 'SESSION_EXPIRED'}), 401
    return None


@app.teardown_request
def clear_request_provider_context(error=None):
    """请求结束后清理请求级 provider 上下文，避免线程复用串状态。"""
    settings.clear_request_provider_context()
    return None


# ============================================================
# 注册 Blueprint 路由
# ============================================================
# 各 Blueprint 定义在 routes/ 目录下：
#   - auth.py      → /api/auth/*     用户认证
#   - upload.py    → /api/*          文件上传、分割、导出
#   - questions.py → /api/*          题目 CRUD、错题库、搜索
#   - chat.py      → /api/*          AI 对话
#   - stats.py     → /api/*          统计分析
#   - settings.py  → /api/*          系统配置、模型管理

register_routes(app)


# ============================================================
# 静态资源服务
# ============================================================
# 以下路由提供后端生成的文件资源，前端通过 Vite 代理访问：
#   /download/*  — 导出的 Markdown 错题本文件
#   /images/*    — PaddleOCR 解析出的图片（存储在 struct_dir/imgs/）
#   /erased/*    — EnsExam 擦除手写字迹后的图片

def _safe_join(base_dir: str, rel_path: str) -> str | None:
    """安全路径拼接，防止目录遍历攻击（如 ../../etc/passwd）

    将 rel_path 拼接到 base_dir 后，检查结果路径是否仍在 base_dir 内。
    如果路径跳出了 base_dir，返回 None。
    """
    base = os.path.abspath(base_dir)
    target = os.path.abspath(os.path.join(base, rel_path))
    if os.path.normcase(target).startswith(os.path.normcase(base + os.sep)):
        return target
    return None


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """提供用户上传的原始文件（笔记图片等）"""
    file_path = _safe_join(str(settings.upload_dir), filename)
    if not file_path or not os.path.exists(file_path):
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    return send_file(file_path)


@app.route('/download/<path:filename>')
def download_file(filename):
    """下载结果文件（如导出的 Markdown 错题本）

    禁用浏览器缓存，确保每次下载都是最新版本。
    """
    file_path = _safe_join(settings.results_dir, filename)
    if not file_path:
        return jsonify({'success': False, 'error': '非法文件路径'}), 400
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    resp = send_file(
        file_path,
        as_attachment=True,                          # 触发浏览器下载而非预览
        download_name=os.path.basename(filename),    # 下载时显示的文件名
        conditional=False,
        etag=False,
        max_age=0,
    )
    # 强制禁用缓存，避免浏览器返回旧文件
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route('/images/<path:filename>')
def serve_image(filename):
    """提供 PaddleOCR 解析出的图片资源

    OCR 处理后的结构化图片存储在 struct_dir/imgs/ 目录下，
    前端题目卡片中的图片通过此接口加载。
    """
    base = os.path.join(settings.struct_dir, "imgs")
    file_path = _safe_join(base, filename)
    if not file_path or not os.path.exists(file_path):
        return jsonify({'success': False, 'error': '图片不存在'}), 404
    return send_file(file_path)


@app.route('/erased/<path:filename>')
def serve_erased_image(filename):
    """提供 EnsExam 擦除手写字迹后的图片

    用户上传试卷后，EnsExam 模型会擦除手写笔迹，
    还原干净的题目底图，结果保存在 erased_dir。
    """
    file_path = _safe_join(str(settings.erased_dir), filename)
    if not file_path or not os.path.exists(file_path):
        return jsonify({'success': False, 'error': '图片不存在'}), 404
    return send_file(file_path)


# ============================================================
# 启动入口
# ============================================================

if __name__ == '__main__':
    # 创建运行时目录（uploads、pages、results 等）
    settings.ensure_dirs()

    # 初始化数据库（建表 + 自动迁移）
    init_db()
    from db.migrate import migrate
    migrate()

    logger.info("错题本生成系统 - API 服务")
    logger.info("API 地址: http://localhost:5001")
    logger.info("=" * 50)

    # 从环境变量读取调试模式开关（默认关闭）
    # 开启后 Flask 会自动重载代码变更，并在浏览器显示详细错误信息
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(
        host='0.0.0.0', port=5001, debug=debug,
        threaded=True,                           # 多线程处理并发请求
        exclude_patterns=["*site-packages*"],    # 排除第三方库文件变更触发的重载
    )

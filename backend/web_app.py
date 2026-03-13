"""
错题本生成系统 - Web应用
提供前端界面用于执行工作流
"""

import os
import json
import uuid
import logging
import threading
import mimetypes
from datetime import datetime
from pathlib import PurePath
from typing import Optional

# Windows 注册表可能将 .js 映射为 text/plain，导致浏览器拒绝加载 ES module
mimetypes.add_type('application/javascript', '.js')
from flask import Flask, request, jsonify, send_file, send_from_directory
from dotenv import load_dotenv

from src.workflow import build_workflow
from src.utils import export_wrongbook as export_wrongbook_md
from config import settings
from db import init_db, SessionLocal
from db import crud
from db.models import Question, UploadBatch, KnowledgeTag

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置（统一从 config.py 导入）
app.config['UPLOAD_FOLDER'] = settings.upload_dir
app.config['MAX_CONTENT_LENGTH'] = settings.max_file_size_mb * 1024 * 1024


def _safe_join(base_dir: str, rel_path: str) -> str | None:
    base = os.path.abspath(base_dir)
    target = os.path.abspath(os.path.join(base, rel_path))
    if os.path.normcase(target).startswith(os.path.normcase(base + os.sep)):
        return target
    return None

@app.errorhandler(413)
def request_entity_too_large(error):
    """文件大小超出Flask限制"""
    return jsonify({
        'success': False,
        'error': f'文件大小超出限制，最大允许 {settings.max_file_size_mb}MB'
    }), 413


@app.errorhandler(404)
def not_found(error):
    """页面未找到"""
    return jsonify({
        'success': False,
        'error': '请求的资源不存在'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """服务器内部错误"""
    return jsonify({
        'success': False,
        'error': '服务器内部错误，请稍后重试'
    }), 500


# 全局工作流图（带 MemorySaver，通过 thread_id 管理会话状态）
workflow_graph = build_workflow()
current_thread_id = None
session_files = {}
session_file_order = []
cancelled_file_keys = set()
session_lock = threading.Lock()


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return PurePath(filename).suffix.lower().lstrip('.') in settings.allowed_extensions


def _serialize_question(q: Question) -> dict:
    """将 Question ORM 对象序列化为前端 JSON 格式"""
    subject = None
    if q.batch:
        subject = q.batch.subject
    knowledge_tags = []
    if q.tags:
        for mapping in q.tags:
            if mapping.tag:
                knowledge_tags.append(mapping.tag.tag_name)

    return {
        'id': q.id,
        'question_type': q.question_type,
        'content_json': json.loads(q.content_json) if q.content_json else [],
        'options_json': json.loads(q.options_json) if q.options_json else None,
        'has_formula': q.has_formula,
        'has_image': q.has_image,
        'needs_correction': q.needs_correction,
        'answer': q.answer,
        'subject': subject,
        'knowledge_tags': knowledge_tags,
        'created_at': q.created_at.isoformat() if q.created_at else None,
    }


def _serialize_chat_session(session) -> dict:
    """将 ChatSession ORM 对象序列化为前端 JSON"""
    return {
        'id': session.id,
        'question_id': session.question_id,
        'created_at': session.created_at.isoformat() if session.created_at else None,
        'updated_at': session.updated_at.isoformat() if session.updated_at else None,
    }


def _serialize_question_detail(q: Question) -> dict:
    """将 Question ORM 对象序列化为详情 JSON（含科目、标签、答案等）"""
    base = _serialize_question(q)
    # subject / knowledge_tags already set by _serialize_question
    base['original_filename'] = q.batch.original_filename if q.batch else None
    base['user_answer'] = q.user_answer
    base['updated_at'] = q.updated_at.isoformat() if q.updated_at else None
    base['review_status'] = q.review_status or '待复习'
    base['image_refs_json'] = json.loads(q.image_refs_json) if q.image_refs_json else None
    return base


# ============================================================
# 前端托管（生产模式：直接返回 Vite 构建产物）
# ============================================================
FRONTEND_DIST = os.path.join(settings.project_root, 'frontend', 'dist')


@app.route('/')
def index():
    """主页 - 返回介绍页"""
    return send_from_directory(FRONTEND_DIST, 'index.html')


@app.route('/app')
@app.route('/app.html')
def app_page():
    """工作台 - 返回 Vue SPA"""
    return send_from_directory(FRONTEND_DIST, 'app.html')


@app.route('/static/vue/<path:filename>')
def serve_vue_dist(filename):
    """提供 Vue 前端构建产物"""
    return send_from_directory(FRONTEND_DIST, filename)


# ============================================================
# 遗留独立页面
# ============================================================


@app.route('/record')
def record_page():
    """错题本记录页面"""
    record_file = os.path.join(settings.project_root, 'record.html')
    if os.path.exists(record_file):
        return send_from_directory(settings.project_root, 'record.html')
    return "记录页文件不存在", 404


# ============================================================
# API 接口
# ============================================================


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """处理文件上传（支持多文件）。

    这里只负责把原始文件保存到 uploads 并登记到会话中；
    标准化(PDF/图片 → 图片列表) + OCR + 分割，会在 /api/split 里由用户点击“开始分割”后统一触发。

    Returns:
        JSON响应，包含上传结果
    """
    # 支持多文件：前端用 'files' 字段发送，兼容单文件 'file' 字段
    files = request.files.getlist('files')
    if not files:
        files = request.files.getlist('file')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': '没有上传文件'}), 400

    # 校验每个文件
    for file in files:
        if file.filename == '':
            continue

        if not allowed_file(file.filename):
            return jsonify({
                'error': f'不支持的文件格式: {file.filename}。支持: {", ".join(settings.allowed_extensions)}'
            }), 400

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        file_size_mb = file_size / (1024 * 1024)

        if file_size_mb > settings.max_file_size_mb:
            return jsonify({
                'error': f'{file.filename} 大小为 {file_size_mb:.1f}MB，超出最大限制 {settings.max_file_size_mb}MB'
            }), 400

        if file_size == 0:
            return jsonify({
                'error': f'{file.filename} 为空文件，请重新选择'
            }), 400

    try:
        global current_thread_id, session_files, session_file_order

        file_keys = request.form.getlist('file_key')
        if not file_keys:
            file_keys = request.form.getlist('file_keys')

        prepared = []
        for i, file in enumerate(files):
            if file.filename == '':
                continue
            fk = file_keys[i] if i < len(file_keys) and file_keys[i] else None
            prepared.append((fk, file))

        if not prepared:
            return jsonify({'error': '没有上传文件'}), 400

        results_out = []
        for fk, file in prepared:
            file_key = fk or f"{uuid.uuid4().hex}"

            original_ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
            filename = f"{uuid.uuid4().hex}.{original_ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            with session_lock:
                cancelled = file_key in cancelled_file_keys
                if cancelled:
                    cancelled_file_keys.discard(file_key)

            if cancelled:
                try:
                    os.remove(filepath)
                except FileNotFoundError:
                    pass
                continue

            with session_lock:
                if current_thread_id is not None:
                    current_thread_id = None
                    session_files = {}
                    session_file_order = []

                session_files[file_key] = {
                    "filename": file.filename,
                    "filepath": filepath,
                }
                if file_key not in session_file_order:
                    session_file_order.append(file_key)

            results_out.append({
                "file_key": file_key,
                "filename": file.filename,
            })

        return jsonify({
            'success': True,
            'message': '上传成功',
            'result': {
                'file_count': len(results_out),
                'files': results_out,
            }
        })

    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': '文件保存失败，请重新上传'
        }), 500
    except Exception as e:
        logger.exception("文件处理失败")
        return jsonify({
            'success': False,
            'error': '文件处理失败，请稍后重试'
        }), 500


@app.route('/api/cancel_file', methods=['POST'])
def cancel_file():
    try:
        global current_thread_id, session_files, session_file_order

        data = request.get_json(silent=True) or {}
        file_key = data.get('file_key')
        if not file_key:
            return jsonify({
                'success': False,
                'error': '缺少 file_key'
            }), 400

        if current_thread_id is not None:
            return jsonify({
                'success': False,
                'error': '已开始分割，无法撤销单个文件；请重置后重新上传'
            }), 400

        filepath = None
        existed = False
        with session_lock:
            cancelled_file_keys.add(file_key)

            existed = file_key in session_files
            v = session_files.pop(file_key, None) or {}
            filepath = v.get('filepath')
            if file_key in session_file_order:
                session_file_order.remove(file_key)

            cancelled_file_keys.discard(file_key)

        if filepath:
            try:
                os.remove(filepath)
            except FileNotFoundError:
                pass

        return jsonify({
            'success': True,
            'message': '已撤销该文件' if existed else '已标记撤销该文件',
        })

    except Exception as e:
        logger.exception("撤销文件失败")
        return jsonify({
            'success': False,
            'error': '撤销失败，请稍后重试'
        }), 500


@app.route('/api/split', methods=['POST'])
def split_questions():
    """开始执行标准化 + OCR + 分割。

    用户点击前端“开始分割题目”后调用该接口：
    - 标准化输入（PDF/图片 → 图片列表）
    - 触发 Agent/OCR 并分割题目

    Returns:
        JSON响应，包含分割后的题目
    """
    try:
        global workflow_graph, current_thread_id, session_files, session_file_order

        # 读取请求体参数（模型供应商）
        data = request.get_json(silent=True) or {}
        model_provider = data.get("model_provider", "deepseek")
        if model_provider not in ("deepseek", "ernie"):
            return jsonify({
                'success': False,
                'error': f'不支持的模型供应商: {model_provider}'
            }), 400

        with session_lock:
            keys = list(session_file_order)
            file_paths = []
            for k in keys:
                v = session_files.get(k) or {}
                fp = v.get('filepath')
                if fp:
                    file_paths.append(fp)

        if not file_paths:
            return jsonify({
                'success': False,
                'error': '请先上传文件'
            }), 400

        current_thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": current_thread_id}}

        workflow_graph.invoke({"file_paths": file_paths, "model_provider": model_provider}, config=config)
        state = workflow_graph.invoke(None, config=config)

        questions = state.get('questions', [])
        warnings = state.get('warnings', [])

        return jsonify({
            'success': True,
            'message': f'成功分割 {len(questions)} 道题目',
            'questions': questions,
            'warnings': warnings,
        })

    except Exception as e:
        logger.exception("题目分割失败")
        return jsonify({
            'success': False,
            'error': '题目分割失败，请稍后重试'
        }), 500


@app.route('/api/export', methods=['POST'])
def export_wrongbook():
    """
    注入选中题目 ID 并恢复图执行导出

    图执行: export → END

    Returns:
        JSON响应，包含导出文件路径
    """
    try:
        global current_thread_id, session_files, session_file_order

        data = request.get_json(silent=True) or {}
        selected_ids = data.get('selected_ids', [])

        if not isinstance(selected_ids, list):
            return jsonify({
                'success': False,
                'error': 'selected_ids 必须为列表'
            }), 400

        if not selected_ids:
            return jsonify({
                'success': False,
                'error': '未选择任何题目'
            }), 400

        # 检查是否已分割（通过 questions.json 存在性判断，不依赖内存中的 current_thread_id）
        results_dir = settings.results_dir
        questions_file = os.path.join(results_dir, "questions.json")
        if not os.path.exists(questions_file):
            return jsonify({
                'success': False,
                'error': '请先分割题目'
            }), 400

        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        output_path = export_wrongbook_md(
            questions,
            selected_ids,
        )

        return jsonify({
            'success': True,
            'message': '错题本导出成功',
            'output_path': output_path
        })

    except Exception as e:
        logger.exception("导出失败")
        return jsonify({
            'success': False,
            'error': '导出失败，请稍后重试'
        }), 500


@app.route('/api/questions', methods=['GET'])
def get_questions():
    """
    获取已分割的题目列表

    Returns:
        JSON响应，包含题目列表
    """
    try:
        results_dir = settings.results_dir
        questions_file = os.path.join(results_dir, "questions.json")

        if not os.path.exists(questions_file):
            return jsonify({
                'success': True,
                'questions': [],
                'message': '暂无题目数据'
            })

        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        return jsonify({
            'success': True,
            'questions': questions
        })

    except json.JSONDecodeError:
        return jsonify({
            'success': False,
            'error': '题目数据文件格式错误，请重新分割题目'
        }), 500
    except Exception as e:
        logger.exception("获取题目列表失败")
        return jsonify({
            'success': False,
            'error': '获取题目列表失败，请稍后重试'
        }), 500


@app.route('/preview')
def preview():
    """显示预览页面"""
    results_dir = settings.results_dir
    preview_file = os.path.join(results_dir, "preview.html")

    if os.path.exists(preview_file):
        with open(preview_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    else:
        return "预览文件不存在，请先分割题目", 404


# ============================================================
# 资源服务
# ============================================================


@app.route('/download/<path:filename>')
def download_file(filename):
    """下载结果文件"""
    results_dir = settings.results_dir
    file_path = _safe_join(results_dir, filename)
    if not file_path:
        return jsonify({
            'success': False,
            'error': '非法文件路径'
        }), 400

    if not os.path.exists(file_path):
        return jsonify({
            'success': False,
            'error': '文件不存在'
        }), 404

    resp = send_file(
        file_path,
        as_attachment=True,
        download_name=os.path.basename(filename),
        conditional=False,
        etag=False,
        max_age=0,
    )
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route('/images/<path:filename>')
def serve_image(filename):
    """提供 OCR 解析出的图片资源"""
    base = os.path.join(settings.struct_dir, "imgs")
    file_path = _safe_join(base, filename)
    if not file_path or not os.path.exists(file_path):
        return jsonify({'success': False, 'error': '图片不存在'}), 404
    return send_file(file_path)


@app.route('/api/status', methods=['GET'])
def get_status():
    """
    获取系统状态

    Returns:
        JSON响应，包含系统配置和状态
    """
    try:
        # 检查配置
        paddleocr_configured = bool(os.getenv('PADDLEOCR_API_URL'))
        deepseek_configured = bool(os.getenv('DEEPSEEK_API_KEY'))
        ernie_configured = bool(os.getenv('ERNIE_API_KEY'))
        
        # 构建可用模型列表
        available_models = [
            {
                'value': 'deepseek', 
                'label': 'DeepSeek', 
                'configured': deepseek_configured,
                'description': 'DeepSeek V3.2'
            },
            {
                'value': 'ernie', 
                'label': '文心一言', 
                'configured': ernie_configured,
                'description': '百度文心大模型 4.5'
            }
        ]

        status = {
            'paddleocr_configured': paddleocr_configured,
            'deepseek_configured': deepseek_configured,
            'ernie_configured': ernie_configured,
            'available_models': available_models,
            'langsmith_enabled': os.getenv('LANGSMITH_TRACING', 'false').lower() == 'true',
            'output_dirs': {
                'pages': str(settings.pages_dir),
                'struct': str(settings.struct_dir),
                'results': str(settings.results_dir),
            }
        }

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        logger.exception("获取系统状态失败")
        return jsonify({
            'success': False,
            'error': '获取系统状态失败，请稍后重试'
        }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """
    分页查询历史题目（全部题目，非仅错题）

    Query参数:
        page: 页码（默认1）
        page_size: 每页数量（默认20）
        start_date: 开始日期（可选，格式：YYYY-MM-DD）
        end_date: 结束日期（可选，格式：YYYY-MM-DD）
    """
    try:
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # 解析日期
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        with SessionLocal() as db:
            questions, total = crud.get_history_questions(
                db,
                start_date=start_date,
                end_date=end_date,
                page=page,
                page_size=page_size
            )

            total_pages = (total + page_size - 1) // page_size
            items = [_serialize_question(q) for q in questions]

            return jsonify({
                'success': True,
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            })

    except ValueError:
        return jsonify({'success': False, 'error': '日期格式错误，请使用 YYYY-MM-DD 格式'}), 400
    except Exception as e:
        logger.exception("查询历史题目失败")
        return jsonify({'success': False, 'error': '查询失败，请稍后重试'}), 500


@app.route('/api/search', methods=['GET'])
def search_questions():
    """
    搜索题目（知识点/题型/关键字）

    Query参数:
        keyword: 关键字搜索（匹配题目内容）
        knowledge_tag: 知识点标签筛选
        question_type: 题型筛选
        page: 页码（默认1）
        page_size: 每页数量（默认20）
    """
    try:
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))
        keyword = request.args.get('keyword', type=str)
        knowledge_tag = request.args.get('knowledge_tag', type=str)
        question_type = request.args.get('question_type', type=str)

        # 至少需要一个搜索条件
        if not any([keyword, knowledge_tag, question_type]):
            return jsonify({
                'success': False,
                'error': '至少需要提供一个搜索条件（keyword/knowledge_tag/question_type）'
            }), 400

        with SessionLocal() as db:
            questions, total = crud.search_questions(
                db,
                keyword=keyword if keyword else None,
                knowledge_tag=knowledge_tag if knowledge_tag else None,
                question_type=question_type if question_type else None,
                page=page,
                page_size=page_size
            )

            total_pages = (total + page_size - 1) // page_size
            items = [_serialize_question(q) for q in questions]

            return jsonify({
                'success': True,
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            })

    except Exception as e:
        logger.exception("搜索题目失败")
        return jsonify({'success': False, 'error': '搜索失败，请稍后重试'}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    获取知识点统计信息
    """
    try:
        subject = request.args.get('subject', type=str) or None
        with SessionLocal() as db:
            stats = crud.get_knowledge_stats(db, subject=subject)
            return jsonify({
                'success': True,
                'stats': stats,
                'total_tags': len(stats)
            })

    except Exception as e:
        logger.exception("获取统计失败")
        return jsonify({'success': False, 'error': '获取统计失败，请稍后重试'}), 500


@app.route('/api/question/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """
    删除题目

    Path参数:
        question_id: 题目ID
    """
    try:
        with SessionLocal() as db:
            success = crud.delete_question(db, question_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': '题目已删除'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '题目不存在'
                }), 404

    except Exception as e:
        logger.exception("删除题目失败")
        return jsonify({'success': False, 'error': '删除失败，请稍后重试'}), 500


# ============================================================
# 错题库 API
# ============================================================


@app.route('/api/error-bank', methods=['GET'])
def get_error_bank():
    """
    错题库统一查询

    Query参数:
        subject: 科目筛选
        knowledge_tag: 知识点标签筛选
        question_type: 题型筛选
        keyword: 关键字搜索
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        page: 页码（默认1）
        page_size: 每页数量（默认20）
    """
    try:
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))
        subject = request.args.get('subject', type=str) or None
        knowledge_tag = request.args.get('knowledge_tag', type=str) or None
        question_type = request.args.get('question_type', type=str) or None
        keyword = request.args.get('keyword', type=str) or None
        review_status = request.args.get('review_status', type=str) or None
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        with SessionLocal() as db:
            questions, total = crud.query_questions(
                db,
                subject=subject,
                knowledge_tag=knowledge_tag,
                question_type=question_type,
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                review_status=review_status,
                page=page,
                page_size=page_size,
            )

            total_pages = (total + page_size - 1) // page_size
            items = [_serialize_question_detail(q) for q in questions]

            return jsonify({
                'success': True,
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
            })

    except ValueError:
        return jsonify({'success': False, 'error': '日期格式错误，请使用 YYYY-MM-DD 格式'}), 400
    except Exception as e:
        logger.exception("查询错题库失败")
        return jsonify({'success': False, 'error': '查询失败，请稍后重试'}), 500


@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    """获取所有科目列表"""
    try:
        with SessionLocal() as db:
            subjects = crud.get_existing_subjects(db)
            return jsonify({'success': True, 'subjects': subjects})
    except Exception as e:
        logger.exception("获取科目列表失败")
        return jsonify({'success': False, 'error': '获取科目列表失败'}), 500


@app.route('/api/question-types', methods=['GET'])
def get_question_types():
    """获取所有题型列表"""
    try:
        with SessionLocal() as db:
            types = crud.get_existing_question_types(db)
            return jsonify({'success': True, 'question_types': types})
    except Exception as e:
        logger.exception("获取题型列表失败")
        return jsonify({'success': False, 'error': '获取题型列表失败'}), 500


@app.route('/api/question/<int:question_id>/answer', methods=['PATCH'])
def update_question_answer(question_id):
    """保存用户答案"""
    try:
        data = request.get_json(silent=True) or {}
        user_answer = data.get('user_answer')
        if user_answer is None:
            return jsonify({'success': False, 'error': '缺少 user_answer 字段'}), 400
        if len(user_answer) > 10000:
            return jsonify({'success': False, 'error': '答案内容过长（最多 10000 字符）'}), 400

        with SessionLocal() as db:
            question = crud.update_user_answer(db, question_id, user_answer)
            if not question:
                return jsonify({'success': False, 'error': '题目不存在'}), 404

            return jsonify({
                'success': True,
                'message': '答案已保存',
                'user_answer': question.user_answer,
                'updated_at': question.updated_at.isoformat() if question.updated_at else None,
            })

    except Exception as e:
        logger.exception("保存答案失败")
        return jsonify({'success': False, 'error': '保存答案失败，请稍后重试'}), 500


@app.route('/api/question/<int:question_id>/review-status', methods=['PATCH'])
def update_question_review_status(question_id):
    """更新题目复习状态"""
    try:
        data = request.get_json(silent=True) or {}
        review_status = data.get('review_status')
        if not review_status:
            return jsonify({'success': False, 'error': '缺少 review_status 字段'}), 400

        with SessionLocal() as db:
            question = crud.update_review_status(db, question_id, review_status)
            if not question:
                return jsonify({'success': False, 'error': '题目不存在'}), 404

            return jsonify({
                'success': True,
                'message': '复习状态已更新',
                'review_status': question.review_status,
                'updated_at': question.updated_at.isoformat() if question.updated_at else None,
            })

    except ValueError:
        return jsonify({'success': False, 'error': f'无效的复习状态，可选值: {", ".join(crud.VALID_REVIEW_STATUSES)}'}), 400
    except Exception as e:
        logger.exception("更新复习状态失败")
        return jsonify({'success': False, 'error': '更新复习状态失败，请稍后重试'}), 500


@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """获取 Dashboard 所需的完整统计数据，支持 ?subject= 学科筛选"""
    try:
        subject = request.args.get('subject') or None
        with SessionLocal() as db:
            # 可用学科列表（始终返回完整列表供筛选器使用）
            subjects = crud.get_existing_subjects(db)

            # 复习状态统计
            review_stats = crud.get_review_status_stats(db, subject=subject)

            # 总体统计
            statistics = crud.get_statistics(db, subject=subject)

            # 知识点标签统计 top 10（横向条形图）
            tag_stats = crud.get_knowledge_stats(db, subject=subject, limit=10)

            # 知识点 × 掌握状态（堆叠柱状图）
            tag_status_stats = crud.get_tag_status_stats(db, subject=subject, limit=10)

            # 知识点 × 题型（热力图）
            tag_type_stats = crud.get_tag_type_stats(db, subject=subject, tag_limit=8)

            # 最近30天每日新增 + 已掌握趋势
            daily_counts = crud.get_daily_counts(db, days=30, subject=subject)

            return jsonify({
                'success': True,
                'subjects': subjects,
                'review_stats': review_stats,
                'total_questions': statistics['total_questions'],
                'by_subject': statistics['by_subject'],
                'tag_stats': tag_stats,
                'tag_status_stats': tag_status_stats,
                'tag_type_stats': tag_type_stats,
                'daily_counts': daily_counts,
            })

    except Exception as e:
        logger.exception("获取 Dashboard 统计失败")
        return jsonify({'success': False, 'error': '获取统计失败，请稍后重试'}), 500


@app.route('/api/save-to-db', methods=['POST'])
def save_to_db():
    """
    将分割好的题目导入错题库（仅入库，不导出 Markdown）

    Request Body:
        {
            "selected_ids": ["q_0", "q_1", ...]   # 选中的题目 ID 列表
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        selected_ids = data.get('selected_ids', [])

        if not isinstance(selected_ids, list) or not selected_ids:
            return jsonify({'success': False, 'error': '请选择至少一道题目'}), 400

        results_dir = settings.results_dir
        questions_file = os.path.join(results_dir, "questions.json")
        if not os.path.exists(questions_file):
            return jsonify({'success': False, 'error': '请先分割题目'}), 400

        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        selected_questions = [q for q in questions if q.get('question_id') in selected_ids]
        if not selected_questions:
            return jsonify({'success': False, 'error': '未找到选中的题目'}), 400

        # 合并前端传来的 answer/user_answer（按 question_id 匹配）
        answers_map = {a['question_id']: a for a in data.get('answers', []) if 'question_id' in a}
        for sq in selected_questions:
            qid = sq.get('question_id')
            if qid and qid in answers_map:
                if 'answer' in answers_map[qid]:
                    sq['answer'] = answers_map[qid]['answer']
                if 'user_answer' in answers_map[qid]:
                    sq['user_answer'] = answers_map[qid]['user_answer']

        # 读取科目信息
        subject = None
        meta_path = os.path.join(results_dir, "split_metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            subject = meta.get("subject")

        with session_lock:
            batch_info = {
                "original_filename": ", ".join(
                    session_files.get(k, {}).get("filename", "未知")
                    for k in session_file_order
                ),
                "subject": subject,
                "file_path": "",
            }

        with SessionLocal() as db:
            result = crud.save_questions_to_db(db, selected_questions, batch_info)

        return jsonify({
            'success': True,
            'message': f'已导入 {result["created"]} 道题目（跳过 {result["duplicates"]} 道重复）',
            'created': result['created'],
            'duplicates': result['duplicates'],
        })

    except Exception as e:
        logger.exception("导入错题库失败")
        if 'readonly database' in str(e).lower():
            return jsonify({'success': False, 'error': '数据库文件为只读，请检查文件权限（error_book.db）'}), 500
        return jsonify({'success': False, 'error': '导入错题库失败，请稍后重试'}), 500


@app.route('/api/ai-analysis', methods=['POST'])
def ai_analysis():
    """
    AI 错题分析（骨架路由）

    接收一组题目 ID，调用 AI 对这些错题进行综合分析，返回：
    - 薄弱知识点诊断
    - 错因归纳
    - 针对性复习建议

    Request Body:
        {
            "question_ids": [1, 2, 3]   # 必填，至少 1 道，最多 20 道
        }

    Response:
        {
            "success": true,
            "analysis": {
                "summary": "综合诊断摘要",
                "weak_points": ["知识点A", "知识点B"],
                "error_patterns": [
                    {"pattern": "错因类型", "description": "详细描述", "question_ids": [1, 2]}
                ],
                "suggestions": ["建议1", "建议2"],
                "per_question": [
                    {"question_id": 1, "diagnosis": "该题错因分析", "hint": "解题提示"}
                ]
            }
        }

    TODO（后端开发者）:
        1. 从数据库查询题目详情（content_json, options_json, user_answer, knowledge_tags）
        2. 构建 prompt，将题目内容 + 用户答案 + 知识点标签传给 LLM
        3. 调用 LLM（建议使用 llm.py 中的 init_model，支持 deepseek/ernie）
        4. 解析 LLM 返回的结构化结果，填充 analysis 字段
        5. 可选：将分析结果缓存到数据库，避免重复分析
    """
    try:
        data = request.get_json(silent=True) or {}
        question_ids = data.get('question_ids', [])

        if not isinstance(question_ids, list) or not question_ids:
            return jsonify({'success': False, 'error': '请选择至少一道题目'}), 400

        if len(question_ids) > 20:
            return jsonify({'success': False, 'error': '单次最多分析 20 道题目'}), 400

        with SessionLocal() as db:
            questions = crud.get_questions_by_ids(db, question_ids)
            if not questions:
                return jsonify({'success': False, 'error': '未找到对应题目'}), 404

            # ── TODO: 替换为真实 AI 分析逻辑 ──────────────────
            # 当前返回占位数据，供前端联调使用
            knowledge_tags = set()
            per_question = []
            for q in questions:
                tags = [m.tag.tag_name for m in (q.tags or []) if m.tag]
                knowledge_tags.update(tags)
                per_question.append({
                    'question_id': q.id,
                    'diagnosis': f'题目 #{q.id} 的错因分析（待 AI 生成）',
                    'hint': f'题目 #{q.id} 的解题提示（待 AI 生成）',
                })

            analysis = {
                'summary': f'已选择 {len(questions)} 道题目进行分析（AI 分析功能待接入）',
                'weak_points': list(knowledge_tags) or ['暂无知识点数据'],
                'error_patterns': [
                    {
                        'pattern': '待 AI 识别',
                        'description': '错因模式将由 AI 自动归纳',
                        'question_ids': [q.id for q in questions],
                    }
                ],
                'suggestions': [
                    '建议回顾相关知识点章节',
                    '建议针对薄弱环节进行专项练习',
                ],
                'per_question': per_question,
            }
            # ── END TODO ──────────────────────────────────────

            return jsonify({
                'success': True,
                'analysis': analysis,
            })

    except Exception as e:
        logger.exception("AI 分析失败")
        return jsonify({'success': False, 'error': 'AI 分析失败，请稍后重试'}), 500


@app.route('/api/export-from-db', methods=['POST'])
def export_from_db():
    """从数据库按 ID 列表导出 Markdown 错题本"""
    try:
        data = request.get_json(silent=True) or {}
        selected_ids = data.get('selected_ids', [])

        if not isinstance(selected_ids, list) or not selected_ids:
            return jsonify({'success': False, 'error': '请选择至少一道题目'}), 400

        with SessionLocal() as db:
            questions_orm = crud.get_questions_by_ids(db, selected_ids)
            if not questions_orm:
                return jsonify({'success': False, 'error': '未找到对应题目'}), 404

            # 转换为 export_wrongbook_md 所需的 dict 格式
            questions = []
            for q in questions_orm:
                questions.append({
                    'question_id': str(q.id),
                    'question_type': q.question_type,
                    'content_blocks': json.loads(q.content_json) if q.content_json else [],
                    'options': json.loads(q.options_json) if q.options_json else None,
                    'has_formula': q.has_formula,
                    'has_image': q.has_image,
                    'knowledge_tags': [m.tag.tag_name for m in (q.tags or []) if m.tag],
                })

            str_ids = [str(qid) for qid in selected_ids]
            output_path = export_wrongbook_md(questions, str_ids)

        return jsonify({
            'success': True,
            'message': '错题本导出成功',
            'output_path': output_path,
        })

    except Exception as e:
        logger.exception("从数据库导出失败")
        return jsonify({'success': False, 'error': '导出失败，请稍后重试'}), 500


# ============================================================
# 教学辅导对话 API
# ============================================================


@app.route('/api/question/<int:question_id>/answer', methods=['PUT'])
def save_question_answer(question_id):
    """保存题目答案（Markdown 格式，用于 AI 辅导）"""
    try:
        data = request.get_json(silent=True) or {}
        answer = data.get('answer')
        if answer is None:
            return jsonify({'success': False, 'error': '缺少 answer 字段'}), 400
        if len(answer) > 50000:
            return jsonify({'success': False, 'error': '答案内容过长（最多 50000 字符）'}), 400

        with SessionLocal() as db:
            question = crud.update_question_answer(db, question_id, answer)
            if not question:
                return jsonify({'success': False, 'error': '题目不存在'}), 404

            return jsonify({
                'success': True,
                'message': '答案已保存',
                'answer': question.answer,
            })

    except Exception as e:
        logger.exception("保存答案失败")
        return jsonify({'success': False, 'error': '保存答案失败，请稍后重试'}), 500


@app.route('/api/question/<int:question_id>/chats', methods=['GET'])
def get_question_chats(question_id):
    """获取某道题目的所有对话会话"""
    try:
        with SessionLocal() as db:
            sessions = crud.get_chat_sessions_by_question(db, question_id)
            return jsonify({
                'success': True,
                'sessions': [_serialize_chat_session(s) for s in sessions],
            })
    except Exception as e:
        logger.exception("获取对话列表失败")
        return jsonify({'success': False, 'error': '获取对话列表失败'}), 500


@app.route('/api/chat', methods=['POST'])
def create_chat():
    """创建新对话"""
    try:
        data = request.get_json(silent=True) or {}
        question_id = data.get('question_id')
        if not question_id:
            return jsonify({'success': False, 'error': '缺少 question_id'}), 400

        with SessionLocal() as db:
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return jsonify({'success': False, 'error': '题目不存在'}), 404

            session = crud.create_chat_session(db, question_id)
            return jsonify({
                'success': True,
                'session': _serialize_chat_session(session),
            })

    except Exception as e:
        logger.exception("创建对话失败")
        return jsonify({'success': False, 'error': '创建对话失败'}), 500


@app.route('/api/chat/sessions', methods=['GET'])
def get_chat_sessions():
    """分页获取所有对话会话"""
    try:
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))

        with SessionLocal() as db:
            sessions, total = crud.get_all_chat_sessions(db, page=page, page_size=page_size)
            total_pages = (total + page_size - 1) // page_size

            return jsonify({
                'success': True,
                'sessions': [_serialize_chat_session(s) for s in sessions],
                'total': total,
                'page': page,
                'total_pages': total_pages,
            })

    except Exception as e:
        logger.exception("获取对话会话列表失败")
        return jsonify({'success': False, 'error': '获取对话会话列表失败'}), 500


@app.route('/api/chat/<int:session_id>/messages', methods=['GET'])
def get_chat_messages(session_id):
    """游标分页获取对话消息"""
    try:
        limit = min(100, max(1, request.args.get('limit', 30, type=int)))
        before_id = request.args.get('before_id', type=int)

        with SessionLocal() as db:
            result = crud.get_chat_messages(db, session_id, limit=limit, before_id=before_id)
            return jsonify({
                'success': True,
                'messages': result['messages'],
                'hasMore': result['hasMore'],
            })

    except Exception as e:
        logger.exception("获取对话消息失败")
        return jsonify({'success': False, 'error': '获取对话消息失败'}), 500


@app.route('/api/chat/<int:session_id>/stream', methods=['POST'])
def stream_chat(session_id):
    """SSE 流式对话"""
    from flask import Response
    from teach_agent import stream_teach

    try:
        data = request.get_json(silent=True) or {}
        message = data.get('message', '').strip()
        model_provider = data.get('model_provider', 'deepseek')

        if not message:
            return jsonify({'success': False, 'error': '消息不能为空'}), 400

        if model_provider not in ('deepseek', 'ernie'):
            return jsonify({'success': False, 'error': f'不支持的模型供应商: {model_provider}'}), 400

        with SessionLocal() as db:
            from db.models import ChatSession as ChatSessionModel, QuestionTagMapping
            from sqlalchemy.orm import selectinload
            chat_session = db.query(ChatSessionModel).options(
                selectinload(ChatSessionModel.question)
                .selectinload(Question.batch),
                selectinload(ChatSessionModel.question)
                .selectinload(Question.tags)
                .selectinload(QuestionTagMapping.tag),
            ).filter(ChatSessionModel.id == session_id).first()
            if not chat_session:
                return jsonify({'success': False, 'error': '对话不存在'}), 404

            question = chat_session.question
            if not question:
                return jsonify({'success': False, 'error': '关联题目不存在'}), 404

            # 序列化题目数据
            q_data = _serialize_question(question)

            # 加载历史消息（最近 20 条）
            history_result = crud.get_chat_messages(db, session_id, limit=20)
            history = [{"role": m["role"], "content": m["content"]} for m in history_result["messages"]]

            # 追加用户消息
            history.append({"role": "user", "content": message})
            crud.add_chat_message(db, session_id, "user", message)

        def generate():
            full_response = []
            try:
                for token in stream_teach(
                    question=q_data,
                    messages=history,
                    provider=model_provider,
                ):
                    full_response.append(token)
                    yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.exception("流式对话错误")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            # 保存完整的 assistant 回复
            assistant_content = "".join(full_response)
            if assistant_content:
                try:
                    with SessionLocal() as db:
                        crud.add_chat_message(db, session_id, "assistant", assistant_content)
                except Exception as e:
                    logger.error(f"保存 assistant 回复失败: {e}")

            yield f"data: {json.dumps({'done': True})}\n\n"

        resp = Response(generate(), mimetype='text/event-stream')
        resp.headers['Cache-Control'] = 'no-cache'
        resp.headers['X-Accel-Buffering'] = 'no'
        return resp

    except Exception as e:
        logger.exception("流式对话失败")
        return jsonify({'success': False, 'error': '对话失败，请稍后重试'}), 500


if __name__ == '__main__':
    # 确保运行时目录存在
    settings.ensure_dirs()
    # 初始化数据库
    init_db()
    # 自动迁移（添加新列等）
    from db.migrate import migrate
    migrate()
    print("[数据库] 初始化完成")

    print("=" * 60)
    print("错题本生成系统 - Web应用")
    print("=" * 60)
    print("访问地址: http://localhost:5001")
    print("=" * 60)

    app.run(
        host='0.0.0.0', port=5001, debug=True,
        exclude_patterns=["*site-packages*"],
    )

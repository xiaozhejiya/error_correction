import os
import json
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify, session

from db import SessionLocal
from db import crud
from db.models import Question, UploadBatch, KnowledgeTag
from core.config import settings
from src.utils import export_wrongbook as export_wrongbook_md

logger = logging.getLogger(__name__)

bp = Blueprint('questions', __name__)


def _effective_user_id():
    """管理员返回 None（不过滤），普通用户返回 user_id"""
    if session.get('is_admin'):
        return None
    return session.get('user_id')


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


def _read_split_subject():
    """从 split_metadata.json 读取学科信息"""
    meta_path = os.path.join(str(settings.results_dir), "split_metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f).get("subject")
    return None


@bp.route('/questions', methods=['GET'])
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


@bp.route('/history', methods=['GET'])
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
                page_size=page_size,
                user_id=_effective_user_id(),
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


@bp.route('/search', methods=['GET'])
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
                page_size=page_size,
                user_id=_effective_user_id(),
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


@bp.route('/question/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """
    删除题目

    Path参数:
        question_id: 题目ID
    """
    try:
        with SessionLocal() as db:
            success = crud.delete_question(db, question_id, user_id=_effective_user_id())
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


@bp.route('/error-bank', methods=['GET'])
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
            questions, total, grand_total = crud.query_questions(
            db,
            user_id=_effective_user_id(),
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
                'grand_total': grand_total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
            })

    except ValueError:
        return jsonify({'success': False, 'error': '日期格式错误，请使用 YYYY-MM-DD 格式'}), 400
    except Exception as e:
        logger.exception("查询错题库失败")
        return jsonify({'success': False, 'error': '查询失败，请稍后重试'}), 500


@bp.route('/subjects', methods=['GET'])
def get_subjects():
    """获取所有科目列表"""
    try:
        with SessionLocal() as db:
            subjects = crud.get_existing_subjects(db, user_id=_effective_user_id())
            return jsonify({'success': True, 'subjects': subjects})
    except Exception as e:
        logger.exception("获取科目列表失败")
        return jsonify({'success': False, 'error': '获取科目列表失败'}), 500


@bp.route('/question-types', methods=['GET'])
def get_question_types():
    """获取所有题型列表"""
    try:
        with SessionLocal() as db:
            types = crud.get_existing_question_types(db, user_id=_effective_user_id())
            return jsonify({'success': True, 'question_types': types})
    except Exception as e:
        logger.exception("获取题型列表失败")
        return jsonify({'success': False, 'error': '获取题型列表失败'}), 500


@bp.route('/question/<int:question_id>', methods=['PATCH'])
def update_question(question_id):
    """编辑题目内容和/或答案"""
    try:
        data = request.get_json(silent=True) or {}
        with SessionLocal() as db:
            question = db.get(Question, question_id)
            if not question:
                return jsonify({'success': False, 'error': '题目不存在'}), 404
            uid = _effective_user_id()
            if uid is not None and question.user_id != uid:
                return jsonify({'success': False, 'error': '题目不存在'}), 404
            try:
                if 'content' in data:
                    text = str(data['content'])[:20000]
                    blocks = [{'block_type': 'text', 'content': text}]
                    question.content_json = json.dumps(blocks, ensure_ascii=False)
                    question.content_hash = crud.compute_content_hash(blocks)
                if 'answer' in data:
                    question.answer = str(data['answer'])[:10000] if data['answer'] else None
                question.updated_at = datetime.utcnow()
                db.commit()
                return jsonify({'success': True})
            except Exception:
                db.rollback()
                raise
    except Exception:
        logger.exception("编辑题目失败")
        return jsonify({'success': False, 'error': '保存失败，请稍后重试'}), 500


@bp.route('/question/<int:question_id>/answer', methods=['PATCH'])
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
            question = crud.update_user_answer(db, question_id, user_answer, user_id=_effective_user_id())
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


@bp.route('/question/<int:question_id>/review-status', methods=['PATCH'])
def update_question_review_status(question_id):
    """更新题目复习状态"""
    try:
        data = request.get_json(silent=True) or {}
        review_status = data.get('review_status')
        if not review_status:
            return jsonify({'success': False, 'error': '缺少 review_status 字段'}), 400

        with SessionLocal() as db:
            question = crud.update_review_status(db, question_id, review_status, user_id=_effective_user_id())
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


@bp.route('/save-to-db', methods=['POST'])
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
        selected_uids = data.get('selected_ids', [])

        if not isinstance(selected_uids, list) or not selected_uids:
            return jsonify({'success': False, 'error': '请选择至少一道题目'}), 400

        results_dir = settings.results_dir
        questions_file = os.path.join(results_dir, "questions.json")
        if not os.path.exists(questions_file):
            return jsonify({'success': False, 'error': '请先分割题目'}), 400

        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        uid_set = set(selected_uids)
        selected_questions = [q for q in questions if q.get('uid') in uid_set]
        if not selected_questions:
            return jsonify({'success': False, 'error': '未找到选中的题目'}), 400

        # 合并前端传来的 answer/user_answer（按 uid 匹配）
        answers_map = {a['uid']: a for a in data.get('answers', []) if 'uid' in a}
        for sq in selected_questions:
            uid = sq.get('uid')
            if uid and uid in answers_map:
                if 'answer' in answers_map[uid]:
                    sq['answer'] = answers_map[uid]['answer']
                if 'user_answer' in answers_map[uid]:
                    sq['user_answer'] = answers_map[uid]['user_answer']

        # 读取科目信息
        subject = _read_split_subject()

        from core.state import session_lock, get_user_session
        uid = session.get('user_id')
        with session_lock:
            us = get_user_session(uid)
            batch_info = {
                "original_filename": ", ".join(
                    us["session_files"].get(k, {}).get("filename", "未知")
                    for k in us["session_file_order"]
                ),
                "subject": subject,
                "file_path": "",
            }

        with SessionLocal() as db:
            result = crud.save_questions_to_db(db, selected_questions, batch_info, user_id=session.get('user_id'))

        return jsonify({
            'success': True,
            'message': f'已导入 {result["created"]} 道题目（跳过 {result["duplicates"]} 道重复）',
            'created': result['created'],
            'duplicates': result['duplicates'],
        })

    except Exception as e:
        logger.exception("导入错题库失败")
        return jsonify({'success': False, 'error': '导入错题库失败，请稍后重试'}), 500


@bp.route('/ai-analysis', methods=['POST'])
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
        3. 调用 LLM（建议使用 llm.py 中的 init_model，支持 openai/anthropic）
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
            questions = crud.get_questions_by_ids(db, question_ids, user_id=_effective_user_id())
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


@bp.route('/export-from-db', methods=['POST'])
def export_from_db():
    """从数据库按 ID 列表导出 Markdown 错题本"""
    try:
        data = request.get_json(silent=True) or {}
        selected_ids = data.get('selected_ids', [])

        if not isinstance(selected_ids, list) or not selected_ids:
            return jsonify({'success': False, 'error': '请选择至少一道题目'}), 400

        with SessionLocal() as db:
            questions_orm = crud.get_questions_by_ids(db, selected_ids, user_id=_effective_user_id())
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

            # DB 导出的题目已按 selected_ids 过滤完毕，赋顺序 uid 后全部导出
            for i, q in enumerate(questions):
                q['uid'] = str(i)
            output_path = export_wrongbook_md(questions, [str(i) for i in range(len(questions))])

        return jsonify({
            'success': True,
            'message': '错题本导出成功',
            'output_path': output_path,
        })

    except Exception as e:
        logger.exception("从数据库导出失败")
        return jsonify({'success': False, 'error': '导出失败，请稍后重试'}), 500


@bp.route('/question/<int:question_id>/answer', methods=['PUT'])
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
            question = crud.update_question_answer(db, question_id, answer, user_id=_effective_user_id())
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

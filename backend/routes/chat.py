"""Chat-related routes (AI conversation with questions)."""

import json
import logging

from flask import Blueprint, request, jsonify, session, Response

from db import SessionLocal
from db import crud
from db.models import Question, ChatSession as ChatSessionModel, QuestionTagMapping
from core.config import settings
from core.quota import consume_daily_free_quota, has_daily_free_quota, quota_exceeded_response, uses_server_llm

logger = logging.getLogger(__name__)

bp = Blueprint('chat', __name__)


def _effective_user_id():
    """管理员返回 None（不过滤），普通用户返回 user_id"""
    if session.get('is_admin'):
        return None
    return session.get('user_id')


def _apply_provider_context(db, user_id):
    managed_llm = {}
    for category in ('openai', 'anthropic'):
        provider = crud.get_active_system_provider(db, category)
        if provider and provider.api_key:
            managed_llm[category] = settings.build_provider_config(
                category,
                api_key=provider.api_key or '',
                base_url=provider.base_url or '',
                model_name=provider.model_name or None,
                light_model_name=getattr(provider, 'light_model_name', None) or None,
                supports_function_calling=getattr(provider, 'supports_function_calling', True),
            )

    settings.apply_managed_providers(managed_llm)
    if user_id:
        settings.load_providers_from_db(user_id, db=db)
    else:
        settings.reload_providers()


def _serialize_chat_session(s) -> dict:
    """将 ChatSession ORM 对象序列化为前端 JSON"""
    return {
        'id': s.public_id,
        'title': s.title or '新对话',
        'question_id': s.question_id,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'updated_at': s.updated_at.isoformat() if s.updated_at else None,
    }


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


@bp.route('/question/<int:question_id>/chats', methods=['GET'])
def get_question_chats(question_id):
    """获取某道题目的所有对话会话"""
    try:
        with SessionLocal() as db:
            sessions = crud.get_chat_sessions_by_question(db, question_id, user_id=_effective_user_id())
            return jsonify({
                'success': True,
                'sessions': [_serialize_chat_session(s) for s in sessions],
            })
    except Exception as e:
        logger.exception("获取对话列表失败")
        return jsonify({'success': False, 'error': '获取对话列表失败'}), 500


@bp.route('/chat', methods=['POST'])
def create_chat():
    """创建新对话（支持绑定题目或独立对话）"""
    try:
        data = request.get_json(silent=True) or {}
        question_id = data.get('question_id')  # 可选
        title = data.get('title', '新对话')
        user_id = session.get('user_id')

        if question_id:
            with SessionLocal() as db:
                uid = _effective_user_id()
                q_query = db.query(Question).filter(Question.id == question_id)
                if uid is not None:
                    q_query = q_query.filter(Question.user_id == uid)
                question = q_query.first()
                if not question:
                    return jsonify({'success': False, 'error': '题目不存在'}), 404
                chat_session = crud.create_chat_session(db, question_id=question_id, user_id=user_id, title=title)
                return jsonify({'success': True, 'session': _serialize_chat_session(chat_session)})
        else:
            # 独立对话
            with SessionLocal() as db:
                chat_session = crud.create_chat_session(db, user_id=user_id, title=title)
                return jsonify({'success': True, 'session': _serialize_chat_session(chat_session)})

    except Exception as e:
        logger.exception("创建对话失败")
        return jsonify({'success': False, 'error': '创建对话失败'}), 500


@bp.route('/chat/my-sessions', methods=['GET'])
def get_my_chat_sessions():
    """获取当前用户的独立对话列表"""
    try:
        user_id = session.get('user_id')
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(50, max(1, request.args.get('limit', 20, type=int)))

        with SessionLocal() as db:
            sessions_list, total = crud.get_user_chat_sessions(db, user_id, page=page, page_size=page_size)
            return jsonify({
                'success': True,
                'sessions': [_serialize_chat_session(s) for s in sessions_list],
                'total': total,
            })
    except Exception as e:
        logger.exception("获取对话列表失败")
        return jsonify({'success': False, 'error': '获取对话列表失败'}), 500


@bp.route('/chat/sessions', methods=['GET'])
def get_chat_sessions():
    """分页获取所有对话会话"""
    try:
        page = max(1, request.args.get('page', 1, type=int))
        page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))

        with SessionLocal() as db:
            sessions, total = crud.get_all_chat_sessions(db, page=page, page_size=page_size, user_id=_effective_user_id())
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


@bp.route('/chat/<session_id>', methods=['PATCH'])
def update_chat_title(session_id):
    """更新对话标题"""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', '').strip()
        if not title:
            return jsonify({'success': False, 'error': '标题不能为空'}), 400

        with SessionLocal() as db:
            cs = crud.get_chat_session_by_public_id(db, session_id, user_id=_effective_user_id())
            if not cs:
                return jsonify({'success': False, 'error': '对话不存在'}), 404
            s = crud.update_chat_session_title(db, cs.id, title, user_id=_effective_user_id())
            if not s:
                return jsonify({'success': False, 'error': '对话不存在'}), 404
            return jsonify({'success': True, 'session': _serialize_chat_session(s)})
    except Exception as e:
        logger.exception("更新对话标题失败")
        return jsonify({'success': False, 'error': '更新失败'}), 500


@bp.route('/chat/<session_id>', methods=['DELETE'])
def delete_chat(session_id):
    """删除对话"""
    try:
        with SessionLocal() as db:
            cs = crud.get_chat_session_by_public_id(db, session_id, user_id=_effective_user_id())
            if not cs:
                return jsonify({'success': False, 'error': '对话不存在'}), 404
            if not crud.delete_chat_session(db, cs.id, user_id=_effective_user_id()):
                return jsonify({'success': False, 'error': '对话不存在'}), 404
            return jsonify({'success': True})
    except Exception as e:
        logger.exception("删除对话失败")
        return jsonify({'success': False, 'error': '删除失败'}), 500


@bp.route('/chat/<session_id>/messages', methods=['GET'])
def get_chat_messages(session_id):
    """游标分页获取对话消息"""
    try:
        limit = min(100, max(1, request.args.get('limit', 30, type=int)))
        before_id = request.args.get('before_id', type=int)

        with SessionLocal() as db:
            cs = crud.get_chat_session_by_public_id(db, session_id, user_id=_effective_user_id())
            if not cs:
                return jsonify({'success': False, 'error': '对话不存在'}), 404
            result = crud.get_chat_messages(db, cs.id, limit=limit, before_id=before_id, user_id=_effective_user_id())
            return jsonify({
                'success': True,
                'messages': result['messages'],
                'hasMore': result['hasMore'],
            })

    except Exception as e:
        logger.exception("获取对话消息失败")
        return jsonify({'success': False, 'error': '获取对话消息失败'}), 500


@bp.route('/chat/<session_id>/stream', methods=['POST'])
def stream_chat(session_id):
    """SSE 流式对话"""
    from agents.teach import stream_teach
    from sqlalchemy.orm import selectinload

    try:
        data = request.get_json(silent=True) or {}
        message = data.get('message', '').strip()
        model_provider = data.get('model_provider', 'openai')
        model_name = data.get('model_name') or None
        deep_think = data.get('deep_think', False)

        # 深度思考模式：切换到 reasoner 模型
        if deep_think and model_provider == 'openai':
            model_name = 'deepseek-reasoner'

        if not message:
            return jsonify({'success': False, 'error': '消息不能为空'}), 400

        if not settings.is_valid_provider(model_provider):
            return jsonify({'success': False, 'error': f'不支持的模型供应商: {model_provider}'}), 400

        user_id = session.get('user_id')
        with SessionLocal() as db:
            _apply_provider_context(db, user_id)
            uid = _effective_user_id()
            cs_query = db.query(ChatSessionModel).options(
                selectinload(ChatSessionModel.question)
                .selectinload(Question.batch),
                selectinload(ChatSessionModel.question)
                .selectinload(Question.tags)
                .selectinload(QuestionTagMapping.tag),
            ).filter(ChatSessionModel.public_id == session_id)
            if uid is not None:
                cs_query = cs_query.filter(ChatSessionModel.user_id == uid)
            chat_session = cs_query.first()
            if not chat_session:
                return jsonify({'success': False, 'error': '对话不存在'}), 404

            should_consume_quota = bool(user_id) and uses_server_llm(db, user_id, model_provider)
            quota_user_id = user_id
            if should_consume_quota:
                quota_user = crud.get_user_by_id(db, user_id)
                if not quota_user:
                    session.clear()
                    return jsonify({'success': False, 'error': '用户不存在'}), 401
                if not has_daily_free_quota(db, quota_user):
                    payload, status = quota_exceeded_response(db, quota_user)
                    return jsonify(payload), status

            # 独立对话或题目绑定对话
            question = chat_session.question
            q_data = _serialize_question(question) if question else None

            # 加载历史消息（最近 20 条）
            history_result = crud.get_chat_messages(db, chat_session.id, limit=20)
            history = [{"role": m["role"], "content": m["content"]} for m in history_result["messages"]]

            # 额度校验通过后再追加用户消息
            history.append({"role": "user", "content": message})
            crud.add_chat_message(db, chat_session.id, "user", message)
            chat_session_id = chat_session.id

        def generate():
            full_response = []
            full_reasoning = []
            try:
                for chunk in stream_teach(
                    question=q_data,
                    messages=history,
                    provider=model_provider,
                    model_name=model_name,
                ):
                    # stream_teach 现在 yield dict: {"type": "reasoning"|"content", "content": "..."}
                    if isinstance(chunk, dict):
                        if chunk["type"] == "reasoning":
                            full_reasoning.append(chunk["content"])
                            yield f"data: {json.dumps({'reasoning': chunk['content']}, ensure_ascii=False)}\n\n"
                        else:
                            full_response.append(chunk["content"])
                            yield f"data: {json.dumps({'token': chunk['content']}, ensure_ascii=False)}\n\n"
                    else:
                        # 兼容旧格式（纯字符串）
                        full_response.append(chunk)
                        yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.exception("流式对话错误")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            # 保存完整的 assistant 回复（思考过程不保存到消息历史）
            assistant_content = "".join(full_response)
            if assistant_content:
                try:
                    with SessionLocal() as db:
                        crud.add_chat_message(db, chat_session_id, "assistant", assistant_content)
                        if should_consume_quota and quota_user_id:
                            quota_user = crud.get_user_by_id(db, quota_user_id)
                            if quota_user:
                                consume_daily_free_quota(db, quota_user)
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

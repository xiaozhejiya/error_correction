"""Chat-related routes (AI conversation with questions)."""

import json
import logging

from flask import Blueprint, request, jsonify, session, Response

from db import SessionLocal
from db import crud
from db.models import (
    Note,
    NoteTagMapping,
    Project,
    Question,
    ChatSession as ChatSessionModel,
    QuestionTagMapping,
)
from core.model_selection import LLMSelectionError, resolve_llm_selection
from core.quota import (
    consume_daily_free_quota,
    has_daily_free_quota,
    quota_exceeded_response,
    uses_server_llm_selection,
)

logger = logging.getLogger(__name__)

bp = Blueprint("chat", __name__)


def _effective_user_id():
    """管理员返回 None（不过滤），普通用户返回 user_id"""
    if session.get("is_admin"):
        return None
    return session.get("user_id")


def _serialize_chat_session(s) -> dict:
    """将 ChatSession ORM 对象序列化为前端 JSON"""
    return {
        "id": s.public_id,
        "title": s.title or "新对话",
        "question_id": s.question_id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
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
        "id": q.id,
        "question_type": q.question_type,
        "content_json": json.loads(q.content_json) if q.content_json else [],
        "options_json": json.loads(q.options_json) if q.options_json else None,
        "has_formula": q.has_formula,
        "has_image": q.has_image,
        "needs_correction": q.needs_correction,
        "answer": q.answer,
        "subject": subject,
        "knowledge_tags": knowledge_tags,
        "created_at": q.created_at.isoformat() if q.created_at else None,
    }


def _text_from_question(q: Question) -> str:
    parts = []
    if q.question_type:
        parts.append(f"题型：{q.question_type}")
    if q.batch and q.batch.subject:
        parts.append(f"科目：{q.batch.subject}")
    tags = [m.tag.tag_name for m in (q.tags or []) if m.tag]
    if tags:
        parts.append(f"知识点：{', '.join(tags)}")
    try:
        content_blocks = json.loads(q.content_json) if q.content_json else []
    except Exception:
        content_blocks = []
    for block in content_blocks:
        if isinstance(block, dict) and block.get("block_type") == "text":
            text = (block.get("content") or "").strip()
            if text:
                parts.append(text)
    try:
        options = json.loads(q.options_json) if q.options_json else []
    except Exception:
        options = []
    if isinstance(options, list) and options:
        parts.append("选项：" + "；".join(str(opt) for opt in options if opt))
    if q.answer:
        parts.append(f"答案：{q.answer}")
    if q.user_answer:
        parts.append(f"我的笔记/作答：{q.user_answer}")
    return "\n".join(parts)


def _text_from_note(note: Note) -> str:
    parts = [f"标题：{note.title}"]
    if note.subject:
        parts.append(f"科目：{note.subject}")
    tags = [m.tag.tag_name for m in (note.tags or []) if m.tag]
    if tags:
        parts.append(f"知识点：{', '.join(tags)}")
    content = (note.content_markdown or note.ocr_text or "").strip()
    if content:
        parts.append(content)
    return "\n".join(parts)


def _build_project_context(
    db, refs, user_id=None, max_items=20, max_chars=12000
) -> str:
    from sqlalchemy.orm import selectinload

    if not refs:
        return ""
    sections = []
    used = 0

    for ref in refs[:3]:
        if not isinstance(ref, dict):
            continue
        project_type = "note" if ref.get("type") == "note" else "question"
        try:
            project_id = int(ref.get("project_id"))
        except (TypeError, ValueError):
            continue

        project_query = db.query(Project).filter(
            Project.id == project_id,
            Project.project_type == project_type,
        )
        if user_id is not None:
            project_query = project_query.filter(Project.user_id == user_id)
        project = project_query.first()
        if not project:
            continue

        section_lines = [
            f"## 引用{ '笔记本' if project_type == 'note' else '错题库' }：{project.name}"
        ]
        if project_type == "note":
            rows = (
                db.query(Note)
                .options(selectinload(Note.tags).selectinload(NoteTagMapping.tag))
                .filter(Note.project_id == project.id)
                .order_by(Note.updated_at.desc(), Note.created_at.desc())
                .limit(max_items)
                .all()
            )
            for idx, note in enumerate(rows, 1):
                section_lines.append(f"\n### 笔记 {idx}")
                section_lines.append(_text_from_note(note))
        else:
            question_ids = []
            raw_ids = ref.get("question_ids") or []
            if isinstance(raw_ids, list):
                for raw_id in raw_ids[:max_items]:
                    try:
                        question_ids.append(int(raw_id))
                    except (TypeError, ValueError):
                        continue
            if not question_ids:
                continue

            question_query = (
                db.query(Question)
                .options(
                    selectinload(Question.batch),
                    selectinload(Question.tags).selectinload(QuestionTagMapping.tag),
                )
                .filter(Question.project_id == project.id)
            )
            question_query = question_query.filter(Question.id.in_(question_ids))
            rows = question_query.all()
            order = {question_id: idx for idx, question_id in enumerate(question_ids)}
            rows = sorted(rows, key=lambda question: order.get(question.id, len(order)))
            for idx, question in enumerate(rows, 1):
                section_lines.append(f"\n### 错题 {idx}")
                section_lines.append(_text_from_question(question))

        section = "\n".join(line for line in section_lines if line)
        remaining = max_chars - used
        if remaining <= 0:
            break
        if len(section) > remaining:
            section = section[:remaining] + "\n...（引用内容已截断）"
        sections.append(section)
        used += len(section)

    return "\n\n".join(sections)


@bp.route("/question/<int:question_id>/chats", methods=["GET"])
def get_question_chats(question_id):
    """获取某道题目的所有对话会话"""
    try:
        with SessionLocal() as db:
            sessions = crud.get_chat_sessions_by_question(
                db, question_id, user_id=_effective_user_id()
            )
            return jsonify(
                {
                    "success": True,
                    "sessions": [_serialize_chat_session(s) for s in sessions],
                }
            )
    except Exception as e:
        logger.exception("获取对话列表失败")
        return jsonify({"success": False, "error": "获取对话列表失败"}), 500


@bp.route("/chat", methods=["POST"])
def create_chat():
    """创建新对话（支持绑定题目或独立对话）"""
    try:
        data = request.get_json(silent=True) or {}
        question_id = data.get("question_id")  # 可选
        title = data.get("title", "新对话")
        user_id = session.get("user_id")

        if question_id:
            with SessionLocal() as db:
                uid = _effective_user_id()
                q_query = db.query(Question).filter(Question.id == question_id)
                if uid is not None:
                    q_query = q_query.filter(Question.user_id == uid)
                question = q_query.first()
                if not question:
                    return jsonify({"success": False, "error": "题目不存在"}), 404
                chat_session = crud.create_chat_session(
                    db, question_id=question_id, user_id=user_id, title=title
                )
                return jsonify(
                    {"success": True, "session": _serialize_chat_session(chat_session)}
                )
        else:
            # 独立对话
            with SessionLocal() as db:
                chat_session = crud.create_chat_session(
                    db, user_id=user_id, title=title
                )
                return jsonify(
                    {"success": True, "session": _serialize_chat_session(chat_session)}
                )

    except Exception as e:
        logger.exception("创建对话失败")
        return jsonify({"success": False, "error": "创建对话失败"}), 500


@bp.route("/chat/my-sessions", methods=["GET"])
def get_my_chat_sessions():
    """获取当前用户的独立对话列表"""
    try:
        user_id = session.get("user_id")
        page = max(1, request.args.get("page", 1, type=int))
        page_size = min(50, max(1, request.args.get("limit", 20, type=int)))

        with SessionLocal() as db:
            sessions_list, total = crud.get_user_chat_sessions(
                db, user_id, page=page, page_size=page_size
            )
            return jsonify(
                {
                    "success": True,
                    "sessions": [_serialize_chat_session(s) for s in sessions_list],
                    "total": total,
                }
            )
    except Exception as e:
        logger.exception("获取对话列表失败")
        return jsonify({"success": False, "error": "获取对话列表失败"}), 500


@bp.route("/chat/sessions", methods=["GET"])
def get_chat_sessions():
    """分页获取所有对话会话"""
    try:
        page = max(1, request.args.get("page", 1, type=int))
        page_size = min(100, max(1, request.args.get("page_size", 20, type=int)))

        with SessionLocal() as db:
            sessions, total = crud.get_all_chat_sessions(
                db, page=page, page_size=page_size, user_id=_effective_user_id()
            )
            total_pages = (total + page_size - 1) // page_size

            return jsonify(
                {
                    "success": True,
                    "sessions": [_serialize_chat_session(s) for s in sessions],
                    "total": total,
                    "page": page,
                    "total_pages": total_pages,
                }
            )

    except Exception as e:
        logger.exception("获取对话会话列表失败")
        return jsonify({"success": False, "error": "获取对话会话列表失败"}), 500


@bp.route("/chat/<session_id>", methods=["PATCH"])
def update_chat_title(session_id):
    """更新对话标题"""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get("title", "").strip()
        if not title:
            return jsonify({"success": False, "error": "标题不能为空"}), 400

        with SessionLocal() as db:
            cs = crud.get_chat_session_by_public_id(
                db, session_id, user_id=_effective_user_id()
            )
            if not cs:
                return jsonify({"success": False, "error": "对话不存在"}), 404
            s = crud.update_chat_session_title(
                db, cs.id, title, user_id=_effective_user_id()
            )
            if not s:
                return jsonify({"success": False, "error": "对话不存在"}), 404
            return jsonify({"success": True, "session": _serialize_chat_session(s)})
    except Exception as e:
        logger.exception("更新对话标题失败")
        return jsonify({"success": False, "error": "更新失败"}), 500


@bp.route("/chat/<session_id>", methods=["DELETE"])
def delete_chat(session_id):
    """删除对话"""
    try:
        with SessionLocal() as db:
            cs = crud.get_chat_session_by_public_id(
                db, session_id, user_id=_effective_user_id()
            )
            if not cs:
                return jsonify({"success": False, "error": "对话不存在"}), 404
            if not crud.delete_chat_session(db, cs.id, user_id=_effective_user_id()):
                return jsonify({"success": False, "error": "对话不存在"}), 404
            return jsonify({"success": True})
    except Exception as e:
        logger.exception("删除对话失败")
        return jsonify({"success": False, "error": "删除失败"}), 500


@bp.route("/chat/<session_id>/messages", methods=["GET"])
def get_chat_messages(session_id):
    """游标分页获取对话消息"""
    try:
        limit = min(100, max(1, request.args.get("limit", 30, type=int)))
        before_id = request.args.get("before_id", type=int)

        with SessionLocal() as db:
            cs = crud.get_chat_session_by_public_id(
                db, session_id, user_id=_effective_user_id()
            )
            if not cs:
                return jsonify({"success": False, "error": "对话不存在"}), 404
            result = crud.get_chat_messages(
                db,
                cs.id,
                limit=limit,
                before_id=before_id,
                user_id=_effective_user_id(),
            )
            return jsonify(
                {
                    "success": True,
                    "messages": result["messages"],
                    "hasMore": result["hasMore"],
                }
            )

    except Exception as e:
        logger.exception("获取对话消息失败")
        return jsonify({"success": False, "error": "获取对话消息失败"}), 500


@bp.route("/chat/<session_id>/stream", methods=["POST"])
def stream_chat(session_id):
    """SSE 流式对话"""
    from agents.teach import stream_teach
    from sqlalchemy.orm import selectinload

    try:
        data = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()
        model_provider = data.get("model_provider", "openai")
        model_name = data.get("model_name") or None
        provider_source = data.get("provider_source") or None
        provider_id = data.get("provider_id") or None
        deep_think = data.get("deep_think", False)
        context_refs = data.get("context_refs") or []

        # 深度思考模式：切换到 reasoner 模型
        if deep_think and model_provider == "openai":
            model_name = "deepseek-reasoner"

        if not message:
            return jsonify({"success": False, "error": "消息不能为空"}), 400

        user_id = session.get("user_id")
        with SessionLocal() as db:
            uid = _effective_user_id()
            cs_query = (
                db.query(ChatSessionModel)
                .options(
                    selectinload(ChatSessionModel.question).selectinload(
                        Question.batch
                    ),
                    selectinload(ChatSessionModel.question)
                    .selectinload(Question.tags)
                    .selectinload(QuestionTagMapping.tag),
                )
                .filter(ChatSessionModel.public_id == session_id)
            )
            if uid is not None:
                cs_query = cs_query.filter(ChatSessionModel.user_id == uid)
            chat_session = cs_query.first()
            if not chat_session:
                return jsonify({"success": False, "error": "对话不存在"}), 404

            try:
                selection = resolve_llm_selection(
                    db,
                    user_id=user_id,
                    category=model_provider,
                    model_name=model_name,
                    provider_source=provider_source,
                    provider_id=provider_id,
                )
            except LLMSelectionError as e:
                return (
                    jsonify({"success": False, "code": e.code, "error": e.message}),
                    e.status_code,
                )

            should_consume_quota = bool(user_id) and uses_server_llm_selection(
                selection["source"],
                db=db,
                user_id=user_id,
                provider=model_provider,
            )
            quota_user_id = user_id
            if should_consume_quota:
                quota_user = crud.get_user_by_id(db, user_id)
                if not quota_user:
                    session.clear()
                    return jsonify({"success": False, "error": "用户不存在"}), 401
                if not has_daily_free_quota(db, quota_user):
                    payload, status = quota_exceeded_response(db, quota_user)
                    return jsonify(payload), status

            # 独立对话或题目绑定对话
            question = chat_session.question
            q_data = _serialize_question(question) if question else None
            context_prompt = _build_project_context(
                db,
                context_refs,
                user_id=uid,
            )

            # 加载历史消息（最近 20 条）
            history_result = crud.get_chat_messages(db, chat_session.id, limit=20)
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in history_result["messages"]
            ]

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
                    model_name=selection["model_name"],
                    context_prompt=context_prompt,
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
                        crud.add_chat_message(
                            db, chat_session_id, "assistant", assistant_content
                        )
                        if should_consume_quota and quota_user_id:
                            quota_user = crud.get_user_by_id(db, quota_user_id)
                            if quota_user:
                                consume_daily_free_quota(db, quota_user)
                except Exception as e:
                    logger.error(f"保存 assistant 回复失败: {e}")

            yield f"data: {json.dumps({'done': True})}\n\n"

        resp = Response(generate(), mimetype="text/event-stream")
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["X-Accel-Buffering"] = "no"
        return resp

    except Exception as e:
        logger.exception("流式对话失败")
        return jsonify({"success": False, "error": "对话失败，请稍后重试"}), 500

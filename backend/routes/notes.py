"""
笔记模块 API 路由

流程：上传笔记图片 → PaddleOCR 识别 → LLM 整理 → 保存到数据库
"""

import os
import uuid
import json
import logging
from pathlib import PurePath

from flask import Blueprint, request, jsonify, session

from core.config import settings
from core.quota import consume_daily_free_quota, has_daily_free_quota, quota_exceeded_response, uses_server_llm, uses_server_ocr
from db import SessionLocal
from db import crud

logger = logging.getLogger(__name__)

bp = Blueprint('notes', __name__)


def _effective_user_id():
    """管理员返回 None（不过滤），普通用户返回 user_id"""
    if session.get('is_admin'):
        return None
    return session.get('user_id')


def _allowed_image(filename):
    """检查是否为允许的图片格式"""
    return PurePath(filename).suffix.lower().lstrip('.') in {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}


def _serialize_note(note) -> dict:
    """将 Note ORM 对象序列化为前端 JSON"""
    knowledge_tags = []
    if note.tags:
        for mapping in note.tags:
            if mapping.tag:
                knowledge_tags.append(mapping.tag.tag_name)

    return {
        'id': note.id,
        'title': note.title,
        'subject': note.subject,
        'content_markdown': note.content_markdown,
        'source_images': json.loads(note.source_images_json) if note.source_images_json else [],
        'knowledge_tags': knowledge_tags,
        'created_at': note.created_at.isoformat() if note.created_at else None,
        'updated_at': note.updated_at.isoformat() if note.updated_at else None,
    }


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

    ocr_provider = crud.get_active_system_provider(db, 'paddleocr')
    managed_ocr = (
        settings.build_ocr_config(
            api_url=ocr_provider.base_url or '',
            token=ocr_provider.api_key or '',
            model=ocr_provider.model_name or 'PaddleOCR-VL-1.5',
            use_doc_orientation=getattr(ocr_provider, 'use_doc_orientation', False),
            use_doc_unwarping=getattr(ocr_provider, 'use_doc_unwarping', False),
            use_chart_recognition=getattr(ocr_provider, 'use_chart_recognition', False),
        )
        if ocr_provider else {}
    )

    settings.apply_managed_providers(managed_llm, managed_ocr)
    if user_id:
        settings.load_providers_from_db(user_id, db=db)
    else:
        settings.reload_providers()


@bp.route('/', methods=['POST'])
def create_note():
    """上传笔记图片 → OCR → LLM 整理 → 保存

    请求：multipart/form-data
      - files: 一张或多张图片
      - model_provider: 模型供应商（可选，默认 openai）
      - model_name: 模型名称（可选）
    """
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'error': '请上传笔记图片'}), 400

    # 校验文件格式
    for f in files:
        if f.filename and not _allowed_image(f.filename):
            return jsonify({'success': False, 'error': f'不支持的图片格式: {f.filename}'}), 400

    user_id = session.get('user_id')
    model_provider = request.form.get('model_provider', 'openai')
    model_name = request.form.get('model_name') or None

    try:
        should_consume_quota = False
        with SessionLocal() as db:
            if user_id:
                uses_server_side_ocr = uses_server_ocr(db, user_id)
                uses_server_side_llm = uses_server_llm(db, user_id, model_provider)
                should_consume_quota = uses_server_side_ocr or uses_server_side_llm
                if should_consume_quota:
                    quota_user = crud.get_user_by_id(db, user_id)
                    if not quota_user:
                        session.clear()
                        return jsonify({'success': False, 'error': '用户不存在'}), 401
                    if not has_daily_free_quota(db, quota_user):
                        payload, status = quota_exceeded_response(db, quota_user)
                        return jsonify(payload), status

        # 1. 保存上传图片
        saved_paths = []
        for f in files:
            if not f.filename:
                continue
            ext = os.path.splitext(f.filename)[1].lower()
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(str(settings.upload_dir), filename)
            f.save(filepath)
            saved_paths.append(filepath)

        if not saved_paths:
            return jsonify({'success': False, 'error': '没有有效的图片文件'}), 400

        # 2. OCR 识别
        from src.paddleocr_client import PaddleOCRClient
        from src.utils import simplify_ocr_results, run_async

        # 从数据库加载用户 OCR 凭据
        ocr_kwargs = {}
        with SessionLocal() as db:
            _apply_provider_context(db, user_id)
            if user_id:
                ocr_provider = crud.get_active_provider(db, user_id, 'paddleocr')
                if ocr_provider:
                    ocr_kwargs = {
                        "api_url": ocr_provider.base_url,
                        "token": ocr_provider.api_key,
                        "model": ocr_provider.model_name,
                    }

        client = PaddleOCRClient(**ocr_kwargs)
        raw_results = run_async(client.parse_images_async(saved_paths))
        simplified = simplify_ocr_results(raw_results)

        # 拼接 OCR 文本 + 图片引用
        ocr_text_parts = []
        image_refs = []
        for page in simplified:
            for block in page.get('blocks', []):
                label = block.get('block_label', '')
                content = block.get('block_content', '').strip()
                if label in ('image', 'chart') and content:
                    # 图片块：记录路径，在文本中插入占位符
                    image_refs.append(content)
                    ocr_text_parts.append(f'[图片: {content}]')
                elif content:
                    ocr_text_parts.append(content)
        ocr_text = '\n'.join(ocr_text_parts)

        if not ocr_text.strip():
            return jsonify({'success': False, 'error': 'OCR 未识别到任何文字，请检查图片'}), 400

        # 3. LLM 整理
        from agents.note import invoke_note_organize
        result = invoke_note_organize(ocr_text, provider=model_provider, model_name=model_name)

        # 4. 保存到数据库
        with SessionLocal() as db:
            note = crud.save_note(
                db,
                title=result.title,
                subject=result.subject,
                content_markdown=result.content_markdown,
                source_images=saved_paths,
                ocr_text=ocr_text,
                knowledge_tags=result.knowledge_tags,
                user_id=user_id,
            )
            note_id = note.id

        if should_consume_quota and user_id:
            with SessionLocal() as db:
                quota_user = crud.get_user_by_id(db, user_id)
                if quota_user:
                    consume_daily_free_quota(db, quota_user)

        with SessionLocal() as db:
            note = crud.get_note_by_id(db, note_id, user_id=_effective_user_id())
            return jsonify({
                'success': True,
                'note': _serialize_note(note),
            }), 201

    except Exception as e:
        logger.exception("笔记创建失败")
        return jsonify({'success': False, 'error': f'笔记创建失败: {str(e)}'}), 500


@bp.route('/', methods=['GET'])
def list_notes():
    """分页查询笔记列表

    查询参数：page, limit, subject, knowledge_tag, keyword
    """
    try:
        page = max(1, request.args.get('page', 1, type=int))
        limit = min(100, max(1, request.args.get('limit', 20, type=int)))
        subject = request.args.get('subject') or None
        knowledge_tag = request.args.get('knowledge_tag') or None
        keyword = request.args.get('keyword') or None
        user_id = session.get('user_id')

        with SessionLocal() as db:
            notes, total = crud.get_notes(
                db,
                user_id=user_id,
                subject=subject,
                knowledge_tag=knowledge_tag,
                keyword=keyword,
                page=page,
                page_size=limit,
            )
            return jsonify({
                'success': True,
                'items': [_serialize_note(n) for n in notes],
                'total': total,
                'page': page,
                'total_pages': (total + limit - 1) // limit,
            })

    except Exception as e:
        logger.exception("获取笔记列表失败")
        return jsonify({'success': False, 'error': '获取笔记列表失败'}), 500


@bp.route('/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """获取单条笔记详情"""
    try:
        with SessionLocal() as db:
            note = crud.get_note_by_id(db, note_id, user_id=_effective_user_id())
            if not note:
                return jsonify({'success': False, 'error': '笔记不存在'}), 404
            return jsonify({
                'success': True,
                'note': _serialize_note(note),
            })
    except Exception as e:
        logger.exception("获取笔记详情失败")
        return jsonify({'success': False, 'error': '获取笔记详情失败'}), 500


@bp.route('/<int:note_id>', methods=['PATCH'])
def update_note_route(note_id):
    """更新笔记（标题、内容、科目、标签）"""
    try:
        data = request.get_json(silent=True) or {}
        with SessionLocal() as db:
            note = crud.update_note(
                db,
                note_id=note_id,
                title=data.get('title'),
                content_markdown=data.get('content_markdown'),
                subject=data.get('subject'),
                knowledge_tags=data.get('knowledge_tags'),
                user_id=_effective_user_id(),
            )
            if not note:
                return jsonify({'success': False, 'error': '笔记不存在'}), 404
            return jsonify({
                'success': True,
                'note': _serialize_note(note),
            })
    except Exception as e:
        logger.exception("更新笔记失败")
        return jsonify({'success': False, 'error': '更新笔记失败'}), 500


@bp.route('/<int:note_id>', methods=['DELETE'])
def delete_note_route(note_id):
    """删除笔记"""
    try:
        with SessionLocal() as db:
            if not crud.delete_note(db, note_id, user_id=_effective_user_id()):
                return jsonify({'success': False, 'error': '笔记不存在'}), 404
            return jsonify({'success': True})
    except Exception as e:
        logger.exception("删除笔记失败")
        return jsonify({'success': False, 'error': '删除笔记失败'}), 500

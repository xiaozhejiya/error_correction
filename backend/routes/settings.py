import os
import json
import uuid
import logging

import requests as http_requests
from flask import Blueprint, request, jsonify, session

from core.config import settings
from db import SessionLocal
from db import crud
from db.models import ProviderConfig

logger = logging.getLogger(__name__)

bp = Blueprint('settings', __name__)


def _require_admin():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'error': '需要管理员权限'}), 403
    return None


def _managed_llm_from_provider(category: str, provider):
    return settings.build_provider_config(
        category,
        api_key=provider.api_key or '',
        base_url=provider.base_url or '',
        model_name=provider.model_name or None,
        light_model_name=getattr(provider, 'light_model_name', None) or None,
        supports_function_calling=getattr(provider, 'supports_function_calling', True),
    )


def _managed_ocr_from_provider(provider):
    return settings.build_ocr_config(
        api_url=provider.base_url or '',
        token=provider.api_key or '',
        model=provider.model_name or 'PaddleOCR-VL-1.5',
        use_doc_orientation=getattr(provider, 'use_doc_orientation', False),
        use_doc_unwarping=getattr(provider, 'use_doc_unwarping', False),
        use_chart_recognition=getattr(provider, 'use_chart_recognition', False),
    )


def _apply_system_provider_context(db):
    managed_llm = {}
    for category in ('openai', 'anthropic'):
        provider = crud.get_active_system_provider(db, category)
        if provider and provider.api_key:
            managed_llm[category] = _managed_llm_from_provider(category, provider)

    ocr_provider = crud.get_active_system_provider(db, 'paddleocr')
    managed_ocr = _managed_ocr_from_provider(ocr_provider) if ocr_provider else {}
    settings.apply_managed_providers(managed_llm, managed_ocr)
    return managed_llm, managed_ocr


@bp.route('/models/erase', methods=['POST'])
def erase_text():
    """文字擦除接口

    使用 GAN 模型将试卷图片中的手写笔迹擦除，还原干净的题目底图。

    Request:
        multipart/form-data，字段 file：图片文件（JPEG/PNG/BMP 等）

    Response:
        {"success": true, "result_url": "/erased/<filename>"}
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '缺少 file 字段'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'success': False, 'error': '文件为空'}), 400

    ext = os.path.splitext(file.filename)[1].lower() or '.png'
    allowed = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    if ext not in allowed:
        return jsonify({'success': False, 'error': f'不支持的图片格式: {ext}'}), 400

    try:
        image_bytes = file.read()
    except Exception:
        return jsonify({'success': False, 'error': '读取文件失败'}), 400

    try:
        from models.inference import InferenceEngine

        result_img = InferenceEngine().run(image_bytes)

        filename = uuid.uuid4().hex + '.png'
        save_path = settings.erased_dir / filename
        result_img.save(save_path, format='PNG')

        return jsonify({'success': True, 'result_url': f'/erased/{filename}'})

    except FileNotFoundError as e:
        logger.error("模型权重缺失: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 503
    except Exception:
        logger.exception("文字擦除失败")
        return jsonify({'success': False, 'error': '擦除处理失败，请稍后重试'}), 500


@bp.route('/status', methods=['GET'])
def get_status():
    """
    获取系统状态

    Returns:
        JSON响应，包含系统配置和状态
    """
    try:
        user_id = session.get('user_id')

        # 检查 EnsExam 模型权重是否存在
        ensexam_configured = settings.model_path.exists()

        if user_id:
            # 已登录：从数据库读取用户配置
            with SessionLocal() as db:
                paddle_provider = crud.get_active_provider(db, user_id, 'paddleocr')
                paddleocr_configured = bool(paddle_provider and paddle_provider.api_key and paddle_provider.base_url)

                # 构建用户级可用模型列表
                available_models = []
                for category, label in [('openai', 'OpenAI'), ('anthropic', 'Anthropic')]:
                    provider = crud.get_active_provider(db, user_id, category)
                    if provider and provider.api_key:
                        available_models.append({
                            'value': category,
                            'label': provider.name or label,
                            'configured': True,
                            'status': '配置成功',
                            'default_model': provider.model_name or '',
                            'models': [provider.model_name] if provider.model_name else [],
                        })
                    else:
                        available_models.append({
                            'value': category,
                            'label': label,
                            'configured': False,
                            'status': '未配置',
                            'default_model': '',
                            'models': [],
                        })
        else:
            # 未登录：返回空状态
            paddleocr_configured = False
            available_models = []

        status = {
            'paddleocr_configured': paddleocr_configured,
            'ensexam_configured': ensexam_configured,
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


@bp.route('/config', methods=['GET'])
def get_config():
    """获取当前用户的 provider 配置"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        with SessionLocal() as db:
            config = crud.get_user_providers(db, user_id)
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        logger.exception("获取配置失败")
        return jsonify({'success': False, 'error': '获取配置失败'}), 500


@bp.route('/config', methods=['PUT'])
def update_config():
    """保存当前用户的 provider 配置到数据库"""
    try:
        data = request.get_json(force=True) or {}
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401

        with SessionLocal() as db:
            try:
                crud.save_user_providers(db, user_id, data)
                _apply_system_provider_context(db)
                settings.load_providers_from_db(user_id)
            except Exception:
                db.rollback()
                raise
        return jsonify({'success': True})

    except Exception as e:
        logger.exception("更新配置失败")
        return jsonify({'success': False, 'error': '更新配置失败，请检查日志'}), 500


@bp.route('/models/list', methods=['POST'])
def list_models():
    """代理请求目标 API 的模型列表，绕过浏览器 CORS 限制。

    请求体:
        type: 'openai' | 'anthropic'
        api_key: API Key（可选，留空则使用系统已配置的 key）
        base_url: Base URL（可选）
        provider_id: 已有 provider 的 id（可选，用于回退读取已存 key）
    """
    try:
        data = request.get_json(force=True) or {}
        provider_type = data.get('type', 'openai')
        api_key = data.get('api_key') or ''
        base_url = data.get('base_url') or ''

        if not api_key:
            user_id = session.get('user_id')
            provider_id = data.get('provider_id')
            with SessionLocal() as db:
                _, _ = _apply_system_provider_context(db)
                if user_id:
                    if provider_id:
                        provider = db.query(ProviderConfig).filter_by(id=provider_id, user_id=user_id).first()
                    else:
                        provider = crud.get_active_provider(db, user_id, provider_type)
                    if provider:
                        api_key = api_key or provider.api_key or ''
                        base_url = base_url or provider.base_url or ''
                if not api_key and provider_type in ('openai', 'anthropic'):
                    system_provider = crud.get_active_system_provider(db, provider_type)
                    if system_provider:
                        api_key = system_provider.api_key or ''
                        base_url = base_url or system_provider.base_url or ''
            if not api_key and provider_type in ('openai', 'anthropic'):
                managed_cfg = settings.get_managed_provider(provider_type)
                api_key = api_key or managed_cfg.api_key or ''
                base_url = base_url or managed_cfg.base_url or ''

        if not api_key:
            return jsonify({'error': '未提供 API Key，请先在设置中配置，或联系管理员配置平台托管 provider'}), 400

        if provider_type == 'openai':
            url = (base_url.rstrip('/') if base_url else 'https://api.openai.com') + '/v1/models'
            headers = {'Authorization': f'Bearer {api_key}'}
            resp = http_requests.get(url, headers=headers, timeout=15)

            # 部分 OpenAI 兼容 API 的路径可能不带 /v1
            if resp.status_code == 404:
                url_alt = (base_url.rstrip('/') if base_url else 'https://api.openai.com') + '/models'
                resp = http_requests.get(url_alt, headers=headers, timeout=15)

            if resp.status_code != 200:
                return jsonify({'error': f'API 返回 {resp.status_code}: {resp.text[:200]}'}), 502

            body = resp.json()
            models = sorted([m['id'] for m in body.get('data', [])]) if 'data' in body else []
            return jsonify({'models': models})

        elif provider_type == 'anthropic':
            # Anthropic 没有官方 list models 接口，返回常用模型列表
            models = [
                'claude-opus-4-20250514',
                'claude-sonnet-4-20250514',
                'claude-haiku-4-20250506',
                'claude-3-5-sonnet-20241022',
                'claude-3-5-haiku-20241022',
                'claude-3-opus-20240229',
            ]
            return jsonify({'models': models})

        else:
            return jsonify({'error': f'不支持的 provider 类型: {provider_type}'}), 400

    except http_requests.Timeout:
        return jsonify({'error': '请求超时，请检查 Base URL 是否正确'}), 504
    except http_requests.ConnectionError:
        return jsonify({'error': '无法连接目标 API，请检查 Base URL'}), 502
    except Exception as e:
        logger.exception("获取模型列表失败")
        return jsonify({'error': str(e)}), 500


@bp.route('/paddleocr/test', methods=['POST'])
def test_paddleocr():
    """测试 PaddleOCR API Token 是否可用。

    请求体:
        api_token: API Token（可选，留空则从数据库读取）
        api_url: API URL（可选，留空则从数据库读取）
        provider_id: 已有 provider 的 id（可选，用于回退读取已存 token）
    """
    try:
        data = request.get_json(force=True) or {}
        api_token = data.get('api_token') or ''
        api_url = data.get('api_url') or ''

        if not api_token or not api_url:
            user_id = session.get('user_id')
            provider_id = data.get('provider_id')
            with SessionLocal() as db:
                _, managed_ocr = _apply_system_provider_context(db)
                if user_id:
                    if provider_id:
                        provider = db.query(ProviderConfig).filter_by(id=provider_id, user_id=user_id).first()
                    else:
                        provider = crud.get_active_provider(db, user_id, 'paddleocr')
                    if provider:
                        api_token = api_token or provider.api_key or ''
                        api_url = api_url or provider.base_url or ''
                if not api_token or not api_url:
                    system_provider = crud.get_active_system_provider(db, 'paddleocr')
                    if system_provider:
                        api_token = api_token or system_provider.api_key or ''
                        api_url = api_url or system_provider.base_url or ''
            if managed_ocr:
                api_token = api_token or managed_ocr.get('token', '')
                api_url = api_url or managed_ocr.get('api_url', '')

        if not api_token or not api_url:
            return jsonify({'error': '未提供 API Token 或 API URL，请先在设置中配置，或联系管理员配置平台托管 OCR'}), 400

        # 用 GET 请求 API URL，带 token 验证认证是否有效
        headers = {'Authorization': f'bearer {api_token}'}
        resp = http_requests.get(api_url, headers=headers, timeout=10)

        # 401/403 表示 token 无效
        if resp.status_code in (401, 403):
            return jsonify({'success': False, 'error': '认证失败，请检查 API Token 是否正确'})

        # 其他非 5xx 状态码都认为 token 有效（包括 404/405 等，因为 GET 可能不被支持但认证通过了）
        if resp.status_code >= 500:
            return jsonify({'success': False, 'error': f'服务端错误 ({resp.status_code})，请检查 API URL'})

        return jsonify({'success': True, 'message': 'API Token 验证通过'})

    except http_requests.Timeout:
        return jsonify({'success': False, 'error': '请求超时，请检查 API URL 是否正确'}), 504
    except http_requests.ConnectionError:
        return jsonify({'success': False, 'error': '无法连接，请检查 API URL'}), 502
    except Exception as e:
        logger.exception("测试 PaddleOCR 连接失败")
        return jsonify({'success': False, 'error': str(e)}), 500

import os
import json
import uuid
import logging
from pathlib import PurePath
from typing import Optional

from flask import Blueprint, request, jsonify, session

import core.state as state
from core.state import (
    workflow_graph,
    session_lock,
    get_user_session,
)
from db import SessionLocal
from db import crud
from core.config import settings
from core.quota import consume_daily_free_quota, has_daily_free_quota, quota_exceeded_response, uses_server_llm, uses_server_ocr
from src.utils import export_wrongbook as export_wrongbook_md

logger = logging.getLogger(__name__)

bp = Blueprint('upload', __name__)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return PurePath(filename).suffix.lower().lstrip('.') in settings.allowed_extensions


def _read_split_subject() -> Optional[str]:
    """从 split_metadata.json 读取学科信息"""
    meta_path = os.path.join(str(settings.results_dir), "split_metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f).get("subject")
    return None


def _serialize_split_record(r) -> dict:
    """将 SplitRecord ORM 对象序列化为前端 JSON 格式"""
    return {
        "id": r.id,
        "subject": r.subject,
        "model_provider": r.model_provider,
        "file_names": json.loads(r.file_names_json) if r.file_names_json else [],
        "question_count": r.question_count,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _apply_provider_context(db, user_id: Optional[int]) -> None:
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


def _ocr_cache_key(user_id: Optional[int]) -> str:
    return str(user_id) if user_id is not None else "anon"


def _ocr_cache_path(user_id: Optional[int]) -> str:
    return os.path.join(str(settings.results_dir), f"ocr_cache_{_ocr_cache_key(user_id)}.json")


def _clear_ocr_cache(user_id: Optional[int]) -> None:
    cache_path = _ocr_cache_path(user_id)
    try:
        os.remove(cache_path)
    except FileNotFoundError:
        pass


def _mark_server_ocr_cache(user_id: Optional[int], value: bool) -> None:
    with session_lock:
        us = get_user_session(user_id)
        us["ocr_cache_uses_server_ocr"] = bool(value)


def _has_server_ocr_cache(user_id: Optional[int]) -> bool:
    with session_lock:
        cached = bool(get_user_session(user_id).get("ocr_cache_uses_server_ocr"))
    return cached and os.path.exists(_ocr_cache_path(user_id))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bp.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传（支持多文件）。

    这里只负责把原始文件保存到 uploads 并登记到会话中；
    标准化(PDF/图片 → 图片列表) + OCR + 分割，会在 /api/split 里由用户点击"开始分割"后统一触发。

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
        uid = session.get('user_id')
        for fk, file in prepared:
            file_key = fk or f"{uuid.uuid4().hex}"

            original_ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
            filename = f"{uuid.uuid4().hex}.{original_ext}"
            filepath = os.path.join(str(settings.upload_dir), filename)
            file.save(filepath)

            with session_lock:
                us = get_user_session(uid)
                cancelled = file_key in us["cancelled_file_keys"]
                if cancelled:
                    us["cancelled_file_keys"].discard(file_key)

            if cancelled:
                try:
                    os.remove(filepath)
                except FileNotFoundError:
                    pass
                continue

            with session_lock:
                us = get_user_session(uid)
                if us["current_thread_id"] is not None:
                    us["current_thread_id"] = None
                    us["session_files"].clear()
                    us["session_file_order"].clear()
                    us["ocr_cache_uses_server_ocr"] = False
                    _clear_ocr_cache(uid)

                us["session_files"][file_key] = {
                    "filename": file.filename,
                    "filepath": filepath,
                }
                if file_key not in us["session_file_order"]:
                    us["session_file_order"].append(file_key)
                us["ocr_cache_uses_server_ocr"] = False
                _clear_ocr_cache(uid)

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


@bp.route('/cancel_file', methods=['POST'])
def cancel_file():
    try:
        data = request.get_json(silent=True) or {}
        file_key = data.get('file_key')
        if not file_key:
            return jsonify({
                'success': False,
                'error': '缺少 file_key'
            }), 400

        uid = session.get('user_id')
        with session_lock:
            us = get_user_session(uid)
            if us["current_thread_id"] is not None:
                return jsonify({
                    'success': False,
                    'error': '已开始分割，无法撤销单个文件；请重置后重新上传'
                }), 400

        filepath = None
        existed = False
        with session_lock:
            us = get_user_session(uid)
            us["cancelled_file_keys"].add(file_key)

            existed = file_key in us["session_files"]
            v = us["session_files"].pop(file_key, None) or {}
            filepath = v.get('filepath')
            if file_key in us["session_file_order"]:
                us["session_file_order"].remove(file_key)
            us["ocr_cache_uses_server_ocr"] = False
            _clear_ocr_cache(uid)


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


@bp.route('/erase', methods=['POST'])
def run_erase():
    """擦除手写笔迹，返回擦除后的图片 URL。

    擦除后的文件路径保存在会话状态中，供后续 /api/ocr 使用。
    """
    try:
        uid = session.get('user_id')
        with session_lock:
            us = get_user_session(uid)
            keys = list(us["session_file_order"])
            file_paths = []
            for k in keys:
                v = us["session_files"].get(k) or {}
                fp = v.get('filepath')
                if fp:
                    file_paths.append(fp)

        if not file_paths:
            return jsonify({'success': False, 'error': '请先上传文件'}), 400

        ensexam_configured = settings.model_path.exists()
        if not ensexam_configured:
            return jsonify({'success': False, 'error': 'EnsExam 模型未配置'}), 400

        from models.inference import InferenceEngine
        engine = InferenceEngine()
        erased_paths = []
        for fp in file_paths:
            with open(fp, 'rb') as f:
                img_bytes = f.read()
            result_img = engine.run(img_bytes)
            erased_name = f"auto_{uuid.uuid4().hex[:8]}_{os.path.splitext(os.path.basename(fp))[0]}.png"
            erased_path = settings.erased_dir / erased_name
            result_img.save(str(erased_path), format='PNG')
            erased_paths.append(str(erased_path))

        # 保存擦除后的路径到会话，供 /api/ocr 复用
        with session_lock:
            us = get_user_session(uid)
            us["erased_file_paths"] = erased_paths
            us["ocr_cache_uses_server_ocr"] = False
        _clear_ocr_cache(uid)

        preview = []
        for i, (orig, erased) in enumerate(zip(file_paths, erased_paths)):
            preview.append({
                "index": i,
                "original_url": f"/api/image/{os.path.basename(orig)}",
                "erased_url": f"/api/image/{os.path.basename(erased)}",
            })

        return jsonify({
            'success': True,
            'message': f'擦除完成，共 {len(erased_paths)} 张图片',
            'images': preview,
        })

    except Exception:
        logger.exception("擦除手写笔迹失败")
        return jsonify({'success': False, 'error': '擦除失败，请稍后重试'}), 500


@bp.route('/ocr', methods=['POST'])
def run_ocr():
    """只执行 OCR，返回识别结果供用户预览。

    流程：标准化输入 → OCR 解析 → 返回结构化文本
    不触发 Agent 分割。
    如果之前调用过 /api/erase，则使用擦除后的图片。
    """
    try:
        # 加载 OCR 凭据
        user_id = session.get('user_id')
        ocr_credentials = {}
        _mark_server_ocr_cache(user_id, False)
        with SessionLocal() as db:
            _apply_provider_context(db, user_id)
            if user_id:
                ocr_provider = crud.get_active_provider(db, user_id, 'paddleocr')
                if ocr_provider:
                    ocr_credentials = {
                        "api_url": ocr_provider.base_url,
                        "token": ocr_provider.api_key,
                        "model": ocr_provider.model_name,
                        "use_doc_orientation": ocr_provider.use_doc_orientation,
                        "use_doc_unwarping": ocr_provider.use_doc_unwarping,
                        "use_chart_recognition": ocr_provider.use_chart_recognition,
                    }

        # 优先使用擦除后的路径
        file_paths = None
        with session_lock:
            us = get_user_session(user_id)
            if us["erased_file_paths"]:
                file_paths = list(us["erased_file_paths"])
                us["erased_file_paths"] = None  # 用完即清

        if not file_paths:
            with session_lock:
                us = get_user_session(user_id)
                keys = list(us["session_file_order"])
                file_paths = []
                for k in keys:
                    v = us["session_files"].get(k) or {}
                    fp = v.get('filepath')
                    if fp:
                        file_paths.append(fp)

        if not file_paths:
            return jsonify({'success': False, 'error': '请先上传文件'}), 400

        # 标准化输入（PDF → 图片）
        from src.utils import prepare_input
        all_image_paths = []
        for fp in file_paths:
            all_image_paths.extend(prepare_input(fp))

        # 执行 OCR（获取原始结果用于预览 bbox，简化结果用于后续分割）
        from src.paddleocr_client import PaddleOCRClient
        from src.utils import simplify_ocr_results
        from src.workflow import run_async

        creds = ocr_credentials or {}
        client = PaddleOCRClient(
            api_url=creds.get("api_url"),
            token=creds.get("token"),
            model=creds.get("model"),
            use_doc_orientation=creds.get("use_doc_orientation"),
            use_doc_unwarping=creds.get("use_doc_unwarping"),
            use_chart_recognition=creds.get("use_chart_recognition"),
        )

        # 按文件类型分组
        pdf_paths = [p for p in all_image_paths if p.lower().endswith(".pdf")]
        image_only = [p for p in all_image_paths if not p.lower().endswith(".pdf")]

        raw_ocr_results = []
        for pdf_path in pdf_paths:
            try:
                raw_ocr_results.append(client.parse_pdf(pdf_path, save_output=True))
            except Exception:
                logger.exception(f"OCR PDF 失败: {pdf_path}")
        if image_only:
            try:
                img_results = run_async(client.parse_images_async(image_only, save_output=True))
                if img_results:
                    raw_ocr_results.extend(img_results)
            except Exception:
                logger.exception("OCR 图片失败")

        if not raw_ocr_results:
            return jsonify({'success': False, 'error': 'OCR 解析失败，请检查 PaddleOCR 配置'}), 500

        # 简化结果用于后续分割
        ocr_data = simplify_ocr_results(raw_ocr_results)

        # 保存 OCR 结果到会话，供后续 /api/split 复用
        import json
        results_dir = str(settings.results_dir)
        os.makedirs(results_dir, exist_ok=True)
        ocr_cache_path = _ocr_cache_path(user_id)
        with open(ocr_cache_path, 'w', encoding='utf-8') as f:
            json.dump(ocr_data, f, ensure_ascii=False, indent=2)
        _mark_server_ocr_cache(user_id, False)

        # 构建前端预览数据：每页的图片 + bbox 标注
        preview_pages = []
        page_idx = 0
        for result in raw_ocr_results:
            for layout_page in result.get("layoutParsingResults", []):
                pruned = layout_page.get("prunedResult", {})
                page_w = pruned.get("width", 1)
                page_h = pruned.get("height", 1)
                parsing_list = pruned.get("parsing_res_list", [])

                blocks = []
                for b in parsing_list:
                    bbox = b.get("block_bbox")
                    if not bbox:
                        continue
                    blocks.append({
                        "label": b.get("block_label", ""),
                        "content": (b.get("block_content", "") or "")[:80],
                        "bbox": bbox,
                    })

                image_path = all_image_paths[page_idx] if page_idx < len(all_image_paths) else None
                image_url = f"/api/image/{os.path.basename(image_path)}" if image_path else None

                preview_pages.append({
                    "page_index": page_idx,
                    "image_url": image_url,
                    "page_width": page_w,
                    "page_height": page_h,
                    "blocks": blocks,
                })
                page_idx += 1

        return jsonify({
            'success': True,
            'message': f'OCR 完成，共 {len(preview_pages)} 页',
            'pages': preview_pages,
            'total_blocks': sum(len(p["blocks"]) for p in preview_pages),
        })

    except Exception:
        logger.exception("OCR 执行失败")
        return jsonify({'success': False, 'error': 'OCR 执行失败，请稍后重试'}), 500


@bp.route('/split', methods=['POST'])
def split_questions():
    """开始执行标准化 + OCR + 分割。

    用户点击前端"开始分割题目"后调用该接口：
    - 标准化输入（PDF/图片 → 图片列表）
    - 触发 Agent/OCR 并分割题目

    Returns:
        JSON响应，包含分割后的题目
    """
    try:
        # 读取请求体参数（模型供应商 + 模型名称）
        data = request.get_json(silent=True) or {}
        model_provider = data.get("model_provider", "openai")
        model_name = data.get("model_name")  # 可选，None 时使用 provider 默认模型
        if not settings.is_valid_provider(model_provider):
            return jsonify({
                'success': False,
                'error': f'不支持的模型供应商: {model_provider}'
            }), 400

        # 从数据库加载用户的 LLM + OCR 凭据
        user_id = session.get('user_id')
        ocr_credentials = {}
        should_consume_quota = False
        with SessionLocal() as db:
            _apply_provider_context(db, user_id)
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

                ocr_provider = crud.get_active_provider(db, user_id, 'paddleocr')
                if ocr_provider:
                    ocr_credentials = {
                        "api_url": ocr_provider.base_url,
                        "token": ocr_provider.api_key,
                        "model": ocr_provider.model_name,
                        "use_doc_orientation": ocr_provider.use_doc_orientation,
                        "use_doc_unwarping": ocr_provider.use_doc_unwarping,
                        "use_chart_recognition": ocr_provider.use_chart_recognition,
                    }

        with session_lock:
            us = get_user_session(user_id)
            keys = list(us["session_file_order"])
            file_paths = []
            for k in keys:
                v = us["session_files"].get(k) or {}
                fp = v.get('filepath')
                if fp:
                    file_paths.append(fp)

        if not file_paths:
            return jsonify({
                'success': False,
                'error': '请先上传文件'
            }), 400

        with session_lock:
            us = get_user_session(user_id)
            us["current_thread_id"] = str(uuid.uuid4())
            thread_id = us["current_thread_id"]
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "file_paths": file_paths,
            "model_provider": model_provider,
            "model_name": model_name,
            "ocr_credentials": ocr_credentials,
            "ocr_cache_path": _ocr_cache_path(user_id),
        }
        workflow_graph.invoke(initial_state, config=config)
        result_state = workflow_graph.invoke(None, config=config)
        _mark_server_ocr_cache(user_id, False)

        questions = result_state.get('questions', [])
        warnings = result_state.get('warnings', [])

        # 自动保存分割记录
        try:
            subject = _read_split_subject()

            with session_lock:
                us = get_user_session(user_id)
                file_names = [
                    us["session_files"].get(k, {}).get("filename", "未知")
                    for k in us["session_file_order"]
                ]

            with SessionLocal() as db:
                crud.save_split_record(db, subject, model_provider, file_names, questions, user_id=user_id)
        except Exception:
            logger.warning("保存分割记录失败，不影响主流程", exc_info=True)

        if should_consume_quota and user_id:
            with SessionLocal() as db:
                quota_user = crud.get_user_by_id(db, user_id)
                if quota_user:
                    consume_daily_free_quota(db, quota_user)

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


@bp.route('/split-records', methods=['GET'])
def get_split_records():
    """获取最近 N 次分割历史记录，limit 由前端通过查询参数指定"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = max(1, min(limit, crud.MAX_SPLIT_RECORDS))  # 上限与保留条数一致

        with SessionLocal() as db:
            records = crud.get_recent_split_records(db, limit, user_id=session.get('user_id'))
            result = [_serialize_split_record(r) for r in records]

        return jsonify({"success": True, "records": result})

    except Exception as e:
        logger.exception("获取分割记录失败")
        return jsonify({"success": False, "error": "获取分割记录失败"}), 500


@bp.route('/split-records/<int:record_id>', methods=['GET'])
def get_split_record_detail(record_id):
    """获取单条分割记录的完整数据（含 questions）"""
    try:
        with SessionLocal() as db:
            uid = None if session.get('is_admin') else session.get('user_id')
            record = crud.get_split_record_by_id(db, record_id, user_id=uid)
            if not record:
                return jsonify({"success": False, "error": "记录不存在"}), 404

            result = _serialize_split_record(record)
            result["questions"] = json.loads(record.questions_json) if record.questions_json else []

        return jsonify({"success": True, "record": result})

    except Exception as e:
        logger.exception("获取分割记录详情失败")
        return jsonify({"success": False, "error": "获取分割记录详情失败"}), 500


@bp.route('/export', methods=['POST'])
def export_wrongbook():
    """
    注入选中题目 ID 并恢复图执行导出

    图执行: export → END

    Returns:
        JSON响应，包含导出文件路径
    """
    try:
        data = request.get_json(silent=True) or {}
        selected_uids = data.get('selected_ids', [])

        if not isinstance(selected_uids, list):
            return jsonify({
                'success': False,
                'error': 'selected_ids 必须为列表'
            }), 400

        if not selected_uids:
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
            selected_uids,
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


@bp.route('/image/<filename>')
def serve_image(filename):
    """提供上传/处理后的图片文件访问（OCR 预览用）"""
    from flask import send_from_directory
    # 在多个目录中查找
    for d in [settings.upload_dir, settings.erased_dir, settings.results_dir, settings.pages_dir]:
        path = os.path.join(str(d), filename)
        if os.path.exists(path):
            return send_from_directory(str(d), filename)
    return jsonify({'error': 'File not found'}), 404

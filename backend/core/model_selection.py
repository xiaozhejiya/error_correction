from __future__ import annotations

from dataclasses import dataclass

from core.config import settings
from db import crud


MODEL_OPTION_NOT_FOUND = "MODEL_OPTION_NOT_FOUND"
MODEL_PROVIDER_NOT_CONFIGURED = "MODEL_PROVIDER_NOT_CONFIGURED"
MODEL_NOT_ALLOWED = "MODEL_NOT_ALLOWED"
INVALID_PROVIDER_SOURCE = "INVALID_PROVIDER_SOURCE"

LLM_CATEGORIES = ("openai", "anthropic")


@dataclass
class LLMSelectionError(Exception):
    code: str
    message: str
    status_code: int = 400


def split_models(model_name: str | None) -> list[str]:
    return [item.strip() for item in (model_name or "").split(",") if item.strip()]


def build_managed_provider_context(db):
    managed_llm = {}
    for category in LLM_CATEGORIES:
        provider = crud.get_active_system_provider(db, category)
        if provider and provider.api_key:
            managed_llm[category] = settings.build_provider_config(
                category,
                api_key=provider.api_key or "",
                base_url=provider.base_url or "",
                model_name=provider.model_name or None,
                light_model_name=getattr(provider, "light_model_name", None) or None,
                supports_function_calling=getattr(
                    provider, "supports_function_calling", True
                ),
            )

    ocr_provider = crud.get_active_system_provider(db, "paddleocr")
    managed_ocr = (
        settings.build_ocr_config(
            api_url=ocr_provider.base_url or "",
            token=ocr_provider.api_key or "",
            model=ocr_provider.model_name or "PaddleOCR-VL-1.5",
            use_doc_orientation=getattr(ocr_provider, "use_doc_orientation", False),
            use_doc_unwarping=getattr(ocr_provider, "use_doc_unwarping", False),
            use_chart_recognition=getattr(ocr_provider, "use_chart_recognition", False),
        )
        if ocr_provider
        else {}
    )
    settings.apply_managed_providers(managed_llm, managed_ocr)
    return managed_llm, managed_ocr


def list_model_options(db, user_id: int | None) -> dict[str, object]:
    options = []

    def append_options(source: str, category: str, provider, group_label: str):
        models = split_models(getattr(provider, "model_name", ""))
        if not models:
            return
        configured = bool(getattr(provider, "api_key", ""))
        for idx, model in enumerate(models):
            options.append(
                {
                    "option_id": f"{source}:{category}:{provider.id}:{model}",
                    "source": source,
                    "category": category,
                    "provider_id": provider.id,
                    "provider_name": provider.name or category.upper(),
                    "model_name": model,
                    "label": model,
                    "group_label": group_label,
                    "configured": configured,
                    "available": configured,
                    "reason": "" if configured else "API Key 未配置",
                    "is_default": bool(
                        getattr(provider, "is_active", False) and idx == 0
                    ),
                    "supports_function_calling": getattr(
                        provider, "supports_function_calling", True
                    ),
                }
            )

    # 查询 ORM 对象时直接按类别读取，避免依赖序列化结构。
    from db.models import ProviderConfig, SystemProviderConfig

    system_items = (
        db.query(SystemProviderConfig)
        .filter(SystemProviderConfig.category.in_(LLM_CATEGORIES))
        .order_by(SystemProviderConfig.created_at)
        .all()
    )
    for provider in system_items:
        append_options("system", provider.category, provider, "平台托管")

    if user_id:
        personal_items = (
            db.query(ProviderConfig)
            .filter(
                ProviderConfig.user_id == user_id,
                ProviderConfig.category.in_(LLM_CATEGORIES),
            )
            .order_by(ProviderConfig.created_at)
            .all()
        )
        for provider in personal_items:
            append_options("personal", provider.category, provider, "个人配置")

    default_option_id = None
    for category in LLM_CATEGORIES:
        personal_provider = (
            crud.get_active_provider(db, user_id, category) if user_id else None
        )
        personal_models = split_models(
            getattr(personal_provider, "model_name", "") if personal_provider else ""
        )
        if personal_provider and personal_provider.api_key and personal_models:
            default_option_id = (
                f"personal:{category}:{personal_provider.id}:{personal_models[0]}"
            )
            break

        system_provider = crud.get_active_system_provider(db, category)
        system_models = split_models(
            getattr(system_provider, "model_name", "") if system_provider else ""
        )
        if system_provider and system_provider.api_key and system_models:
            default_option_id = (
                f"system:{category}:{system_provider.id}:{system_models[0]}"
            )
            break

    if default_option_id is None:
        first_available = next((item for item in options if item["available"]), None)
        default_option_id = first_available["option_id"] if first_available else None

    return {
        "options": options,
        "default_option_id": default_option_id,
        "groups": [
            {"key": "system", "label": "平台托管"},
            {"key": "personal", "label": "个人配置"},
        ],
    }


def resolve_llm_selection(
    db,
    *,
    user_id: int | None,
    category: str,
    model_name: str | None = None,
    provider_source: str | None = None,
    provider_id: str | None = None,
):
    if category not in LLM_CATEGORIES:
        raise LLMSelectionError(
            MODEL_OPTION_NOT_FOUND,
            f"不支持的模型供应商: {category}",
            400,
        )

    managed_llm, managed_ocr = build_managed_provider_context(db)
    strict_selection = bool(provider_source or provider_id)

    if not strict_selection:
        if user_id:
            provider = crud.get_active_provider(db, user_id, category)
            if provider and provider.api_key:
                source = "personal"
            else:
                provider = crud.get_active_system_provider(db, category)
                source = "system"
        else:
            provider = crud.get_active_system_provider(db, category)
            source = "system"
    else:
        if provider_source not in {"system", "personal"}:
            raise LLMSelectionError(
                INVALID_PROVIDER_SOURCE,
                "模型来源无效，请重新选择模型。",
                400,
            )
        if not provider_id:
            raise LLMSelectionError(
                MODEL_OPTION_NOT_FOUND,
                "模型配置不存在，请重新选择模型。",
                404,
            )
        source = provider_source
        if source == "system":
            provider = crud.get_active_system_provider(db, category)
            if not provider or provider.id != provider_id:
                from db.models import SystemProviderConfig

                provider = (
                    db.query(SystemProviderConfig)
                    .filter(
                        SystemProviderConfig.id == provider_id,
                        SystemProviderConfig.category == category,
                    )
                    .first()
                )
            if not provider:
                raise LLMSelectionError(
                    MODEL_OPTION_NOT_FOUND,
                    "平台模型不可用：该配置已被删除，请重新选择模型。",
                    404,
                )
        else:
            if not user_id:
                raise LLMSelectionError(
                    MODEL_OPTION_NOT_FOUND,
                    "个人模型不可用：请先登录后再试。",
                    401,
                )
            from db.models import ProviderConfig

            provider = (
                db.query(ProviderConfig)
                .filter(
                    ProviderConfig.id == provider_id,
                    ProviderConfig.user_id == user_id,
                    ProviderConfig.category == category,
                )
                .first()
            )
            if not provider:
                raise LLMSelectionError(
                    MODEL_OPTION_NOT_FOUND,
                    "个人模型不可用：该配置已被删除，请重新选择模型。",
                    404,
                )

    if not provider or not getattr(provider, "api_key", ""):
        # 尝试回退到 settings 中的默认配置
        default_key = getattr(settings, f"default_{category}_api_key", None)
        if source == "system" and default_key:
            # 构造一个临时的 provider 对象或直接返回配置
            selected_model_name = model_name or getattr(settings, f"default_{category}_model_name", "gpt-4o-mini")
            
            request_registry = {
                name: settings.get_managed_provider(name) for name in LLM_CATEGORIES
            }
            request_registry[category] = settings.build_provider_config(
                category,
                api_key=default_key,
                base_url=getattr(settings, f"default_{category}_base_url", ""),
                model_name=getattr(settings, f"default_{category}_model_name", None),
                light_model_name=getattr(settings, f"default_{category}_light_model_name", None),
                supports_function_calling=getattr(settings, f"default_{category}_supports_function_calling", True),
            )
            settings.activate_request_providers(request_registry)

            return {
                "source": "system",
                "category": category,
                "provider_id": "default",
                "provider_name": f"Default {category.upper()}",
                "model_name": selected_model_name,
                "api_key": default_key,
                "base_url": getattr(settings, f"default_{category}_base_url", ""),
                "supports_function_calling": getattr(settings, f"default_{category}_supports_function_calling", True),
                "managed_llm": managed_llm,
                "managed_ocr": managed_ocr,
            }

        raise LLMSelectionError(
            MODEL_PROVIDER_NOT_CONFIGURED,
            (
                "个人模型不可用：API Key 未配置，请前往设置页完善后重试。"
                if source == "personal"
                else "平台模型不可用：平台配置未完成，请联系管理员。"
            ),
            400,
        )

    models = split_models(getattr(provider, "model_name", ""))
    if not models:
        raise LLMSelectionError(
            MODEL_NOT_ALLOWED,
            "当前所选模型已不可用，请重新选择。",
            400,
        )

    selected_model_name = model_name or models[0]
    if strict_selection and selected_model_name not in models:
        raise LLMSelectionError(
            MODEL_NOT_ALLOWED,
            "当前所选模型已不可用，请重新选择。",
            400,
        )

    request_registry = {
        name: settings.get_managed_provider(name) for name in LLM_CATEGORIES
    }
    request_registry[category] = settings.build_provider_config(
        category,
        api_key=provider.api_key or "",
        base_url=provider.base_url or "",
        model_name=provider.model_name or None,
        light_model_name=getattr(provider, "light_model_name", None) or None,
        supports_function_calling=getattr(provider, "supports_function_calling", True),
    )
    settings.activate_request_providers(request_registry)

    return {
        "source": source,
        "category": category,
        "provider_id": provider.id,
        "provider_name": provider.name or category.upper(),
        "model_name": selected_model_name,
        "api_key": provider.api_key or "",
        "base_url": provider.base_url or "",
        "supports_function_calling": getattr(provider, "supports_function_calling", True),
        "managed_llm": managed_llm,
        "managed_ocr": managed_ocr,
    }

"""
公共 LLM 初始化工具

所有智能体模块共享的模型初始化逻辑。
供应商配置和工厂方法统一在 config.py 的 LLMProviderConfig 子类中定义。
"""

from core.config import settings


def init_model(
    temperature: float = 0.1,
    provider: str = "openai",
    model_name: str | None = None,
    use_light: bool = False,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    light_model_name: str | None = None,
    supports_function_calling: bool | None = None,
):
    """初始化 LLM 模型

    Args:
        temperature: 温度参数
        provider: 模型供应商名称
        model_name: 指定模型名称，为 None 时使用配置默认值
        use_light: 使用轻量模型（用于科目识别等低成本任务）
        api_key: 直接传入 API Key（优先于数据库配置）
        base_url: 直接传入 Base URL
        light_model_name: 直接传入轻量模型名称
        supports_function_calling: 是否支持 function calling
    """
    if api_key:
        # 用传入的凭据动态构建配置，跳过环境变量
        from core.config import OpenAICompatibleConfig, AnthropicCompatibleConfig
        if provider == "anthropic":
            cfg = AnthropicCompatibleConfig(
                api_key=api_key,
                base_url=base_url or "",
                model_name=model_name or "claude-sonnet-4-20250514",
            )
        else:
            cfg = OpenAICompatibleConfig(
                api_key=api_key,
                base_url=base_url or "",
                model_name=model_name or "gpt-4o-mini",
                light_model_name=light_model_name,
                supports_function_calling=supports_function_calling if supports_function_calling is not None else True,
            )
    else:
        cfg = settings.get_provider(provider)

    if not cfg.configured:
        raise ValueError(f"使用 {provider} 需要配置 API Key，请在设置中配置")

    effective_model = cfg.resolve_model_name(model_name, use_light=use_light)

    return cfg.create_llm(model=effective_model, temperature=temperature)

"""Model factory — 使用 OpenAILike 构建 LLM 实例。"""

from dataclasses import dataclass

from agno.models.openai.like import OpenAILike

from config.settings import settings


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    api_key: str
    base_url: str


def get_primary_model_config() -> ModelConfig:
    return ModelConfig(
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )


def get_fallback_model_config() -> ModelConfig | None:
    if not settings.LLM_FALLBACK_PROVIDER:
        return None
    return ModelConfig(
        provider=settings.LLM_FALLBACK_PROVIDER,
        model=settings.LLM_FALLBACK_MODEL or "",
        api_key=settings.LLM_FALLBACK_API_KEY or "",
        base_url=settings.LLM_FALLBACK_BASE_URL or "",
    )


def build_model(cfg: ModelConfig | None = None) -> OpenAILike:
    cfg = cfg or get_primary_model_config()
    return OpenAILike(
        id=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )

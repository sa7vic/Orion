"""
Central configuration for Orion.

IMPORTANT — Groq model choice:
Groq deprecates and retires models periodically (e.g. llama-3.1-8b-instant and
llama-3.3-70b-versatile were both retired mid-2026). To avoid the whole app
breaking on a model retirement, EVERY model name lives here, is overridable
via .env, and the code never hard-codes a model string anywhere else.

Current defaults (checked at build time) point at Groq's `openai/gpt-oss-*`
family, which Groq itself recommends as the migration target for retired
Llama chat models. If these are retired in the future, check
https://console.groq.com/docs/deprecations and update the two lines below —
nothing else needs to change.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # --- Groq ---
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")

    # Fast/cheap model — used for high-volume, low-latency calls
    # (transcript scam-marker scoring, per-case classification prompts).
    groq_model_fast: str = Field(default="openai/gpt-oss-20b", alias="GROQ_MODEL_FAST")
    # Larger/higher-quality model — used for low-volume, high-value calls
    # (Identify pillar's fraud-pattern research/clustering, taxonomy writing).
    groq_model_smart: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL_SMART")

    # Free tier is roughly 30 requests/minute. We stay well under that so a
    # live demo never gets a 429. Tune via .env if you're on a paid tier.
    groq_max_requests_per_minute: int = Field(default=20, alias="GROQ_MAX_RPM")
    groq_cache_ttl_seconds: int = Field(default=3600, alias="GROQ_CACHE_TTL")

    # --- App ---
    cors_origins: list[str] = Field(default=["*"])
    data_dir: str = Field(default="app/data")
    models_dir: str = Field(default="app/data/trained_models")

    # Router confidence threshold: below this, route to the generalist
    # instead of a specialist.
    router_confidence_threshold: float = Field(default=0.42)

    # How many "generalist caught it, no specialist claimed it" cases of a
    # similar pattern before we auto-promote a stub specialist to active.
    feedback_promotion_threshold: int = Field(default=5)

    class Config:
        env_file = ".env"
        populate_by_name = True


settings = Settings()

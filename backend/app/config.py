from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Infrastructure — required
    DATABASE_URL: str
    REDIS_URL: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str

    # External APIs — optional until auth/AI phases are built
    ANTHROPIC_API_KEY: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # JWT
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_EXPIRE_HOURS: int = 24

    # Portfolio Ed25519 signing keypair (base64-encoded, generated in Phase 4)
    PORTFOLIO_SIGNING_PRIVATE_KEY: str = ""
    PORTFOLIO_SIGNING_PUBLIC_KEY: str = ""

    # Sandbox
    SANDBOX_TEMP_DIR: str = "/tmp/submissions"

    # ── Dev/testing helpers — never enable in production ─────────────────────
    # DEV_MODE=true exposes POST /auth/dev-login (login bypass for local testing)
    DEV_MODE: bool = False

    # AI review provider:
    #   "anthropic"     — Claude (default, production)
    #   "openai_compat" — any OpenAI-compatible API (free keys: Groq, Gemini,
    #                     OpenRouter) using DEV_LLM_* settings below
    #   "mock"          — no API key needed; deterministic review from test results
    REVIEW_PROVIDER: str = "anthropic"
    DEV_LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    DEV_LLM_API_KEY: str = ""
    DEV_LLM_MODEL: str = "llama-3.3-70b-versatile"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    """应用配置，通过 .env 或环境变量覆盖。"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+asyncpg://hpf:hpf@localhost:5432/hpf_work"
    secret_key: str = _DEFAULT_SECRET
    environment: str = "production"  # dev 允许默认密钥；其余环境强制强密钥
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 个人/小团队：7 天，无需 refresh token
    sse_ticket_expire_seconds: int = 30  # SSE ticket 短期有效（仅用于 /events/stream 认证）
    cors_origins: str = "http://localhost:8080"
    mcp_enabled: bool = True
    mcp_path: str = "/mcp"
    # MCP DNS 防重绑定的允许 Host（逗号分隔）；空则从 CORS_ORIGINS 推导
    mcp_allowed_hosts: str = ""

    @model_validator(mode="after")
    def _enforce_secret_key(self) -> "Settings":
        """非 dev 环境下拒绝公开默认密钥或过短密钥（fail-fast）。"""
        if self.environment == "dev":
            return self
        if self.secret_key == _DEFAULT_SECRET:
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in non-dev "
                "(generate: python -c \"import secrets; print(secrets.token_hex(32))\")"
            )
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in non-dev")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

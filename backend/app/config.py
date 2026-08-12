from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，通过 .env 或环境变量覆盖。"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+asyncpg://hpf:hpf@localhost:5432/hpf_work"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 个人/小团队：7 天，无需 refresh token
    cors_origins: str = "http://localhost:8080,http://localhost:3000"
    mcp_enabled: bool = True
    mcp_path: str = "/mcp"
    # MCP DNS 防重绑定的允许 Host（逗号分隔）；空则从 CORS_ORIGINS 推导
    mcp_allowed_hosts: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FlowState API"
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    api_token: str = Field(default="change-me", min_length=8)
    jwt_secret: str = Field(default="flowstate-dev-secret-change-in-production-32chars", min_length=32)
    enable_auth: bool = Field(default=True)

    database_url: str = Field(default="sqlite:///./flowstate.db")
    behavior_window_size: int = Field(default=500, ge=100, le=5000)
    rl_alpha: float = Field(default=0.1, ge=0.01, le=1.0)
    rl_gamma: float = Field(default=0.9, ge=0.01, le=0.99)
    rl_epsilon: float = Field(default=0.1, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()


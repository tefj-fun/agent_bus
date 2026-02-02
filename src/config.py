"""Configuration management for agent_bus system."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "agent_bus"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    # LLM
    llm_mode: str = Field(default="real", env="LLM_MODE")  # real|mock
    llm_provider: str = Field(default="anthropic", env="LLM_PROVIDER")  # anthropic|openai

    # Anthropic Claude (only required when LLM_PROVIDER=anthropic and LLM_MODE=real)
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-5-20250929", env="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(default=8192, env="ANTHROPIC_MAX_TOKENS")

    # OpenAI (only required when LLM_PROVIDER=openai and LLM_MODE=real)
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")

    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    # PostgreSQL
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="agent_bus", env="POSTGRES_DB")
    postgres_user: str = Field(default="agent_bus", env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")

    # ChromaDB
    chroma_persist_directory: str = Field(default="./data/chroma", env="CHROMA_PERSIST_DIRECTORY")

    # Artifact Storage
    artifact_output_dir: str = Field(default="./outputs", env="ARTIFACT_OUTPUT_DIR")
    artifact_storage_backend: str = Field(
        default="file", env="ARTIFACT_STORAGE_BACKEND"
    )  # file|postgres

    # Skills
    skills_directory: str = Field(default="./skills", env="SKILLS_DIRECTORY")

    # Workers
    max_workers: int = Field(default=4, env="MAX_WORKERS")

    # PostgreSQL Pool Settings
    postgres_pool_min_size: int = Field(default=2, env="POSTGRES_POOL_MIN_SIZE")
    postgres_pool_max_size: int = Field(default=10, env="POSTGRES_POOL_MAX_SIZE")
    postgres_command_timeout: int = Field(default=60, env="POSTGRES_COMMAND_TIMEOUT")

    # Timeout Configuration (in seconds)
    timeout_task_completion: int = Field(
        default=3600, env="TIMEOUT_TASK_COMPLETION"
    )  # Max time to wait for a task
    timeout_llm_call: int = Field(default=180, env="TIMEOUT_LLM_CALL")  # LLM API call timeout
    timeout_db_query: int = Field(default=30, env="TIMEOUT_DB_QUERY")  # Database query timeout
    timeout_redis_operation: int = Field(
        default=10, env="TIMEOUT_REDIS_OPERATION"
    )  # Redis operation timeout

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = Field(
        default=5, env="CIRCUIT_BREAKER_FAILURE_THRESHOLD"
    )  # Failures before opening
    circuit_breaker_recovery_timeout: int = Field(
        default=30, env="CIRCUIT_BREAKER_RECOVERY_TIMEOUT"
    )  # Seconds before trying again
    circuit_breaker_half_open_requests: int = Field(
        default=3, env="CIRCUIT_BREAKER_HALF_OPEN_REQUESTS"
    )  # Requests to test in half-open

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

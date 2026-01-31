"""Configuration management for agent_bus system."""

import os
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

    # Anthropic Claude
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-5-20250929", env="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(default=8192, env="ANTHROPIC_MAX_TOKENS")

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
    chroma_persist_directory: str = Field(
        default="./data/chroma",
        env="CHROMA_PERSIST_DIRECTORY"
    )

    # Skills
    skills_directory: str = Field(default="./skills", env="SKILLS_DIRECTORY")

    # Workers
    worker_type: str = Field(default="cpu", env="WORKER_TYPE")  # cpu or gpu
    max_workers: int = Field(default=4, env="MAX_WORKERS")

    # Kubernetes
    k8s_namespace: str = Field(default="agent-bus", env="K8S_NAMESPACE")
    k8s_gpu_node_selector: str = Field(
        default="accelerator=nvidia-tesla-v100",
        env="K8S_GPU_NODE_SELECTOR"
    )

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
